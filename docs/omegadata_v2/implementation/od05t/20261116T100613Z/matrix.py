"""Fresh guarded three-runtime command matrix, existing environments only."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
LOGS=HERE/'logs'

def save(name,body):
    with (LOGS/name).open('x',encoding='utf-8') as f:json.dump(body,f,indent=2)

def run(label,root,module,args):
    hashes={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for top in ('src','tests','scripts','config') for p in (root/top).rglob('*')
        if p.is_file() and '__pycache__' not in p.parts}
    save(label+'-inputs.json',hashes)
    with (LOGS/(label+'-launcher.txt')).open('x',encoding='utf-8') as out:
        cmd=[sys.executable,'-B',str(HERE/'verification_runner.py'),label,str(root),module,*args]
        result=subprocess.run(cmd,stdout=out,stderr=subprocess.STDOUT)
    print(label,result.returncode,flush=True)
    return result.returncode

def main(label,root):
    root=Path(root)
    commands=[('environment','environment',[]),
        ('collection','pytest',['--collect-only','-q','-m','not realdata']),
        ('new','pytest',['-q','tests/unit/test_od05t_archive_inventory.py']),
        ('targeted','pytest',['-q','tests/unit/test_od01_source_rights.py','tests/unit/test_od01r_rights_hardening.py',
            'tests/unit/test_od02_acquisition.py','tests/unit/test_od02v_portability.py',
            'tests/unit/test_od04_raw_archive.py','tests/unit/test_od04r_adversarial.py',
            'tests/unit/test_od05_era_parsing.py','tests/unit/test_od05r_reference_evidence.py']),
        ('full','pytest',['-q','-m','not realdata','--cov=omegadata','--cov-branch','--cov-report=term-missing']),
        ('guard','pytest',['-q',str(HERE/'guard_probe.py')]),
        ('performance','pytest',['-q','-s','tests/unit/test_od05t_archive_inventory.py','-k','m16']),
        ('ruff','ruff',['check','--no-cache','src/omegadata','tests','scripts']),
        ('mypy','mypy',['src/omegadata']),('pip','pip',['check']),
        ('compile','compileall',['-q','src/omegadata','scripts'])]
    results={name:run(label+'-'+name,root,module,args) for name,module,args in commands}
    save(label+'-matrix.json',{'root':str(root),'results':results})
    return int(any(results.values()))

if __name__=='__main__':raise SystemExit(main(*sys.argv[1:]))
