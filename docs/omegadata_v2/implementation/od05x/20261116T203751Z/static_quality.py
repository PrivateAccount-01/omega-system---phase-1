"""Read-only static tools; not credited as an OS-isolated regression run."""
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
previous = root / 'docs/omegadata_v2/implementation/od05w/20261116T183719Z/logs'
rows = []
for label, exe in [('win314', sys.executable), ('win311', json.loads((previous / 'win311-r3-accepted-environment.txt').read_text())['executable'])]:
    temp = Path(tempfile.mkdtemp(prefix='omega-od05x-static-'))
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPYCACHEPREFIX': str(temp / 'pycache'),
           'MYPY_CACHE_DIR': str(temp / 'mypy'), 'PIP_DISABLE_PIP_VERSION_CHECK': '1'}
    for module, args in [('ruff', ['check', '--no-cache', 'src/omegadata', 'scripts', 'tests']),
                         ('mypy', ['src/omegadata']), ('pip', ['check']),
                         ('compileall', ['-q', 'src/omegadata', 'scripts'])]:
        argv = [exe, '-B', '-m', module, *args]
        tick = time.monotonic()
        start = datetime.now(UTC).isoformat()
        r = subprocess.run(argv, capture_output=True, text=True, env=env)
        rows.append({'runtime': label, 'argv': argv, 'start_utc': start,
                     'end_utc': datetime.now(UTC).isoformat(), 'elapsed_seconds': time.monotonic() - tick,
                     'exit_code': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr,
                     'scope': 'STATIC_TOOL_ONLY; not approved isolated test-runner acceptance'})
        print(label, module, r.returncode, flush=True)
with (here / 'logs/windows-static-quality.json').open('x') as f: json.dump(rows, f, indent=2)
