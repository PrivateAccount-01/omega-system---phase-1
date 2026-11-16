"""OD-02V cross-platform offline test runner. Fresh logs, disposable writes only."""
from __future__ import annotations

import contextlib
import gc
import hashlib
import importlib.metadata
import json
import os
import platform
import socket
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

HERE=Path(__file__).resolve().parent
LOGS=HERE/"logs"


def save(name,value):
    with (LOGS/name).open("x",encoding="utf-8") as handle:
        json.dump(value,handle,indent=2)


def tests(label,root,args):
    platform.uname()  # Windows stdlib's OS inventory may invoke a child once.
    sandbox=Path(tempfile.mkdtemp(prefix="omega-od02v-tests-",dir="/tmp" if os.name!="nt" else None)).resolve()
    os.environ["TMP"]=os.environ["TEMP"]=os.environ["TMPDIR"]=str(sandbox)
    tempfile.tempdir=str(sandbox)
    for key,value in {"DB_URL":"sqlite:///"+str(sandbox/"default.sqlite"),
        "VERIFICATION_DB_URL":"sqlite:///"+str(sandbox/"verification.sqlite"),
        "ALERT_WEBHOOK_URL":"", "API_KEY":"SYNTHETIC_TEST_ONLY", "RELEASE_GPG_KEY_ID":""}.items():
        os.environ["OMEGA_"+key]=value
    for key,value in {"RAW_ROOT":"raw","SEED_RAW_ROOT":"seed","PARQUET_ROOT":"parquet",
        "REPORT_ROOT":"reports","REPROCESS_ROOT":"reprocess","RELEASE_ROOT":"releases","RELEASE_GPG_HOME":"gnupg"}.items():
        os.environ["OMEGA_"+key]=str(sandbox/value)
    os.environ["OD01R_DISPOSABLE_ROOT"]=os.environ["OD02V_DISPOSABLE_ROOT"]=str(sandbox)
    os.environ["OD02V_WORKTREE"]=str(root)
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"]="1"
    os.environ["COVERAGE_FILE"]=str(sandbox/"coverage.db")
    sys.path.insert(0,str(root/"src"))
    active=True
    local=threading.local()
    original_pair=socket.socketpair
    original_connect=socket.socket.connect
    denials=Counter()

    def deny(kind):
        denials[kind]+=1
        raise RuntimeError("OD02V_BLOCKED_"+kind)

    def connection(self,address):
        if getattr(local,"internal_pair",False) and os.name=="nt":
            # CPython Windows constructs socketpair with loopback listener;
            # scope is synchronous/thread-local around stdlib socketpair only.
            return original_connect(self,address)
        return deny("SOCKET")

    def pair(*args,**kwargs):
        local.internal_pair=True
        try:return original_pair(*args,**kwargs)
        finally:local.internal_pair=False

    socket.socket.connect=connection
    socket.socket.connect_ex=lambda *a,**kw:deny("SOCKET")
    socket.socket.sendto=lambda *a,**kw:deny("UDP")
    if hasattr(socket.socket,"sendmsg"):
        socket.socket.sendmsg=lambda *a,**kw:deny("UDP")
    socket.create_connection=lambda *a,**kw:deny("SOCKET")
    socket.getaddrinfo=lambda *a,**kw:deny("DNS")
    socket.socketpair=pair

    def descriptor_path(path,dir_fd=None):
        p=Path(os.fsdecode(path))
        if not p.is_absolute() and dir_fd not in (None,-1):
            if os.name=="nt":deny("UNSUPPORTED_DIR_FD")
            p=Path(os.readlink("/proc/self/fd/"+str(dir_fd)))/p
        return p

    def bounded(path,follow=True,dir_fd=None):
        if isinstance(path,int):return
        p=descriptor_path(path,dir_fd)
        target=p.resolve() if follow else p.parent.resolve()/p.name
        if not target.is_relative_to(sandbox):deny("PROTECTED_WRITE")

    original_open=os.open
    def descriptor_open(path,flags,mode=0o777,*,dir_fd=None):
        actual=descriptor_path(path,dir_fd)
        if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):bounded(actual)
        old=getattr(local,"descriptor_open",None)
        local.descriptor_open=actual
        try:return original_open(path,flags,mode,dir_fd=dir_fd)
        finally:local.descriptor_open=old
    os.open=descriptor_open

    def audit(event,args):
        if not active:return
        if event in {"subprocess.Popen","os.system","os.posix_spawn","os.spawn"}:deny("SUBPROCESS")
        if event in {"socket.connect","socket.bind"} and not (os.name=="nt" and getattr(local,"internal_pair",False)):deny("SOCKET")
        if event=="socket.getaddrinfo":deny("DNS")

        if event=="open":
            path,mode,flags=args
            path=getattr(local,"descriptor_open",None) or path
            if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):bounded(path)
            if not isinstance(path,int):
                p=Path(os.fsdecode(path))
                if "gnupg" in p.parts and not p.resolve().is_relative_to(sandbox):deny("SIGNING_READ")
        if event in {"os.remove","os.rmdir"}:bounded(args[0],False,args[1])
        if event in {"os.mkdir","os.chmod"}:bounded(args[0],dir_fd=args[2])
        if event=="os.utime":bounded(args[0],dir_fd=args[3])
        if event=="os.symlink":bounded(args[1],False,args[2])
        if event=="os.link":
            bounded(args[0],False,args[2])
            bounded(args[1],False,args[3])
        if event=="os.rename":
            bounded(args[0],False,args[2])
            bounded(args[1],False,args[3])
        if event=="sqlite3.connect" and args[0]!=":memory:":bounded(args[0])
    sys.addaudithook(audit)
    reports=[]
    deselected=[]
    symlink_observations=[]
    def observe(frame,event,arg):
        if event!="return" or frame.f_code.co_name not in {
            "test_r05_cache_escape_never_opens_external_sentinel","test_r06_real_symlink_payload_escape"
        }:return
        values=frame.f_locals
        if "reads" not in values:return
        reads=values["reads"]
        path=values.get("link") or values.get("pointer")
        symlink_observations.append({"function":frame.f_code.co_name,"form":values.get("form"),
            "seed":values.get("seed",False),"outside_read_calls":len(reads) if isinstance(reads,list) else reads.call_count,
            "is_actual_symlink":path.is_symlink(),"path":str(path)})
    class Evidence:
        def pytest_runtest_logreport(self,report):
            if report.when=="call" or report.failed or report.skipped:
                reports.append({"nodeid":report.nodeid,"when":report.when,"outcome":report.outcome,
                    "reason":str(report.longrepr) if report.failed or report.skipped else None})
        def pytest_deselected(self,items):
            deselected.extend(item.nodeid for item in items)
    try:
        import pytest
        extra=["-p","pytest_asyncio.plugin","-p","no:cacheprovider","--log-file",str(sandbox/"pytest.log"),"--basetemp",str(sandbox/"pytest")]
        if any(arg.startswith("--cov=") for arg in args):
            extra += ["-p","pytest_cov.plugin","--cov-report=json:"+str(sandbox/"coverage.json")]
        if "symlink-proof" in label:sys.setprofile(observe)
        try:result=pytest.main(args+extra,plugins=[Evidence()])
        finally:
            if "symlink-proof" in label:sys.setprofile(None)
        gc.collect()  # retain cleanup warnings within the captured command log
    finally:
        active=False
        os.open=original_open
    if (sandbox/"coverage.json").is_file():
        save(label+"-coverage.json",json.loads((sandbox/"coverage.json").read_text()))
    return int(result),{"sandbox":str(sandbox),"root":str(root),"guard_denials":dict(denials),
        "test_reports":reports,"deselected":deselected,"symlink_observations":symlink_observations,
        "call_counts":dict(Counter(r["outcome"] for r in reports if r["when"]=="call"))}


def main():
    sys.dont_write_bytecode=True
    os.environ["PYTHONDONTWRITEBYTECODE"]="1"
    label,worktree,module,*args=sys.argv[1:]
    root=Path(worktree).resolve()
    os.chdir(root)
    platform_name=platform.platform()  # warm complete Windows 3.11 CPU metadata
    started=datetime.now(UTC).isoformat()
    tick=time.monotonic()
    details={}
    with (LOGS/(label+".txt")).open("x",encoding="utf-8") as out, contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        try:
            if module=="pytest":code,details=tests(label,root,args)
            elif module=="environment":
                import runpy
                runpy.run_path(str(HERE/"environment_probe.py"),run_name="__main__")
                code=0
            else:
                # Static/package commands do not import/run application jobs.
                env={**os.environ,"MYPY_CACHE_DIR":tempfile.mkdtemp(prefix="omega-od02v-mypy-")}
                code=subprocess.run([sys.executable,"-B","-m",module,*args],stdout=out,stderr=subprocess.STDOUT,env=env).returncode
        except Exception:
            traceback.print_exc()
            code=1
    row={"command":[sys.executable,"-B",str(Path(__file__)),label,str(root),module,*args],"cwd":str(root),
        "baseline":"db087fb9ee12887d3d9c787b797bb6968ad45440","platform":platform_name,
        "python":sys.version,"start_utc":started,"end_utc":datetime.now(UTC).isoformat(),
        "elapsed_seconds":time.monotonic()-tick,"exit_code":code,"output":label+".txt",**details}
    save(label+".json",row)
    print(json.dumps({k:v for k,v in row.items() if k not in {"test_reports","deselected"}},indent=2))
    print((LOGS/(label+".txt")).read_text(encoding="utf-8")[-4000:])
    return code


if __name__=="__main__":raise SystemExit(main())
