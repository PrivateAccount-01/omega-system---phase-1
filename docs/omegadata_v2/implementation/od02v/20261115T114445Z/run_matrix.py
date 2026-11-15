"""Execute actual required gates on one explicitly selected runtime/copy."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
LOGS=HERE/"logs"
sys.path.insert(0,str(HERE))
import phase_control as ctl


def main():
    mode=sys.argv[1]
    reviewed=len(sys.argv)>2 and sys.argv[2]=="reviewed"
    prefix=mode+"-reviewed" if reviewed else mode
    if mode=="linux312":
        info=json.loads((LOGS/"linux-environment-paths.json").read_text())
        root=Path(info["copy"])
        py=info["python"]
        original=Path("/mnt/e/omega system - phase 1")
    else:
        info=json.loads((LOGS/"windows-environment-paths.json").read_text())
        root=Path(info["copy"])
        py=info["python"] if mode=="win311" else str(Path.cwd()/".venv/Scripts/python.exe")
        original=Path.cwd()
    new_paths=["src/omegadata/track_a/acquisition.py","src/omegadata/track_a/download_manager.py","tests/unit/test_od02v_portability.py"]
    rows=[]
    for name in new_paths:
        shutil.copyfile(original/name,root/name)
        rows.append({"path":name,"sha256":hashlib.sha256((root/name).read_bytes()).hexdigest()})
    # All other code/tests/config match reviewed HEAD; fixture allowlist is exact.
    copy=json.loads((LOGS/"sanitized-copy.json").read_text())
    for item in copy["files"]:
        p=Path(item["path"])
        if p.as_posix() in new_paths or any(part.endswith(".egg-info") for part in p.parts):continue
        assert hashlib.sha256((root/p).read_bytes()).hexdigest()==item["head_sha256"],str(p)
    ctl.save(prefix+"-tested-source.json",{"copy":str(root),"baseline":copy["baseline"],"overlays":rows,
        "all_other_source_test_config_match_head":True,"original_inherited_tests_unmodified":True})
    commands=[
        ("environment",["environment"]),
        ("pip-version",["pip","--version"]),
        ("freeze",["pip","freeze","--all"]),
        ("collection",["pytest","--collect-only","-q","-m","not realdata"]),
        ("targeted",["pytest","-q","tests/unit/test_od01_source_rights.py","tests/unit/test_od01r_rights_hardening.py","tests/unit/test_od02_acquisition.py","tests/unit/test_od02v_portability.py","-m","not realdata"]),
        ("full",["pytest","-q","-m","not realdata","--cov=omegadata","--cov-branch","--cov-report=term-missing"]),
        ("ruff",["ruff","check","--no-cache","src/omegadata","tests","scripts"]),
        ("mypy",["mypy","src/omegadata"]),
        ("pip-check",["pip","check"]),
    ]
    results=[]
    for label,args in commands:
        if reviewed and label not in {"collection","targeted","full"}:continue
        command=[py,"-B",str(HERE/"verification_runner.py"),prefix+"-"+label,str(root),*args]
        # Child stdout already points to its exclusive raw log/JSON. Preserve
        # launcher stdout too for errors that precede its own logging setup.
        launch=LOGS/(prefix+"-"+label+"-launcher.txt")
        with launch.open("x",encoding="utf-8") as out:
            result=subprocess.run(command,cwd=root,stdout=out,stderr=subprocess.STDOUT,
                env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1","PIP_DISABLE_PIP_VERSION_CHECK":"1"})
        results.append({"gate":label,"exit_code":result.returncode})
        print(json.dumps({"runtime":mode,"gate":label,"exit_code":result.returncode}),flush=True)
    ctl.save(prefix+"-matrix.json",{"runtime":mode,"results":results,"no_ignored_failures":True})
    return max(r["exit_code"] for r in results)


if __name__=="__main__":
    sys.dont_write_bytecode=True
    raise SystemExit(main())
