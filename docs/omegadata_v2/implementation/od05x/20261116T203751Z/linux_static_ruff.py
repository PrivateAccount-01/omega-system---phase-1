"""Namespace-restricted static Rust executable; not a child-denial certification."""
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
here = Path(__file__).parent
root = here.parents[4]
runtime = '/home/parilrupani/omega-od02v-37b3vimd/venv312'
argv = ['/usr/bin/bwrap', '--unshare-all', '--die-with-parent', '--new-session', '--cap-drop', 'ALL',
        '--clearenv', '--ro-bind', '/usr', '/usr', '--symlink', 'usr/lib', '/lib',
        '--symlink', 'usr/lib64', '/lib64', '--ro-bind', runtime, runtime,
        '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp',
        '--ro-bind', str(root / 'src'), '/repo/src', '--ro-bind', str(root / 'scripts'), '/repo/scripts',
        '--ro-bind', str(root / 'tests'), '/repo/tests', '--ro-bind', str(root / 'pyproject.toml'), '/repo/pyproject.toml',
        '--chdir', '/repo', runtime + '/bin/ruff', 'check', '--no-cache', 'src/omegadata', 'scripts', 'tests']
tick = time.monotonic()
start = datetime.now(UTC).isoformat()
r = subprocess.run(argv, capture_output=True, text=True)
record = {'argv': argv, 'start_utc': start, 'end_utc': datetime.now(UTC).isoformat(),
          'elapsed_seconds': time.monotonic() - tick, 'exit_code': r.returncode,
          'stdout': r.stdout, 'stderr': r.stderr,
          'scope': 'STATIC_TOOL_ONLY; read-only source and separate filesystem/network namespace; child/native exec policy not certified for this trusted executable job'}
name = sys.argv[1] if len(sys.argv) > 1 else 'linux-static-ruff.json'
with (here / 'logs' / name).open('x') as f: json.dump(record, f, indent=2)
print(json.dumps(record))
