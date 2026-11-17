import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

here = Path(__file__).parent
prior = json.loads((here / 'logs/negative-first-baseline.json').read_text())
argv = prior['argv']
cut = argv.index('/home/parilrupani/omega-od02v-37b3vimd/venv312/bin/python')
argv[cut:cut] = ['--setenv', 'PYTHONPATH', '/input/scripts', '--ro-bind',
    '/mnt/e/omega system - phase 1/scripts/od05x_isolated_runner.py',
    '/input/scripts/od05x_isolated_runner.py']
argv[-1:] = ['/tests/test_x.py::' + n for n in (
    'test_x15_collected_inventory_and_source_pins',
    'test_x16_original_B_C_identities_preserved', 'test_x17_fresh_original_stat_reconciliation')]
start = datetime.now(UTC).isoformat()
r = subprocess.run(argv, capture_output=True, text=True)
with (here / 'logs/integration-negative-first.json').open('x') as f:
    json.dump({'argv': argv, 'start_utc': start, 'end_utc': datetime.now(UTC).isoformat(),
               'exit_code': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr,
               'classification': 'NEW_FEATURE_ABSENT'}, f, indent=2)
print(r.stdout[-2400:])
