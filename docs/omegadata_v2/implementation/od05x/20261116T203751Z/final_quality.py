"""Fresh final Windows static checks and unsupported-backend refusal."""
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
sources = ['scripts/od05x_isolated_runner.py', 'scripts/od05x_worker_jobs.py',
           'tests/unit/test_od05x_isolation.py', 'tests/unit/test_od05x_native_extensions.py']
pins = {n: hashlib.sha256((root / n).read_bytes()).hexdigest() for n in sources}
for label, exe in [('win314', sys.executable), ('win311', json.loads((old / 'win311-r3-accepted-environment.txt').read_text())['executable'])]:
    temp = Path(tempfile.mkdtemp(prefix='omega-od05x-final-static-'))
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPYCACHEPREFIX': str(temp / 'pycache'),
           'MYPY_CACHE_DIR': str(temp / 'mypy'), 'PIP_DISABLE_PIP_VERSION_CHECK': '1'}
    commands = [('environment', [exe, '-B', '-c', 'import json,platform,sys; print(json.dumps(dict(executable=sys.executable,version=sys.version,platform=platform.platform())))']),
                ('refused-runner', [exe, '-B', 'scripts/od05x_isolated_runner.py', 'launch',
                    '--manifest', str(temp / 'not-opened.json'), '--manifest-sha256', '0' * 64,
                    '--policy', str(temp / 'not-opened-policy.json'), '--output', str(temp / 'not-created')])]
    commands += [(module, [exe, '-B', '-m', module, *args]) for module, args in (
        ('ruff', ['check', '--no-cache', 'src/omegadata', 'scripts', 'tests']),
        ('mypy', ['src/omegadata']), ('pip', ['check']), ('compileall', ['-q', 'src/omegadata', 'scripts']))]
    for kind, argv in commands:
        tick = time.monotonic()
        start = datetime.now(UTC).isoformat()
        r = subprocess.run(argv, capture_output=True, text=True, env=env)
        rows.append({'runtime': label, 'kind': kind, 'argv': argv, 'start_utc': start,
                     'end_utc': datetime.now(UTC).isoformat(), 'elapsed_seconds': time.monotonic() - tick,
                     'exit_code': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr,
                     'source_pins': pins, 'scope': 'STATIC/PREFLIGHT_ONLY; Windows pytest remains NOT_RUN_OS_ISOLATION_CAPABILITY_BLOCKED'})
        print(label, kind, r.returncode, flush=True)
    assert not (temp / 'not-created').exists()
with (here / 'logs/final-windows-quality.json').open('x') as f: json.dump(rows, f, indent=2)
