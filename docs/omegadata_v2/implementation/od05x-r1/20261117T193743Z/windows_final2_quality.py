"""Safe Windows refusal and static checks; no isolated Windows pytest claim."""
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
cap = json.loads((HERE / '02_windows_capability_assessment.json').read_bytes())
for label in ('win314', 'win311'):
    exe = json.loads(cap['offline_runtime_inventory'][label]['stdout'])['executable']
    base = Path(tempfile.mkdtemp(prefix='omega-od05xr1-static-'))
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE':'1', 'PYTHONPYCACHEPREFIX':str(base/'pycache'),
           'MYPY_CACHE_DIR':str(base/'mypy'), 'PIP_DISABLE_PIP_VERSION_CHECK':'1'}
    operations = [('refusal', [exe, '-B', str(ROOT/'scripts/od05xr1_windows_backend.py'),
                               '--manifest', str(base/'not-opened.json'),
                               '--manifest-sha256', '0'*64, '--output', str(base/'not-created')])]
    for mod,args in [('ruff',['check','--no-cache','src/omegadata','scripts','tests']),
                     ('mypy',['src/omegadata']),('pip',['check']),
                     ('compileall',['-q','src/omegadata','scripts'])]:
        operations.append((mod,[exe,'-B','-m',mod,*args]))
    rows = []
    for name, argv in operations:
        start,tick = datetime.now(UTC).isoformat(),time.monotonic()
        r = subprocess.run(argv,cwd=ROOT,env=env,capture_output=True,text=True,timeout=180)
        rows.append({'operation':name,'argv':argv,'cwd':str(ROOT),'start_utc':start,
                     'end_utc':datetime.now(UTC).isoformat(),'elapsed_seconds':time.monotonic()-tick,
                     'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr,
                     'scope':'TRUSTED_PREFLIGHT_OR_STATIC_ONLY_NOT_ISOLATED_PYTEST'})
        if name == 'refusal':
            assert r.returncode == 2 and not (base/'not-created').exists()
            assert json.loads(r.stdout)['manifest_read'] is False
        print(label,name,r.returncode,flush=True)
    report = {'runtime':label,'python':json.loads(cap['offline_runtime_inventory'][label]['stdout'])['version'],
              'operations':rows,'collection':'NOT_RUN_OS_CAPABILITY_BLOCKED',
              'pytest_A':'NOT_RUN_OS_CAPABILITY_BLOCKED','diagnostic':'NOT_RUN_OS_CAPABILITY_BLOCKED',
              'native_denial_probes':'NOT_RUN_OS_CAPABILITY_BLOCKED',
              'identity_stress':'NOT_RUN_OS_CAPABILITY_BLOCKED','copied_inputs':0,
              'financial_rows_verified':0,'overall':'BLOCKED'}
    with (HERE / ('logs/windows314-final2-quality.json' if label=='win314' else 'logs/windows311-final2-quality.json')).open('x') as f:
        json.dump(report,f,indent=2)


