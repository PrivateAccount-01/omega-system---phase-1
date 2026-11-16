"""Three-runtime offline verification; existing environments, no installation."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOGS = HERE / 'logs'


def run(label, root, module, args):
    inputs = {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
              for folder in ('src','tests','scripts','config') for p in (Path(root)/folder).rglob('*')
              if p.is_file() and '__pycache__' not in p.parts}
    with (LOGS/(label+'-inputs.json')).open('x',encoding='utf-8') as manifest:
        json.dump(inputs,manifest,indent=2)
    cmd = [sys.executable, '-B', str(HERE / 'verification_runner.py'), label, root, module, *args]
    with (LOGS / (label+'-launcher.txt')).open('x', encoding='utf-8') as out:
        result = subprocess.run(cmd, stdout=out, stderr=subprocess.STDOUT)
    print(label, result.returncode, flush=True)
    return result.returncode


def matrix(label, root):
    commands = [('environment', 'environment', []),
        ('collection', 'pytest', ['--collect-only','-q','-m','not realdata']),
        ('targeted', 'pytest', ['-q','tests/unit/test_od05_era_parsing.py','tests/unit/test_od05r_reference_evidence.py',
            'tests/unit/test_od01_source_rights.py','tests/unit/test_od01r_rights_hardening.py',
            'tests/unit/test_od02_acquisition.py','tests/unit/test_od02v_portability.py',
            'tests/unit/test_od04_raw_archive.py','tests/unit/test_od04r_adversarial.py']),
        ('full', 'pytest', ['-q','-m','not realdata','--cov=omegadata','--cov-branch','--cov-report=term-missing']),
        ('ruff', 'ruff', ['check','--no-cache','src/omegadata','tests','scripts']),
        ('mypy', 'mypy', ['src/omegadata']), ('pip', 'pip', ['check']),
        ('compile', 'compileall', ['-q','src/omegadata'])]
    results = {name:run(label+'-'+name,root,module,args) for name,module,args in commands}
    files = {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
             for folder in ('src','tests','scripts','config') for p in (Path(root)/folder).rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    with (LOGS/(label+'-matrix.json')).open('x',encoding='utf-8') as out:
        json.dump({'root':root,'results':results,'files':files},out,indent=2)
    return int(any(results.values()))


if __name__=='__main__':
    if sys.argv[1]=='linux-prepare':
        target=Path(tempfile.mkdtemp(prefix='omega-od05-',dir='/home/parilrupani'))/'repo'
        shutil.copytree(sys.argv[2],target)
        assert not (target/'artifacts').exists() and not (target/'.env').exists()
        print(json.dumps({'root':str(target),'python':sys.executable,'version':sys.version}))
    else:
        raise SystemExit(matrix(sys.argv[1],sys.argv[2]))
