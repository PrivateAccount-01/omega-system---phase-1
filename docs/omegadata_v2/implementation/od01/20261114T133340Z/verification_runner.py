"""OD-01 reproducible offline verification; no source collection or secret reads."""
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
PYTHON = str(ROOT / ".venv/Scripts/python.exe")

def stamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def dump(name, value):
    (EVIDENCE / "logs" / name).write_text(json.dumps(value, indent=2), encoding="utf-8")

def snapshot():
    tracked = subprocess.check_output(["git", "ls-files", "-z"]).decode().split("\0")
    paths = {Path(p) for p in tracked if p}
    for folder in ("data", "artifacts"):
        paths.update(p for p in Path(folder).rglob("*") if p.is_file())
    paths.update(ROOT.glob("*.db"))
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
            row["sha256"] = hashlib.file_digest(p.open("rb"), "sha256").hexdigest()
        result[relative.as_posix()] = row
    return result

def preflight():
    rows = []
    for cmd in [
        ["git", "rev-parse", "--show-toplevel"], ["git", "branch", "--show-current"],
        ["git", "rev-parse", "HEAD"], ["git", "status", "--short"],
        ["git", "log", "-4", "--oneline"], ["git", "diff", "--stat"],
        ["git", "diff", "--name-only"], [PYTHON, "--version"],
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
    root = Path(tempfile.mkdtemp(prefix="od01-offline-"))
    os.environ["OMEGA_DB_URL"] = "sqlite:///" + str(root / "default.sqlite")
    for key, value in {"PARQUET_ROOT":"parquet", "RAW_ROOT":"raw", "SEED_RAW_ROOT":"seed",
         "REPORT_ROOT":"reports", "REPROCESS_ROOT":"reprocess", "RELEASE_ROOT":"releases",
         "RELEASE_GPG_HOME":"gnupg"}.items():
        os.environ["OMEGA_" + key] = str(root / value)
    os.environ["OMEGA_VERIFICATION_DB_URL"] = "sqlite:///" + str(root / "verification.sqlite")
    os.environ["OMEGA_ALERT_WEBHOOK_URL"] = ""
    os.environ["COVERAGE_FILE"] = str(EVIDENCE / "logs" / (label + ".coverage"))
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
    def audit(event, args):
        if event == "subprocess.Popen":
            deny()
    sys.addaudithook(audit)
    import pytest
    return pytest.main(args + ["-p", "no:cacheprovider", "--basetemp", str(root / "pytest")])

def main():
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(ROOT / "src"))
    label = sys.argv[1]
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
    with path.open("w", encoding="utf-8") as log:
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
                               env={**os.environ, "MYPY_CACHE_DIR":str(Path(tempfile.gettempdir())/"od01-mypy")})
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

