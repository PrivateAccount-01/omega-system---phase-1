"""OD-04 exclusive logs, clean copies and original-file preservation."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

sys.dont_write_bytecode = True
ROOT=Path.cwd()
HERE=Path(__file__).resolve().parent
LOGS=HERE/'logs'
OLD=ROOT/'docs/omegadata_v2/implementation/od02v/20261115T114445Z'
HEAD='44090a42958869faaab57a42b65f7ad8571d924d'

def save(name, value):
    with (LOGS/name).open('x',encoding='utf-8') as out:json.dump(value,out,indent=2)

def command(label,args,cwd=None):
    start=datetime.now(UTC).isoformat(); tick=time.monotonic()
    with (LOGS/(label+'.txt')).open('x',encoding='utf-8') as out:
        rc=subprocess.run(args,cwd=cwd or ROOT,stdout=out,stderr=subprocess.STDOUT,
            env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'}).returncode
    save(label+'.json',dict(command=args,cwd=str(cwd or ROOT),start_utc=start,
        end_utc=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-tick,exit_code=rc))
    print(label,rc,flush=True)
    return rc

def snapshot():
    spec=importlib.util.spec_from_file_location('oldcontrol',OLD/'phase_control.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod.snapshot()

def preflight():
    LOGS.mkdir(exist_ok=False)
    assert subprocess.check_output(['git','rev-parse','HEAD']).decode().strip()==HEAD
    for name,args in [('root',['rev-parse','--show-toplevel']),('branch',['branch','--show-current']),
        ('head',['rev-parse','HEAD']),('status',['status','--porcelain=v1']),('diff',['diff','--stat']),
        ('history',['log','-5','--oneline']),('main',['rev-parse','main'])]:
        assert command('git-'+name,['git',*args])==0
    save('preservation-before.json',snapshot())
    body=(ROOT/'docs/omegadata_v2/implementation/od04/20261115T124835Z/verification_runner.py').read_text()
    body=body.replace('d24e9cfd29c8a59e590aaee85983babe9e8bf182',HEAD)
    # Egress and protected-path audit logic remains byte-for-byte unchanged.
    (HERE/'verification_runner.py').write_text(body,encoding='utf-8')
    shutil.copyfile(OLD/'environment_probe.py',HERE/'environment_probe.py')
    target=Path(tempfile.mkdtemp(prefix='omega-od04r-copy-'))/'repo';target.mkdir()
    rows=[]
    for value in subprocess.check_output(['git','ls-files','-z']).decode().split('\0'):
        p=Path(value)
        if not value or not (p.parts[0] in {'src','scripts','tests','config'} or value in {'pyproject.toml','README.md'}):continue
        raw=subprocess.check_output(['git','show',HEAD+':'+p.as_posix()])
        out=target/p;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(raw)
        rows.append(dict(path=p.as_posix(),sha256=hashlib.sha256(raw).hexdigest()))
    fixtures=json.loads((OLD/'logs/fixture-allowlist.json').read_text())['files']
    for row in fixtures:
        p=Path(row['path']);raw=(ROOT/p).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==row['sha256']
        out=target/p;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(raw)
    save('copy.json',dict(root=str(target),files=rows,fixture_allowlist=fixtures))
    print(target,flush=True)

if __name__=='__main__':
    if sys.argv[1]=='preflight':preflight()
    elif sys.argv[1]=='command':raise SystemExit(command(sys.argv[2],sys.argv[3:]))
