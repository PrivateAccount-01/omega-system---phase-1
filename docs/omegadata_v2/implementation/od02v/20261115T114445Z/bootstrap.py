"""Isolated official-index-only dependency setup; never import application code."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import phase_control as ctl


def windows():
    info=json.loads((HERE/"logs/sanitized-copy.json").read_text())
    base="C:/Users/Paril Rupani/AppData/Roaming/uv/python/cpython-3.11-windows-x86_64-none/python.exe"
    assert Path(base).is_file()
    ctl.command("win311-before",[base,"-B",str(HERE/"environment_probe.py")])
    parent=Path(info["windows_copy"]).parent
    env=parent/"venv311"
    assert ctl.command("win311-create",[base,"-m","venv",str(env)])==0
    py=str(env/"Scripts/python.exe")
    ctl.command("win311-cache",[py,"-m","pip","cache","info"])
    args=[py,"-m","pip","--isolated","install","--dry-run","--no-index","--only-binary=:all:","-c",info["constraints"],"-e",info["windows_copy"]+"[dev]"]
    local=ctl.command("win311-cache-resolution",args)
    args=[py,"-m","pip","--isolated","install","--index-url","https://pypi.org/simple","--only-binary=:all:","-c",info["constraints"],"-e",info["windows_copy"]+"[dev]"]
    installed=ctl.command("win311-install",args)
    ctl.save("windows-environment-paths.json",{"python":py,"copy":info["windows_copy"],"cache_only_exit":local,"install_exit":installed,"source":"https://pypi.org/simple; pip built-in cache reused where available"})
    return installed


def linux():
    # Executed by native Linux Python on the original read-only evidence script.
    info=json.loads((HERE/"logs/sanitized-copy.json").read_text())
    source=Path("/mnt/c")/Path(info["windows_copy"].replace("\\","/").split(":",1)[1].lstrip("/"))
    constraints=source.parent/"working-environment-constraints.txt"
    # This WSL host clears /tmp on distribution restart. A fresh native home
    # directory persists across command invocations without touching user files.
    parent=Path(tempfile.mkdtemp(prefix="omega-od02v-",dir=str(Path.home())))
    target=parent/"repo"
    shutil.copytree(source,target)
    copied_constraints=parent/"working-environment-constraints.txt"
    shutil.copyfile(constraints,copied_constraints)
    ctl.command("linux312-before",[sys.executable,"-B",str(HERE/"environment_probe.py")],cwd=target)
    env=parent/"venv312"
    made=ctl.command("linux312-create",[sys.executable,"-m","venv",str(env)],cwd=target)
    py=str(env/"bin/python")
    if made:
        # Debian may omit ensurepip. Existing local pip can manage a fresh
        # --without-pip venv; install pip from the official index as runner setup.
        assert ctl.command("linux312-create-without-pip",[sys.executable,"-m","venv","--without-pip",str(env)],cwd=target)==0
        existing=Path("/mnt/e/omega system - phase 1/.venv-linux/bin/python")
        assert existing.is_file()
        assert ctl.command("linux312-pip-bootstrap",[str(existing),"-m","pip","--isolated","--python",py,"install","--index-url","https://pypi.org/simple","pip==26.0.1"],cwd=target)==0
    ctl.command("linux312-cache",[py,"-m","pip","cache","info"],cwd=target)
    local=ctl.command("linux312-cache-resolution",[py,"-m","pip","--isolated","install","--dry-run","--no-index","--only-binary=:all:","-c",str(copied_constraints),"-e",str(target)+"[dev]"],cwd=target)
    result=ctl.command("linux312-install",[py,"-m","pip","--isolated","install","--index-url","https://pypi.org/simple","--only-binary=:all:","-c",str(copied_constraints),"-e",str(target)+"[dev]"],cwd=target)
    return finish_linux(info,target,py,local,result)


def finish_linux(info,target,py,local,result):
    rows=[]
    import hashlib
    for row in info["files"]:
        actual=hashlib.sha256((target/row["path"]).read_bytes()).hexdigest()
        generated=any(part.endswith(".egg-info") for part in Path(row["path"]).parts)
        assert actual==row["head_sha256"] or generated,row["path"]
        rows.append({"path":row["path"],"matches_head":actual==row["head_sha256"],"generated_package_metadata":generated})
    ctl.save("linux-environment-paths.json",{"python":py,"copy":str(target),"cache_only_exit":local,
        "install_exit":result,"files_match_head":rows,"native_filesystem":True,"source":"https://pypi.org/simple; no source/provider requests"})
    return result


if __name__=="__main__":
    sys.dont_write_bytecode=True
    if sys.argv[1]=="linux-v2":
        original_command=ctl.command
        ctl.command=lambda label,args,cwd=None:original_command(label.replace("linux312","linux312-v2"),args,cwd)
    if sys.argv[1]=="linux-finalize":
        info=json.loads((HERE/"logs/sanitized-copy.json").read_text())
        installed=json.loads((HERE/"logs/linux312-install.json").read_text())
        target=Path(installed["cwd"])
        result=finish_linux(info,target,str(target.parent/"venv312/bin/python"),1,installed["exit_code"])
    else:
        result=windows() if sys.argv[1]=="windows" else linux()
    raise SystemExit(result)
