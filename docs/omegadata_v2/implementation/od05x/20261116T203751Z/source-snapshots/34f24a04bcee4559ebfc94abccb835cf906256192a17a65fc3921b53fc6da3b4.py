"""OD05X v1: exact input staging inside a fail-closed Linux OS boundary.

Trusted launcher binds reviewed files individually; worker proves namespaces,
read-only inputs and irreversible seccomp before calling the sole stage API.
Windows has no implemented backend and refuses without staging any files.
"""

from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import json
import os
import platform
import re
import stat
import subprocess
import sys
import threading
import uuid
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

STAGING_ENTRYPOINT = "stage"
CLASSES = {
    "CODE": {".py"}, "STATIC_CONFIG": {".json", ".toml"},
    "LOCAL_META": {".json"}, "EXISTING_REGRESSION_METADATA": {".json"},
    "STATIC_UI": {".html", ".css", ".js"}, "DOCUMENTATION": {".md"},
}
DENIED = {"zip", "csv", "gz", "parquet", "db", "sqlite", "bin", "key", "pem", "rev"}
_BOUNDARY: dict[str, Any] | None = None
_LIBC: Any = None


def identity(path: Path) -> tuple[int, ...]:
    return stat_identity(path.lstat())


def stat_identity(s: os.stat_result) -> tuple[int, ...]:
    return (s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_nlink)


def ancestors(path: Path) -> None:
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError("PATH_UNSAFE")
    for parent in (*reversed(path.parents), path):
        info = parent.lstat()
        if (not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & 0x400):
            raise ValueError("PATH_UNSAFE")


def entries(spec: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = spec.get("files")
    if (spec.get("schema_version") != "od05x.inputs/v1" or not isinstance(rows, list)
            or not rows or len(rows) > 10000 or spec.get("file_count") != len(rows)):
        raise ValueError("MANIFEST_COUNT")
    seen = set()
    for row in rows:
        name = row.get("path", "")
        parts = name.split("/")
        classification = row.get("class")
        if (not isinstance(name, str) or not name or name.casefold() in seen
                or any(p in {"", ".", ".."} or not re.fullmatch(r"[A-Za-z0-9_. =-]+", p)
                       for p in parts)
                or any(p.casefold() in {"artifacts", "gnupg", "od05v", "od05r"}
                       or p.casefold().startswith((".env", ".venv")) for p in parts)
                or classification not in CLASSES
                or Path(name).suffix not in CLASSES[classification]
                or any(p.casefold() in DENIED for p in Path(name).name.split("."))
                or ("data" in parts and not (classification == "LOCAL_META"
                                               and name.endswith(".manifest.json")))
                or type(row.get("bytes")) is not int or not 0 <= row["bytes"] <= 8_000_000
                or not re.fullmatch(r"[a-f0-9]{64}", row.get("sha256", ""))):
            raise ValueError("MANIFEST_SCOPE")
        seen.add(name.casefold())
    return rows


def verify_pins(root: Path, spec: Mapping[str, Any]) -> int:
    """Only a reviewed code/metadata manifest may reach this reader."""
    rows = entries(spec)
    ancestors(root)
    for row in rows:
        path = root / row["path"]
        ancestors(path.parent)
        before = identity(path)
        if not stat.S_ISREG(before[2]) or before[5] != 1:
            raise ValueError("PATH_UNSAFE")
        with path.open("rb") as stream:
            if stat_identity(os.fstat(stream.fileno())) != before:
                raise ValueError("INPUT_CHANGED")
            raw = stream.read(row["bytes"] + 1)
        if (len(raw) != row["bytes"] or hashlib.sha256(raw).hexdigest() != row["sha256"]
                or identity(path) != before):
            raise ValueError("INPUT_CHANGED")
    return len(rows)


def assert_boundary() -> dict[str, Any]:
    if sys.platform != "linux" or _BOUNDARY is None or _LIBC is None:
        raise ValueError("OS_ISOLATION_CAPABILITY_BLOCKED")
    if _LIBC.prctl(39, 0, 0, 0, 0) != 1 or _LIBC.prctl(21, 0, 0, 0, 0) != 2:
        raise ValueError("OS_ISOLATION_MISMATCH")
    actual = {n: os.readlink("/proc/self/ns/" + n) for n in ("mnt", "net", "pid", "user")}
    if actual != _BOUNDARY["worker_namespaces"]:
        raise ValueError("OS_ISOLATION_MISMATCH")
    return dict(_BOUNDARY)


def selected_source(root: Path, row: Mapping[str, Any]) -> Path:
    mapped = row.get("sandbox_source")
    if mapped is None:
        return root / row["path"]
    path = Path(mapped)
    if (not path.is_relative_to(Path("/chunks")) or ".." in path.parts
            or not str(path).endswith("/" + row["path"])):
        raise ValueError("PATH_UNSAFE")
    return path


def stage(root: Path, destination: Path, spec: Mapping[str, Any], *,
          capability: Mapping[str, Any] | None,
          hooks: Mapping[str, Callable[[], None]] | None = None) -> dict[str, Any]:
    if capability is None or capability != assert_boundary():
        raise ValueError("OS_ISOLATION_MISMATCH")
    rows = entries(spec)
    ancestors(root)
    if (not destination.is_absolute() or destination.exists() or destination.is_symlink()
            or destination.is_relative_to(root) or root.is_relative_to(destination)
            or not destination.is_relative_to(Path("/work"))):
        raise ValueError("FRESH_DESTINATION_REQUIRED")
    ancestors(destination.parent)
    # Validate the entire selection before opening the first file. Mount-device
    # exceptions are exact per-file records supplied by the trusted launcher.
    before = {}
    for row in rows:
        path = selected_source(root, row)
        ancestors(path.parent)
        info = identity(path)
        allowed_device = row.get("device", root.lstat().st_dev)
        if not stat.S_ISREG(info[2]) or info[5] != 1 or info[0] != allowed_device:
            raise ValueError("PATH_UNSAFE")
        before[row["path"]] = info
    destination.mkdir(mode=0o700)
    records = []
    for row in rows:
        source = selected_source(root, row)
        if hooks and "before_open" in hooks:
            hooks["before_open"]()
        if identity(source) != before[row["path"]]:
            raise ValueError("INPUT_CHANGED")
        fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as stream:
            if stat_identity(os.fstat(stream.fileno())) != before[row["path"]]:
                raise ValueError("INPUT_CHANGED")
            raw = stream.read(row["bytes"] + 1)
            if hooks and "after_read" in hooks:
                hooks["after_read"]()
            stable_descriptor = stat_identity(os.fstat(stream.fileno())) == before[row["path"]]
        if (not stable_descriptor or len(raw) != row["bytes"]
                or hashlib.sha256(raw).hexdigest() != row["sha256"]
                or identity(source) != before[row["path"]]):
            raise ValueError("INPUT_CHANGED")
        output = destination / row["path"]
        output.parent.mkdir(parents=True, exist_ok=True)
        ancestors(output.parent)
        with output.open("xb") as stream:
            stream.write(raw)
        if hashlib.sha256(output.read_bytes()).hexdigest() != row["sha256"]:
            raise ValueError("COPY_MISMATCH")
        records.append(dict(row))
    receipt = {"schema_version": "od05x.copy/v1", "file_count": len(records),
               "files": records, "payload_files_copied": 0, "boundary_before_copy": capability,
               "bytes": sum(r["bytes"] for r in records)}
    raw_receipt = json.dumps(receipt, sort_keys=True).encode()
    receipt_path = destination.parent / ("receipt-" + hashlib.sha256(raw_receipt).hexdigest() + ".json")
    with receipt_path.open("xb") as stream:
        stream.write(raw_receipt)
    receipt_path.chmod(0o444)
    return receipt


def install_seccomp() -> None:
    """Irreversible worker-only filter, after trusted interpreter initialization."""
    global _LIBC
    _LIBC = ctypes.CDLL(None, use_errno=True)
    lib = ctypes.CDLL("libseccomp.so.2", use_errno=True)
    lib.seccomp_init.argtypes = [ctypes.c_uint32]
    lib.seccomp_init.restype = ctypes.c_void_p
    lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    lib.seccomp_syscall_resolve_name.restype = ctypes.c_int
    lib.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    lib.seccomp_load.argtypes = [ctypes.c_void_p]
    lib.seccomp_release.argtypes = [ctypes.c_void_p]
    ctx = lib.seccomp_init(0x7FFF0000)  # SCMP_ACT_ALLOW; narrowly denied syscall families.
    if not ctx or _LIBC.prctl(38, 1, 0, 0, 0):
        raise ValueError("OS_ISOLATION_SECCOMP_UNAVAILABLE")

    class Compare(ctypes.Structure):
        _fields_ = [("arg", ctypes.c_uint), ("op", ctypes.c_int),
                    ("a", ctypes.c_uint64), ("b", ctypes.c_uint64)]

    def rule(name: str, action: int, *comparisons: Any) -> None:
        number = lib.seccomp_syscall_resolve_name(name.encode())
        if number < 0 or lib.seccomp_rule_add(ctx, action, number, len(comparisons), *comparisons):
            raise ValueError("OS_ISOLATION_SECCOMP_RULE")

    deny = 0x00050000 | errno.EPERM
    try:
        for name in ("execve", "execveat", "fork", "vfork", "unshare", "setns", "mount",
                     "umount2", "ptrace", "process_vm_readv", "process_vm_writev",
                     "open_by_handle_at", "bpf", "io_uring_setup", "reboot", "kexec_load",
                     "connect", "bind", "listen", "accept", "accept4", "sendmsg"):
            rule(name, deny)
        # glibc falls back to clone for threads when clone3 returns ENOSYS.
        rule("clone3", 0x00050000 | errno.ENOSYS)
        rule("clone", deny, Compare(0, 7, 0x10000, 0))  # MASKED_EQ, no CLONE_THREAD.
        rule("socket", deny, Compare(0, 1, 1, 0))  # NE AF_UNIX: all other families denied.
        # Connected local socketpair IPC is required by asynchronous test workers.
        # Explicit destination addresses remain denied; Internet socket creation
        # and every connect syscall remain denied independently.
        rule("sendto", deny, Compare(4, 1, 0, 0))  # NE: destination pointer != NULL.
        if lib.seccomp_load(ctx):
            raise ValueError("OS_ISOLATION_SECCOMP_LOAD")
    finally:
        lib.seccomp_release(ctx)


def native_probe(kind: str) -> dict[str, Any]:
    cap = assert_boundary()
    assert _LIBC is not None
    ctypes.set_errno(0)
    if kind == "read":
        value = _LIBC.open(cap["outside_canary"].encode(), os.O_RDONLY)
    elif kind == "write":
        value = _LIBC.open(b"/input/scripts/od05x_isolated_runner.py", os.O_WRONLY)
    elif kind == "exec":
        value = _LIBC.fork()
        if value == 0:
            os._exit(97)
        if value > 0:
            os.waitpid(value, 0)
    elif kind == "tcp":
        value = _LIBC.socket(2, 1, 0)
    elif kind == "dns":
        value = _LIBC.socket(2, 2, 0)
    elif kind == "execve":
        args = (ctypes.c_char_p * 2)(b"true", None)
        environment = (ctypes.c_char_p * 1)(None)
        value = _LIBC.execve(b"/usr/bin/true", args, environment)
    elif kind == "netlink":
        value = _LIBC.socket(16, 3, 0)
    elif kind in {"bind", "listen", "accept4"}:
        fd = _LIBC.socket(1, 1, 0)
        if fd < 0:
            raise ValueError("OS_PROBE_DESCRIPTOR_FAILED")
        address = ctypes.create_string_buffer(b"\x01\x00\x00OD05X_NON_MARKET_CANARY")
        ctypes.set_errno(0)
        if kind == "bind":
            value = _LIBC.bind(fd, ctypes.byref(address), 27)
        elif kind == "listen":
            value = _LIBC.listen(fd, 1)
        else:
            value = _LIBC.accept4(fd, None, None, 0x800)
        saved_errno = ctypes.get_errno()
        _LIBC.close(fd)
        ctypes.set_errno(saved_errno)
    elif kind in {"tcp_connect", "dns_sendto"}:
        # AF_UNIX descriptor prevents a packet even if a filter is broken.
        # The native syscall must nevertheless return the filter's EPERM,
        # rather than a protocol/address error from the harmless descriptor.
        fd = _LIBC.socket(1, 2 if kind == "dns_sendto" else 1, 0)
        if fd < 0:
            raise ValueError("OS_PROBE_DESCRIPTOR_FAILED")
        address = ctypes.create_string_buffer(
            b"\x02\x00\x00" + (b"\x35" if kind == "dns_sendto" else b"\x09")
            + b"\x7f\x00\x00\x01" + b"\x00" * 8
        )
        ctypes.set_errno(0)
        if kind == "tcp_connect":
            value = _LIBC.connect(fd, ctypes.byref(address), 16)
        else:
            value = _LIBC.sendto(fd, b"NON_MARKET_CANARY", 16, 0, ctypes.byref(address), 16)
        saved_errno = ctypes.get_errno()
        _LIBC.close(fd)
        ctypes.set_errno(saved_errno)
    else:
        raise ValueError("PROBE_SCOPE")
    error = ctypes.get_errno()
    if value >= 0 and kind in {"read", "write", "tcp", "dns"}:
        _LIBC.close(value)
    expected = {errno.ENOENT, errno.EACCES} if kind == "read" else (
        {errno.EROFS, errno.EACCES} if kind == "write" else {errno.EPERM})
    return {"probe": kind, "native_return": value, "errno": error,
            "denied": value == -1 and error in expected,
            "python_hook": False}


def small_canary(parent: Path) -> tuple[Path, Any, Path]:
    from omegadata.parsers.archive_candidate_inventory import ExpectedMetadata
    from omegadata.parsers.local_archive_presence import ROOTS

    groups = json.loads(Path("/work/repo/od05v_inputs/groups.json").read_bytes())
    name, sha, length = groups["seed"]["entries"][0]
    raw = (Path("/work/repo/od05t_inputs/seed") / name).read_bytes()
    repo = parent / "NON_MARKET_CANARY"
    target = repo / ROOTS["seed"] / name
    target.parent.mkdir(parents=True)
    target.write_bytes(raw)
    body = json.loads(raw)
    payload = repo / body["artifact_path"].replace("\\", "/")
    payload.touch()
    with payload.open("r+b") as stream:
        stream.truncate(body["bytes_downloaded"])
    return repo, ExpectedMetadata(((name, sha, length),)), target


class CanaryObservation:
    """Opt-in canary diagnostic wrapper. Never used for original archive paths."""

    def __init__(self, repo: Path, label: str, expected: Any, events: list[dict[str, Any]]):
        from omegadata.parsers.local_archive_presence import ROOTS, PresenceObservation

        if not repo.is_relative_to(Path("/work")) or repo.name != "NON_MARKET_CANARY":
            raise ValueError("CANARY_DIAGNOSTICS_ONLY")
        self.repo, self.root = repo, repo / ROOTS[label]
        self.inner = PresenceObservation(repo, label, expected)
        self.events, self.lock, self.generation = events, threading.Lock(), uuid.uuid4().hex

    @property
    def scan_count(self) -> int:
        return self.inner.scan_count

    def get(self) -> dict[str, Any]:
        from omegadata.parsers.archive_candidate_inventory import InventoryError

        with self.lock:
            before = self.inner._identities.copy() or self.inner._fingerprint(self.root)
            try:
                result = self.inner.get()
                reason = "UNCHANGED"
            except InventoryError as error:
                reason = error.reason_code
                raise
            finally:
                after = self.inner._fingerprint(self.root)
                keys = ("dev", "ino", "mode", "size", "mtime_ns", "nlink")
                changed = [{"relative": p.relative_to(self.repo).as_posix(),
                            "before": dict(zip(keys, before[p], strict=True)),
                            "after": dict(zip(keys, after[p], strict=True)) if p in after else None}
                           for p in before if before[p] != after.get(p)]
                self.events.append({"reason": reason, "generation": self.generation,
                                    "process": os.getpid(), "thread": threading.get_ident(),
                                    "invocation": len(self.events) + 1, "changes": changed,
                                    "directory_identity": list(identity(self.root))})
        return result


def corpus_status(kind: str) -> dict[str, Any]:
    if kind not in {"NON_MARKET_CANARY", "LOCAL_META"}:
        raise ValueError("CORPUS_CLASS")
    return {"class": kind, "financial_rows": 0}


def classify(nodes: Sequence[str], reviewed: Mapping[str, str]) -> dict[str, str]:
    if len(nodes) != len(set(nodes)) or set(nodes) != set(reviewed):
        raise ValueError("UNCLASSIFIED_TEST")
    if any(value not in {"A", "B", "C"} for value in reviewed.values()):
        raise ValueError("UNCLASSIFIED_TEST")
    return dict(reviewed)


def diagnostic_status(exit_code: int) -> str:
    return "FAIL" if exit_code else "PASS"


def reconcile_reviewed_inputs(root: Path) -> dict[str, Any]:
    inputs = root / "od05x_inputs"
    review = json.loads((inputs / "review.json").read_bytes())
    inventory = review["old_inventory"]
    from collections import Counter

    assert len(inventory) == 775 and Counter(inventory.values()) == {"A": 767, "B": 4, "C": 4}
    assert all(hashlib.sha256((root / n).read_bytes()).hexdigest() == sha
               for n, sha in review["old_test_hashes"].items())
    assert review.get("new_test_hashes") and all(
        hashlib.sha256((root / n).read_bytes()).hexdigest() == sha
        for n, sha in review["new_test_hashes"].items()
    ), "NEW_TEST_SOURCE_CHANGED"
    independent = json.loads((inputs / "original-independent-stat.json").read_bytes())
    model = json.loads((inputs / "original-model-stat.json").read_bytes())
    assert set(independent["rows"]) == set(model["rows"]) and len(model["rows"]) == 3626
    for name, row in independent["rows"].items():
        assert row == model["rows"][name]
    assert independent["counts"] == model["counts"]
    return {"old_nodes": len(inventory), "old_classes": dict(Counter(inventory.values())),
            "all_reviewed_test_hashes_match": True, "new_test_class": "EXPLICIT_REVIEWED_A",
            "B_exact_unchanged": 4, "C_exact_blocked": 4, "C_executed": 0,
            "fresh_stat_counts": independent["counts"], "all_candidate_identities_accounted": 3626,
            "original_byte_integrity": "NOT_MEASURED"}


def verdicts(*, software: bool, containment: bool) -> dict[str, str]:
    return {"software": "PASS" if software else "BLOCKED",
            "containment": "PASS" if containment else "BLOCKED",
            "financial": "BLOCKED_REAL_DATA", "B": "BLOCKED_INPUT",
            "C": "NOT_RUN_BLOCKED_REAL_DATA",
            "safe_engineering": "OD05X_SAFE_ENGINEERING_PASS" if software and containment else "BLOCKED"}


def launch(manifest: Path, manifest_sha: str, output: Path, policy: Path) -> int:
    """Trusted, no-copy launcher. No fallback backend or historical bootstrap."""
    if sys.platform != "linux" or platform.machine() != "x86_64":
        raise ValueError("OS_ISOLATION_CAPABILITY_BLOCKED")
    raw = manifest.read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest_sha:
        raise ValueError("MANIFEST_PIN_MISMATCH")
    spec = json.loads(raw)
    rows = entries(spec)
    config = json.loads(policy.read_bytes())
    if output.exists():
        raise ValueError("FRESH_DESTINATION_REQUIRED")
    ancestors(output.parent)
    output.mkdir(mode=0o700)
    # Configuration and code are exact read-only mounts, never recursive repo binds.
    runtime = config["runtime"]
    argv = ["/usr/bin/bwrap", "--unshare-all", "--die-with-parent", "--new-session",
            "--cap-drop", "ALL", "--clearenv", "--ro-bind", "/usr", "/usr",
            "--symlink", "usr/lib", "/lib", "--symlink", "usr/lib64", "/lib64",
            "--ro-bind", runtime, runtime, "--proc", "/proc", "--dev", "/dev",
            "--bind", str(output), "/work", "--dir", "/input", "--dir", "/policy",
            "--ro-bind", str(manifest), "/policy/manifest.json",
            "--ro-bind", str(policy), "/policy/config.json"]
    chunks = {}
    checked_parents: dict[Path, tuple[int, ...]] = {}
    for row in rows:
        source = Path(row["host"])
        if not source.is_absolute() or ".." in source.parts:
            raise ValueError("PATH_UNSAFE")
        for parent in (*reversed(source.parent.parents), source.parent):
            if parent not in checked_parents:
                current = identity(parent)
                if not stat.S_ISDIR(current[2]) or getattr(parent.lstat(), "st_file_attributes", 0) & 0x400:
                    raise ValueError("PATH_UNSAFE")
                checked_parents[parent] = current
        info = source.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or info.st_dev != row["device"] or info.st_size != row["bytes"]):
            raise ValueError("PATH_UNSAFE")
        if "chunk_root" in row:
            chunk = row["chunk_root"]
            if chunk not in chunks:
                chunks[chunk] = "/chunks/" + str(len(chunks))
                argv += ["--ro-bind", chunk, chunks[chunk]]
            if row.get("sandbox_source") != chunks[chunk] + "/" + row["path"]:
                raise ValueError("PATH_UNSAFE")
            if source != Path(chunk) / row["path"]:
                raise ValueError("PATH_UNSAFE")
        else:
            argv += ["--ro-bind", str(source), "/input/" + row["path"]]
    if any(identity(p) != expected for p, expected in checked_parents.items()):
        raise ValueError("INPUT_CHANGED")
    argv += ["--remount-ro", "/dev", "--remount-ro", "/proc", "--remount-ro", "/", "--chdir", "/work", "--setenv", "PYTHONDONTWRITEBYTECODE", "1",
             "--setenv", "PATH", "/usr/bin", runtime + "/bin/python", "-B",
             "/input/scripts/od05x_isolated_runner.py", "worker"]
    result = subprocess.run(argv, check=False, capture_output=True, text=True)
    with (output / "launcher-result.json").open("x") as stream:
        json.dump({"argv": argv, "exit_code": result.returncode, "stdout": result.stdout,
                   "stderr": result.stderr}, stream, indent=2)
    return result.returncode


def worker() -> int:
    global _BOUNDARY
    config = json.loads(Path("/policy/config.json").read_bytes())
    spec = json.loads(Path("/policy/manifest.json").read_bytes())
    actual = {n: os.readlink("/proc/self/ns/" + n) for n in ("mnt", "net", "pid", "user")}
    if any(actual[n] == config["parent_namespaces"][n] for n in actual):
        raise ValueError("OS_ISOLATION_NAMESPACE_MISMATCH")
    mounts = Path("/proc/self/mountinfo").read_text().splitlines()
    for row in spec["files"]:
        mount = ("/chunks/" + row["sandbox_source"].split("/")[2]
                 if "sandbox_source" in row else "/input/" + row["path"])
        matches = [m.split() for m in mounts if m.split()[4] == mount]
        if len(matches) != 1 or "ro" not in matches[0][5].split(","):
            raise ValueError("OS_ISOLATION_READONLY_MISMATCH")
    install_seccomp()
    _BOUNDARY = {"backend": "bwrap+seccomp/v1", "worker_namespaces": actual,
                 "outside_canary": config["outside_canary"], "verified": True,
                 "source_mounts": "EXACT_READ_ONLY", "no_new_privs": True, "seccomp_mode": 2}
    probes = [native_probe(n) for n in ("read", "write", "exec", "tcp", "dns", "execve", "tcp_connect", "dns_sendto", "netlink", "bind", "listen", "accept4")]
    if not all(p["denied"] for p in probes):
        raise ValueError("OS_ISOLATION_NATIVE_PROBE_FAILED")
    pair = (ctypes.c_int * 2)()
    if _LIBC.socketpair(1, 1, 0, pair) != 0:
        raise ValueError("LOCAL_IPC_CONTROL_FAILED")
    ctypes.set_errno(0)
    local_sent = _LIBC.send(pair[0], b"NON_MARKET_CANARY", 16, 0)
    local_errno = ctypes.get_errno()
    _LIBC.close(pair[0])
    _LIBC.close(pair[1])
    if local_sent != 16:
        raise ValueError("LOCAL_IPC_CONTROL_FAILED")
    with Path("/work/native-probes.json").open("x") as stream:
        json.dump({"boundary": assert_boundary(), "probes": probes,
                   "local_ipc_control": {"bytes": local_sent, "errno": local_errno,
                                         "external_network_packets": 0}}, stream, indent=2)
    stage(Path("/input"), Path("/work/repo"), spec, capability=assert_boundary())
    if config["job"] == "stage_only":
        return 0
    # Ensure imported worker and tests share the same live attestation state.
    sys.modules["od05x_isolated_runner"] = sys.modules[__name__]
    sys.path[:0] = ["/work/repo/src", "/work/repo/scripts", "/work/repo/tests/unit"]
    import od05x_worker_jobs

    return int(od05x_worker_jobs.run(config))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("launch", "worker"))
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--manifest-sha256")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--policy", type=Path)
    args = parser.parse_args()
    try:
        code = worker() if args.mode == "worker" else launch(args.manifest, args.manifest_sha256,
                                                             args.output, args.policy)
    except (ValueError, OSError) as error:
        print(json.dumps({"state": "REFUSED", "reason": str(error)}))
        code = 2
    sys.exit(code)
