"""Post-seal hardening checks, appended without changing previous records."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
here = Path(__file__).parent
root = Path.cwd()
old = root / 'docs/omegadata_v2/implementation/od05w/20261116T183719Z/logs'
rows = []
files = ['scripts/od05x_isolated_runner.py', 'scripts/od05x_worker_jobs.py',
         'tests/unit/test_od05x_isolation.py', 'tests/unit/test_od05x_native_extensions.py']
pins = {n: hashlib.sha256((root / n).read_bytes()).hexdigest() for n in files}
for label, exe in [('win314', sys.executable), ('win311', json.loads((old / 'win311-r3-accepted-environment.txt').read_text())['executable'])]:
    base = Path(tempfile.mkdtemp(prefix='omega-od05x-hardened-static-'))
    env = {**os.environ, 'PYTHONPYCACHEPREFIX': str(base / 'pycache'),
           'MYPY_CACHE_DIR': str(base / 'mypy'), 'PIP_DISABLE_PIP_VERSION_CHECK': '1'}
    checks = [('refused-runner', [exe, '-B', 'scripts/od05x_isolated_runner.py', 'launch',
          '--manifest', str(base / 'not-opened'), '--manifest-sha256', '0' * 64,
          '--policy', str(base / 'not-opened-policy'), '--output', str(base / 'not-created')])]
    checks += [(n, [exe, '-B', '-m', n, *a]) for n, a in (
        ('ruff', ['check', '--no-cache', 'src/omegadata', 'scripts', 'tests']),
        ('mypy', ['src/omegadata']), ('pip', ['check']), ('compileall', ['-q', 'src/omegadata', 'scripts']))]
    for kind, argv in checks:
        tick = time.monotonic()
        start = datetime.now(UTC).isoformat()
        r = subprocess.run(argv, capture_output=True, text=True, env=env)
        rows.append({'runtime': label, 'kind': kind, 'argv': argv, 'start_utc': start,
            'end_utc': datetime.now(UTC).isoformat(), 'elapsed_seconds': time.monotonic() - tick,
            'exit_code': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr, 'source_pins': pins,
            'scope': 'STATIC/PREFLIGHT_ONLY; Windows pytest still blocked'})
        print(label, kind, r.returncode, flush=True)
    assert not (base / 'not-created').exists()
with (here / 'logs/postseal-windows-quality.json').open('x') as f: json.dump(rows, f, indent=2)
