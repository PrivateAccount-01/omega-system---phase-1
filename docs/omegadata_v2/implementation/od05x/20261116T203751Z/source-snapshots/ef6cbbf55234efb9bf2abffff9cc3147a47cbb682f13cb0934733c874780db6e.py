"""Jobs invoked only after OD05X native boundary proof and canonical staging."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.metadata
import io
import json
import os
import runpy
import socket
import sys
import tempfile
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def save(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)


def setup_canaries() -> None:
    """Transform reviewed metadata to sparse NON_MARKET_CANARY filesystem only."""
    from od05v_presence_oracle import observe

    root = Path("/work/repo")
    groups = json.loads((root / "od05v_inputs/groups.json").read_bytes())
    original = json.loads((root / "od05w_inputs/original-stat.json").read_bytes())
    facts = json.loads((root / "od05x_inputs/original-independent-stat.json").read_bytes())["rows"]
    canary = Path("/work/NON_MARKET_CANARY")
    canary.mkdir()
    for label, group in groups.items():
        for name, sha, length in group["entries"]:
            raw = (root / group["repository_root"] / name).read_bytes()
            assert len(raw) == length and hashlib.sha256(raw).hexdigest() == sha
            out = root / "od05t_inputs" / label / name
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(raw)
            out = canary / group["repository_root"] / name
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(raw)
            meta = json.loads(raw)
            payload = canary / meta["artifact_path"].replace("\\", "/")
            payload.touch()
            with payload.open("r+b") as stream:
                stream.truncate(meta["bytes_downloaded"])
            if facts[meta["artifact_path"].replace("\\", "/")]["nlink"] != 1:
                os.link(payload, payload.with_suffix(".NON_MARKET_CANARY"))
    save(root / "od05v_inputs/presence.json", observe(canary, groups))
    # W10 intentionally tests its archived W-phase record, not a false X-phase result.
    assert original["phase"] == "OD05W"


class GuardDenied(PermissionError, RuntimeError):
    pass


def python_guard(writable: Path) -> dict[str, int]:
    """Defense in depth after OS probes; never used to certify native denials."""
    counts: Counter[str] = Counter()
    canary = Path("/work/NON_MARKET_CANARY")
    repo = Path("/work/repo")

    def deny(kind: str) -> None:
        counts[kind] += 1
        raise GuardDenied("OD05X_BLOCKED_" + kind)

    def absolute(value: Any) -> Path:
        return Path(os.path.abspath(os.fsdecode(value)))

    def write_check(value: Any) -> None:
        if not isinstance(value, int) and not absolute(value).resolve().is_relative_to(writable):
            deny("WRITE")

    def audit(event: str, args: tuple[Any, ...]) -> None:
        if event in {"subprocess.Popen", "os.system", "os.posix_spawn", "os.spawn"}:
            deny("SUBPROCESS")
        if event in {"socket.connect", "socket.bind", "socket.getaddrinfo", "socket.sendto"}:
            deny("NETWORK")
        if event == "open" and not isinstance(args[0], int):
            path = absolute(args[0])
            if args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                write_check(path)
            elif (path.is_relative_to(canary) and not path.name.endswith(".manifest.json")):
                deny("CANARY_PAYLOAD")
            elif str(path) in {os.environ.get("OD05W_FORBIDDEN_CANARY"),
                               os.environ.get("OD05W_EXTERNAL_CANARY")}:
                deny("READ")
            elif not (path.is_relative_to(writable) or path.is_relative_to(repo)
                      or path.is_relative_to(canary) or path.is_relative_to(Path("/usr"))
                      or path.is_relative_to(Path(sys.prefix)) or path == Path(os.devnull)
                      or path == Path("/input/scripts/od05x_isolated_runner.py")
                      or path in {Path("/etc/mime.types"), Path("/etc/localtime"), Path("/etc/timezone")}
                      or str(path).startswith("/proc/self/")):
                deny("UNLISTED_READ")
        if event in {"os.remove", "os.rmdir", "os.mkdir", "os.chmod", "os.utime"}:
            write_check(args[0])
        if event in {"os.rename", "os.link"}:
            write_check(args[0])
            write_check(args[1])
        if event == "os.symlink":
            write_check(args[1])
        if event == "sqlite3.connect" and args[0] != ":memory:":
            write_check(args[0])

    sys.addaudithook(audit)
    original_socket = socket.socket

    class RefusalSocket(original_socket):
        """Legacy Python refusal API, backed only by a local IPC descriptor.

        Never creates an Internet socket. Native Internet creation remains
        kernel-denied; this preserves older tests that expect refusal at connect.
        """

        def __init__(self, family: int = -1, type: int = -1, proto: int = -1,
                     fileno: int | None = None) -> None:
            self._blocked_ip = fileno is None and family in {-1, socket.AF_INET, socket.AF_INET6}
            if self._blocked_ip:
                super().__init__(socket.AF_UNIX, socket.SOCK_STREAM if type == -1 else type, 0)
            else:
                super().__init__(family, type, proto, fileno)

        def connect(self, address: Any) -> None:
            if self._blocked_ip:
                deny("NETWORK")
            super().connect(address)

        def connect_ex(self, address: Any) -> int:
            if self._blocked_ip:
                deny("NETWORK")
            return int(super().connect_ex(address))

        def sendto(self, *args: Any, **kwargs: Any) -> int:
            if self._blocked_ip:
                deny("NETWORK")
            return int(super().sendto(*args, **kwargs))

        def send(self, *args: Any, **kwargs: Any) -> int:
            if self._blocked_ip:
                deny("NETWORK")
            return int(super().send(*args, **kwargs))

        def recv(self, *args: Any, **kwargs: Any) -> bytes:
            if self._blocked_ip:
                deny("NETWORK")
            return bytes(super().recv(*args, **kwargs))

    socket.socket = RefusalSocket
    return counts


def run(config: dict[str, Any]) -> int:
    import od05x_isolated_runner as launcher

    launcher.assert_boundary()
    os.chdir("/work/repo")
    setup_canaries()
    output = Path("/work/job")
    output.mkdir()
    os.environ.update({"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1",
                       "TMP": str(output), "TEMP": str(output), "TMPDIR": str(output),
                       "OD05W_GUARD_ACTIVE": "1", "OD05W_CORPUS_CLASS": "NON_MARKET_CANARY",
                       "OD05V_ORIGINAL": "/work/NON_MARKET_CANARY",
                       "OD05W_ORIGINAL_BOUNDARY": "/unmounted-original",
                       "OD05W_FORBIDDEN_CANARY": "/unmounted-original/NON_MARKET_CANARY.zip",
                       "OD05W_EXTERNAL_CANARY": "/unmounted-retained/NON_MARKET_CANARY",
                       "OD05W_FORBIDDEN_WRITE": "/work/repo/NON_MARKET_CANARY",
                       "OD01R_DISPOSABLE_ROOT": str(output), "OD02V_DISPOSABLE_ROOT": str(output),
                       "OD02V_WORKTREE": "/work/repo", "COVERAGE_FILE": str(output / "coverage.db"),
                       "MYPY_CACHE_DIR": str(output / "mypy")})
    for key, value in {"DB_URL": "sqlite:////work/job/default.sqlite",
                       "VERIFICATION_DB_URL": "sqlite:////work/job/verification.sqlite",
                       "API_KEY": "SOFTWARE_TEST_ONLY", "ALERT_WEBHOOK_URL": "",
                       "RELEASE_GPG_KEY_ID": ""}.items():
        os.environ["OMEGA_" + key] = value
    for key in ("RAW_ROOT", "SEED_RAW_ROOT", "PARQUET_ROOT", "REPORT_ROOT", "REPROCESS_ROOT",
                "RELEASE_ROOT", "RELEASE_GPG_HOME"):
        os.environ["OMEGA_" + key] = str(output / key)
    tempfile.tempdir = str(output)
    sys.dont_write_bytecode = True
    reports: list[dict[str, Any]] = []
    collected: list[dict[str, Any]] = []
    deselected: list[str] = []

    class Evidence:
        def pytest_collection_finish(self, session: Any) -> None:
            collected.extend({"nodeid": i.nodeid, "realdata": i.get_closest_marker("realdata") is not None}
                             for i in session.items)

        def pytest_runtest_logreport(self, report: Any) -> None:
            if report.when == "call" or report.failed or report.skipped:
                reports.append({"nodeid": report.nodeid, "outcome": report.outcome,
                                "when": report.when, "reason": str(report.longrepr)
                                if report.failed or report.skipped else None})

        def pytest_deselected(self, items: Any) -> None:
            deselected.extend(i.nodeid for i in items)

    job = config["job"]
    started = datetime.now(UTC).isoformat()
    tick = time.monotonic()
    capture = io.StringIO()
    code = 1
    guard = None
    try:
        with contextlib.redirect_stdout(capture), contextlib.redirect_stderr(capture):
            if job in {"collection", "focused", "presence", "W", "A", "diagnostic", "guardlegacy"}:
                import pytest

                args = ["-q", "-p", "no:cacheprovider", "-p", "pytest_asyncio.plugin",
                        "--log-file", str(output / "pytest.log"), "--basetemp", str(output / "pytest")]
                if job == "collection":
                    args += ["--collect-only"]
                elif job == "focused":
                    args += ["tests/unit/test_od05x_isolation.py", "tests/unit/test_od05x_native_extensions.py"]
                elif job == "presence":
                    args += ["tests/unit/test_od05v_local_presence.py"]
                elif job == "W":
                    args += ["tests/unit/test_od05w_engineering.py"]
                elif job == "guardlegacy":
                    args += ["tests/unit/test_od02v_portability.py::test_v01_guard_denies_dns_tcp_udp_children_and_protected_writes"]
                else:
                    if job == "A":
                        inventory = json.loads(Path("od05x_inputs/runtime-inventory.json").read_bytes())
                        args += [n for n, c in inventory.items() if c == "A"]
                    else:
                        args += ["-m", "not realdata"]
                    args += ["-p", "pytest_cov.plugin", "--cov=omegadata", "--cov-branch",
                             "--cov-report=json:/work/job/coverage.json", "--cov-report=term-missing"]
                # X tests exercise the live kernel boundary and writable canaries.
                # Existing suites additionally require their historical Python guard contract.
                if job != "focused":
                    guard = python_guard(output)
                code = int(pytest.main(args, plugins=[Evidence()]))
            elif job == "mypy":
                from mypy import api

                stdout, stderr, code = api.run(["src/omegadata"])
                print(stdout, stderr)
            elif job == "pip":
                sys.argv = ["pip", "check", "--disable-pip-version-check"]
                try:
                    runpy.run_module("pip", run_name="__main__")
                    code = 0
                except SystemExit as error:
                    code = int(error.code or 0)
            elif job == "compile":
                import compileall

                code = 0 if all(compileall.compile_dir(n, quiet=1, force=True) for n in ("src/omegadata", "scripts")) else 1
            elif job == "environment":
                print(json.dumps({"python": sys.version, "executable": sys.executable,
                                  "packages": sorted((d.metadata["Name"], d.version)
                                                     for d in importlib.metadata.distributions())}))
                code = 0
            elif job == "profile":
                from omegadata.parsers.archive_candidate_inventory import (
                    ExpectedMetadata,
                    InventoryError,
                )
                from omegadata.parsers.local_archive_presence import scan_presence

                groups = json.loads(Path("od05v_inputs/groups.json").read_bytes())
                profiles = {}
                guard = python_guard(output)
                for label, group in groups.items():
                    profile = {}
                    result = scan_presence(Path("/work/NON_MARKET_CANARY"), label,
                        expected=ExpectedMetadata(tuple(tuple(r) for r in group["entries"])),
                        version=2, profile=profile)
                    profiles[label] = {"profile": profile, "counts": result["counts"],
                                       "class": "NON_MARKET_CANARY", "financial_rows": 0}
                parent = output / "stress"
                parent.mkdir()
                repo, pins, meta = launcher.small_canary(parent)
                events: list[dict[str, Any]] = []
                observation = launcher.CanaryObservation(repo, "seed", pins, events)
                for _ in range(100):
                    observation.get()
                import threading

                threads = [threading.Thread(target=observation.get) for _ in range(8)]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join()
                before = observation.scan_count
                meta.write_bytes(meta.read_bytes() + b" ")
                try:
                    observation.get()
                    raise ValueError("MUTATION_NOT_REFUSED")
                except InventoryError as error:
                    assert error.reason_code == "INPUT_CHANGED"
                save(output / "identity-diagnostics.json", {"events": events,
                    "serial_reads": 100, "concurrent_readers": 8, "scan_count": before,
                    "historical_Windows_cause": "INPUT_CHANGED_ROOT_CAUSE_UNKNOWN"})
                save(output / "native-profile.json", profiles)
                code = 0
            else:
                raise ValueError("UNREVIEWED_JOB")
    except Exception:
        import traceback

        capture.write(traceback.format_exc())
    # Evidence output is a fresh location outside the guard's protected code root.
    result = {"job": job, "start_utc": started, "end_utc": datetime.now(UTC).isoformat(),
              "elapsed_seconds": time.monotonic() - tick, "exit_code": code,
              "interpreter": sys.executable, "python": sys.version, "stdout_stderr": capture.getvalue(),
              "collected": collected, "reports": reports, "deselected": deselected,
              "counts": dict(Counter(r["outcome"] for r in reports)),
              "guard_denials": dict(guard) if guard is not None else {},
              "boundary": launcher.assert_boundary()}
    save(output / "result.json", result)
    print(json.dumps({k: v for k, v in result.items() if k in {"job", "exit_code", "counts"}}))
    return code
