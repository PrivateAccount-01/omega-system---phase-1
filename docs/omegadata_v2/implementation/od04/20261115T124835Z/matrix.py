"""Sequential source freezing and actual required command exits on one runtime."""
from __future__ import annotations
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
LOGS=HERE/'logs'
ROOT=Path('/mnt/e/omega system - phase 1') if os.name!='nt' else Path.cwd()
CHANGES=['src/omegadata/track_a/raw_archive.py','src/omegadata/track_a/download_manager.py',
    'tests/unit/test_od04_raw_archive.py','scripts/verify_raw_archive.py','scripts/plan_legacy_raw_import.py']

def main():
    label,copy,*only=sys.argv[1:];copy=Path(copy)
    hashes={}
    for name in CHANGES:
        shutil.copyfile(ROOT/name,copy/name)
        hashes[name]=hashlib.sha256((copy/name).read_bytes()).hexdigest()
        assert hashes[name]==hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    with (LOGS/(label+'-source.json')).open('x') as out:json.dump(hashes,out,indent=2)
    commands=[('environment',['environment']),('collection',['pytest','--collect-only','-q','-m','not realdata']),
        ('targeted',['pytest','-q','tests/unit/test_od01_source_rights.py','tests/unit/test_od01r_rights_hardening.py',
            'tests/unit/test_od02_acquisition.py','tests/unit/test_od02v_portability.py','tests/unit/test_od04_raw_archive.py','-m','not realdata']),
        ('full',['pytest','-q','-m','not realdata','--cov=omegadata','--cov-branch','--cov-report=term-missing']),
        ('ruff',['ruff','check','--no-cache','src/omegadata','tests','scripts']),
        ('mypy',['mypy','src/omegadata']),('pip',['pip','check'])]
    results=[]
    for gate,args in commands:
        if only and gate not in only:continue
        command=[sys.executable,'-B',str(HERE/'verification_runner.py'),label+'-'+gate,str(copy),*args]
        with (LOGS/(label+'-'+gate+'-launcher.txt')).open('x') as out:
            result=subprocess.run(command,cwd=copy,stdout=out,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        results.append({'gate':gate,'exit_code':result.returncode})
        print(label,gate,result.returncode,flush=True)
    with (LOGS/(label+'-matrix.json')).open('x') as out:json.dump(results,out,indent=2)
    return max(x['exit_code'] for x in results)

if __name__=='__main__':raise SystemExit(main())
