"""OD-01R offline evidence runner; unique labels, bounded test writes, no provider egress."""
from __future__ import annotations
import contextlib
import datetime
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path.cwd()
EVIDENCE = Path(__file__).resolve().parent
PYTHON = sys.executable

def stamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def dump(name, value):
    with (EVIDENCE / "logs" / name).open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(value, indent=2))

def snapshot():
    tracked = subprocess.check_output(["git", "ls-files", "-z"]).decode().split("\0")
    paths = {Path(p) for p in tracked if p}
    for folder in ("data", "artifacts"):
        paths.update(p for p in Path(folder).rglob("*") if p.is_file())
    paths.update(ROOT.glob("*.db"))
    paths.add(Path("OMEGADATA_OD01R_CODEX_REMEDIATION.md"))
    result = {}
    for p in sorted(paths):
        if not p.is_file():
            continue
        relative = p.relative_to(ROOT) if p.is_absolute() else p
        info = p.stat()
        row = {"length": info.st_size}
        if relative.parts[:2] == ("artifacts", "gnupg"):
            row["mtime_ns"] = info.st_mtime_ns  # metadata only; NEVER open signing files
        else:
            with p.open("rb") as handle:
                row["sha256"] = hashlib.file_digest(handle, "sha256").hexdigest()
        result[relative.as_posix()] = row
    return result

def preflight():
    rows = []
    for cmd in [
        ["git", "rev-parse", "--show-toplevel"], ["git", "branch", "--show-current"],
        ["git", "rev-parse", "HEAD"], ["git", "status", "--short"],
        ["git", "log", "-4", "--oneline"], ["git", "diff", "--stat"],
        ["git", "diff", "--name-only"], [PYTHON, "--version"],
        ["git", "remote", "-v"], ["git", "merge-base", "main", "HEAD"],
        ["git", "diff", "--stat", "main...HEAD"],
        ["git", "ls-files", "artifacts/gnupg/**"],
        [PYTHON, "-m", "pip", "list", "--format=json"],
        [PYTHON, "-m", "pytest", "--version"], [PYTHON, "-m", "ruff", "--version"],
        [PYTHON, "-m", "mypy", "--version"],
    ]:
        started = stamp()
        r = subprocess.run(cmd, capture_output=True, text=True)
        rows.append({"command": cmd, "cwd": str(ROOT), "start_utc": started,
                     "end_utc": stamp(), "exit_code": r.returncode,
                     "stdout": r.stdout, "stderr": r.stderr})
    dump("preflight.json", {"utc": stamp(), "platform": platform.platform(),
         "shell": "Windows PowerShell 5.1", "commands": rows,
         "packages": {name: importlib.metadata.version(name) for name in
          ("pydantic", "pydantic-settings", "pytest", "ruff", "mypy", "coverage", "httpx")}})
    dump("preservation-before.json", snapshot())
    print("Preflight saved; preservation snapshot complete.")
    return max(r["exit_code"] for r in rows)

def pytest_run(label, args):
    platform.uname()  # warm stdlib Windows OS-query cache before subprocess denial
    root = Path(tempfile.mkdtemp(prefix="od01r-offline-" )).resolve()
    os.environ["TMP"] = os.environ["TEMP"] = str(root)
    tempfile.tempdir = str(root)
    os.environ["OD01R_DISPOSABLE_ROOT"] = str(root)
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    os.environ["OMEGA_DB_URL"] = "sqlite:///" + str(root / "default.sqlite")
    for key, value in {"PARQUET_ROOT":"parquet", "RAW_ROOT":"raw", "SEED_RAW_ROOT":"seed",
         "REPORT_ROOT":"reports", "REPROCESS_ROOT":"reprocess", "RELEASE_ROOT":"releases",
         "RELEASE_GPG_HOME":"gnupg"}.items():
        os.environ["OMEGA_" + key] = str(root / value)
    os.environ["OMEGA_VERIFICATION_DB_URL"] = "sqlite:///" + str(root / "verification.sqlite")
    os.environ["OMEGA_ALERT_WEBHOOK_URL"] = ""
    os.environ["COVERAGE_FILE"] = str(root / "coverage.db")
    original_connect, original_pair = socket.socket.connect, socket.socketpair
    local = threading.local()
    def connect(self, address):
        if getattr(local, "creating_pair", False):
            return original_connect(self, address)
        raise RuntimeError("OD-01 forbids network and service sockets")
    def pair(*a, **kw):
        local.creating_pair = True
        try:
            return original_pair(*a, **kw)
        finally:
            local.creating_pair = False
    def deny(*a, **kw):
        raise RuntimeError("OD-01 forbids network or subprocess side effects during tests")
    socket.socket.connect = connect
    socket.socket.connect_ex = deny
    socket.create_connection = deny
    socket.socket.sendto = deny
    socket.socketpair = pair
    guard_active = True
    def audit(event, args):
        if not guard_active:
            return
        if event in {"subprocess.Popen", "os.system", "os.posix_spawn", "os.spawn"}:
            deny()
        if event == "socket.connect" and not getattr(local, "creating_pair", False):
            deny()
        if event == "socket.getaddrinfo":
            deny()
        def bounded(path):
            if isinstance(path, int):
                return
            target = Path(os.fsdecode(path)).resolve()
            if not target.is_relative_to(root):
                raise RuntimeError("OD-01R forbids writes outside disposable test root")
        if event == "open":
            path, mode, flags = args
            if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                bounded(path)
        if event in {"os.remove", "os.rmdir", "os.mkdir", "os.chmod", "os.utime", "os.symlink", "os.link"}:
            bounded(args[1] if event in {"os.symlink", "os.link"} else args[0])
        if event == "os.rename":
            bounded(args[0])
            bounded(args[1])
        if event == "sqlite3.connect" and args[0] != ":memory:":
            bounded(args[0])
    sys.addaudithook(audit)
    try:
        import pytest
        extra = []
        if any(arg.startswith("--cov=") for arg in args):
            extra = ["-p", "pytest_cov.plugin", "--cov-report=json:" + str(root / "coverage.json")]
        result = pytest.main(args + extra + ["-p", "pytest_asyncio.plugin", "-p", "no:cacheprovider", "--log-file", str(root / "pytest.log"), "--basetemp", str(root / "pytest")])
    finally:
        guard_active = False
    if (root / "coverage.json").is_file():
        dump(label + "-coverage.json", json.loads((root / "coverage.json").read_text()))
    return result

def main():
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(ROOT / "src"))
    label = sys.argv[1]
    if label.endswith("environment"):
        dump(label + ".json", {"utc":stamp(), "python":sys.version, "executable":sys.executable,
            "platform":platform.platform(), "cpu_count":os.cpu_count(),
            "packages":{p.metadata["Name"]:p.version for p in importlib.metadata.distributions()}})
        print("Environment metadata saved; no imports, install or provider requests.")
        return 0
    if label == "preflight":
        return preflight()
    if label == "preserve":
        before = json.loads((EVIDENCE/"logs/preservation-before.json").read_text())
        after = snapshot()
        changes = {p: {"before": v, "after": after.get(p)} for p,v in before.items()
                   if after.get(p) != v}
        dump("preservation-after.json", {"utc":stamp(), "checked":len(before),
             "changes":changes, "note":"Signing paths checked by metadata only; secrets never opened."})
        print(json.dumps({"checked":len(before), "changes":list(changes)}, indent=2))
        return 0
    started = stamp()
    tick = time.perf_counter()
    command = sys.argv[2:]
    path = EVIDENCE / "logs" / (label + ".txt")
    with path.open("x", encoding="utf-8") as log:
        if command[0] == "pytest":
            with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                try:
                    code = pytest_run(label, command[1:])
                except Exception:
                    import traceback
                    traceback.print_exc()
                    code = 1
        else:
            r = subprocess.run([PYTHON, "-B", "-m", *command], stdout=log, stderr=subprocess.STDOUT,
                               env={**os.environ, "MYPY_CACHE_DIR":tempfile.mkdtemp(prefix="od01r-mypy-")})
            code = r.returncode
    result = {"command": [PYTHON, "-B", str(Path(__file__)), label, *command],
              "effective_module":command, "cwd":str(ROOT), "start_utc":started,
              "end_utc":stamp(), "elapsed_seconds":time.perf_counter()-tick,
              "exit_code":int(code), "output":path.name,
              "guard":"pytest: sockets/subprocess blocked, internal Windows socketpair allowed; disposable paths"}
    dump(label + ".json", result)
    print(json.dumps(result, indent=2))
    print(path.read_text(encoding="utf-8")[-6000:])
    return int(code)

if __name__ == "__main__":
    raise SystemExit(main())

