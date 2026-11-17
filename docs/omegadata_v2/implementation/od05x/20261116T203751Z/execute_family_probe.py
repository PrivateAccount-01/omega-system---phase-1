"""Execute an exact two-code-file canary manifest after OS proof."""
import hashlib
import json
import os
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
here = Path(__file__).parent
root = here.parents[4]
runtime = '/home/parilrupani/omega-od02v-37b3vimd/venv312'
tag = 'family-' + uuid.uuid4().hex[:10]
base = Path('/home/parilrupani') / ('omega-od05x-' + tag)
base.mkdir(mode=0o700)
canary = base / 'NON_MARKET_CANARY'
canary.touch()
rows = []
for target, source in [('scripts/od05x_isolated_runner.py', root / 'scripts/od05x_isolated_runner.py'),
                       ('scripts/od05x_worker_jobs.py', here / 'network_family_probe_job.py')]:
    raw = source.read_bytes()
    rows.append({'path': target, 'host': str(source), 'class': 'CODE', 'device': source.lstat().st_dev,
                 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
def save(p, v):
    with p.open('x') as f: json.dump(v, f, indent=2)
manifest = here / 'logs' / (tag + '-manifest.json')
policy = here / 'logs' / (tag + '-policy.json')
save(manifest, {'schema_version': 'od05x.inputs/v1', 'file_count': 2, 'files': rows})
save(policy, {'runtime': runtime, 'job': 'family-control', 'outside_canary': str(canary),
              'parent_namespaces': {n: os.readlink('/proc/self/ns/' + n) for n in ('mnt', 'net', 'pid', 'user')}})
argv = [runtime + '/bin/python', '-B', str(root / 'scripts/od05x_isolated_runner.py'), 'launch',
        '--manifest', str(manifest), '--manifest-sha256', hashlib.sha256(manifest.read_bytes()).hexdigest(),
        '--policy', str(policy), '--output', str(base / 'output')]
start = datetime.now(UTC).isoformat()
r = subprocess.run(argv, capture_output=True, text=True, timeout=30)
record = {'argv': argv, 'start_utc': start, 'end_utc': datetime.now(UTC).isoformat(),
          'exit_code': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr,
          'probe_sha256': rows[1]['sha256'], 'classification': sys.argv[1]}
for name in ('launcher-result.json', 'family-result.json', 'native-probes.json'):
    p = base / 'output' / name
    if p.exists(): record[name] = json.loads(p.read_bytes())
save(here / 'logs' / (tag + '-command.json'), record)
print(json.dumps({k: v for k, v in record.items() if k not in {'argv', 'launcher-result.json', 'native-probes.json'}}))
