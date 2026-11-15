"""OD-02V exclusive command logs and read-only preservation/copy control."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT=Path.cwd()
HERE=Path(__file__).resolve().parent
LOGS=HERE/"logs"
EXPECTED="eaedac1bddc35867f9089486beffa3bb38cb11f4"


def save(name,value):
    with (LOGS/name).open("x",encoding="utf-8") as out:
        json.dump(value,out,indent=2)


def command(label,args,cwd=None):
    started=datetime.now(UTC).isoformat()
    tick=time.monotonic()
    with (LOGS/(label+".txt")).open("x",encoding="utf-8") as out:
        result=subprocess.run(args,cwd=cwd or ROOT,stdout=out,stderr=subprocess.STDOUT,
            env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1","PIP_DISABLE_PIP_VERSION_CHECK":"1"})
    row={"label":label,"command":args,"cwd":str(cwd or ROOT),"start_utc":started,
        "end_utc":datetime.now(UTC).isoformat(),"elapsed_seconds":time.monotonic()-tick,
        "exit_code":result.returncode,"output":label+".txt"}
    save(label+".json",row)
    print(json.dumps(row,indent=2))
    print((LOGS/(label+".txt")).read_text(encoding="utf-8")[-3500:])
    return result.returncode


def snapshot():
    spec=importlib.util.spec_from_file_location("old_runner",ROOT/"docs/omegadata_v2/implementation/od02/20261115T084441Z/verification_runner.py")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    records=module.snapshot()
    prompt=ROOT/"OMEGADATA_OD02V_CODEX_PROMPT_2026-11-15.md"
    records[prompt.name]={"length":prompt.stat().st_size,"sha256":hashlib.sha256(prompt.read_bytes()).hexdigest()}
    return records


def preflight():
    assert subprocess.check_output(["git","rev-parse","HEAD"]).decode().strip()==EXPECTED
    assert subprocess.check_output(["git","branch","--show-current"]).decode().strip()=="feature/od01-source-rights"
    for label,args in [
        ("git-root",["git","rev-parse","--show-toplevel"]),
        ("git-branch",["git","branch","--show-current"]),
        ("git-head",["git","rev-parse","HEAD"]),
        ("git-status-before",["git","status","--porcelain=v1","-uall"]),
        ("git-main-diff",["git","diff","--name-status","main...HEAD"]),
        ("git-log",["git","log","-5","--date=iso-strict","--pretty=fuller"]),
        ("git-main",["git","rev-parse","main"]),
        ("win314-before",[sys.executable,"-B",str(HERE/"environment_probe.py")]),
        ("win314-pip",[sys.executable,"-m","pip","--version"]),
        ("win314-cache",[sys.executable,"-m","pip","cache","info"]),
    ]:
        command(label,args)
    save("preservation-before.json",snapshot())
    print("Original non-secret content hashes and signing metadata frozen.")


def sanitized_copy():
    target=Path(tempfile.mkdtemp(prefix="omega-od02v-copy-"))/"repo"
    target.mkdir()
    tracked=subprocess.check_output(["git","ls-files","-z"]).decode().split("\0")
    rows=[]
    for value in tracked:
        p=Path(value)
        # Allowlist only code/config and reviewed test fixture tree. No data,
        # operational databases, artifacts, keys, environments, .env or history.
        if not value or not (p.parts[0] in {"src","scripts","tests","config"} or value in {"pyproject.toml","README.md"}):
            continue
        if any(part in {"__pycache__",".env","gnupg"} for part in p.parts):
            raise RuntimeError("Disallowed copy path")
        body=(ROOT/p).read_bytes()
        original=subprocess.check_output(["git","show",EXPECTED+":"+p.as_posix()])
        # Windows working-tree CRLF is equivalent; copy exact HEAD blob for
        # identical sanitized source/test checksums on every platform.
        if body.replace(b"\r\n",b"\n") != original.replace(b"\r\n",b"\n"):
            raise RuntimeError("Unexpected source drift: "+str(p))
        out=target/p
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_bytes(original)
        rows.append({"path":p.as_posix(),"head_sha256":hashlib.sha256(original).hexdigest(),"bytes":len(original)})
    constraints=[]
    import importlib.metadata
    for package in importlib.metadata.distributions():
        name=package.metadata["Name"]
        if name.lower()!="omegadata":
            constraints.append(name+"=="+package.version)
    constraint_path=target.parent/"working-environment-constraints.txt"
    constraint_path.write_text("\n".join(sorted(constraints))+"\n",encoding="utf-8")
    save("sanitized-copy.json",{"baseline":EXPECTED,"windows_copy":str(target),"constraints":str(constraint_path),
        "files":rows,"allowed":"src/scripts/tests/config, pyproject and README only; exact HEAD blobs",
        "excluded":"all data/artifacts/gnupg/.env/databases/environments/history; fixtures only under reviewed tests tree"})
    print(json.dumps({"windows_copy":str(target),"constraints":str(constraint_path),"files":len(rows)}))


if __name__=="__main__":
    sys.dont_write_bytecode=True
    if sys.argv[1]=="preflight":preflight()
    elif sys.argv[1]=="copy":sanitized_copy()
    else:raise SystemExit(command(sys.argv[1],sys.argv[2:]))
