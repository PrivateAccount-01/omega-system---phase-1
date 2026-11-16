"""Fresh runtime matrix on disposable source copies; no original payload copies."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
LOGS=HERE/'logs'

def main(label, root, original):
    root=Path(root)
    commands=[('environment','environment',[]),
      ('collection','pytest',['--collect-only','-q','-m','not realdata']),
      ('focused','pytest',['-q','tests/unit/test_od05v_local_presence.py']),
      ('full','pytest',['-q','-m','not realdata','--cov=omegadata','--cov-branch','--cov-report=term-missing']),
      ('guard','pytest',['-q',str(HERE/'guard_probe.py')]),
      ('ruff','ruff',['check','--no-cache','src/omegadata','tests','scripts']),
      ('mypy','mypy',['src/omegadata']),('pip','pip',['check']),
      ('compile','compileall',['-q','src/omegadata','scripts'])]
    results={}
    for name,module,args in commands:
        stamp=label+'-'+name
        identities={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
              for folder in ('src','tests','scripts','config') for p in (root/folder).rglob('*')
              if p.is_file() and '__pycache__' not in p.parts}
        with (LOGS/(stamp+'-inputs.json')).open('x',encoding='utf-8') as f:json.dump(identities,f,indent=2)
        cmd=[sys.executable,'-B',str(HERE/'verification_runner.py'),stamp,str(root),module,*args]
        with (LOGS/(stamp+'-launcher.txt')).open('x',encoding='utf-8') as out:
            result=subprocess.run(cmd,stdout=out,stderr=subprocess.STDOUT,env={**os.environ,'OD05V_ORIGINAL':original})
        results[name]=result.returncode
        print(stamp,result.returncode,flush=True)
    with (LOGS/(label+'-matrix.json')).open('x',encoding='utf-8') as f:json.dump(results,f,indent=2)
    return int(any(results.values()))

if __name__=='__main__':raise SystemExit(main(*sys.argv[1:]))
