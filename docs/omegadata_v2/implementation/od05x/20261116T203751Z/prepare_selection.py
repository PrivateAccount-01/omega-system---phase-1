"""Resume selection only; preserve the initial stale-copy-pin refusal."""
import hashlib
import json
from pathlib import Path

ROOT = Path.cwd()
HERE = Path(__file__).parent
OLD = ROOT / 'docs/omegadata_v2/implementation/od05w/20261116T183719Z'
INPUT = HERE / 'inputs'
def load(p): return json.loads(p.read_bytes())
def save(p, v):
    with p.open('x', encoding='utf-8') as f: json.dump(v, f, indent=2)
before = load(HERE / 'logs/read-and-preservation-before.json')['code_and_metadata_before']
groups = load(INPUT / 'groups.json')
review = load(INPUT / 'review.json')
selected = []
stale = []
for row in load(OLD / 'logs/accepted-copy-manifest.json')['files']:
    n = row['path']
    if n.startswith(('src/', 'scripts/', 'tests/', 'config/')) or n in {'pyproject.toml', 'README.md'}:
        current = hashlib.sha256((ROOT / n).read_bytes()).hexdigest()
        if current != row['sha256']: stale.append({'path': n, 'historical_copy_pin': row['sha256'], 'reviewed_HEAD_pin': current})
        if n in before: assert current == before[n]
        selected.append({'path': n, 'class': row['class'], 'source': n})
save(HERE / 'logs/prior-copy-pin-reconciliation.json', {'historical_copy_pins_differing_from_reviewed_HEAD': stale,
     'resolution': 'Use independently frozen current HEAD code hashes; historical intermediate copy receipt retained unchanged',
     'initial_prepare_exit_code': 1})
for n in ('scripts/od05x_isolated_runner.py', 'scripts/od05x_worker_jobs.py', 'tests/unit/test_od05x_isolation.py'):
    selected.append({'path': n, 'class': 'CODE', 'source': n})
for label, group in groups.items():
    for name, sha, length in group['entries']:
        n = group['repository_root'] + '/' + name
        selected.append({'path': n, 'class': 'LOCAL_META', 'source': n})
for target, source in {
    'od05v_inputs/groups.json': INPUT / 'groups.json', 'od05t_inputs/pins.json': INPUT / 'groups.json',
    'od05w_inputs/preservation.json': INPUT / 'preservation.json',
    'od05w_inputs/original-stat.json': OLD / 'logs/original-stat.json',
    'od05w_inputs/incident.json': ROOT / 'docs/omegadata_v2/implementation/od05v/20261116T172401Z/logs/setup-deviation.json',
    'od05x_inputs/review.json': INPUT / 'review.json',
    'od05x_inputs/original-independent-stat.json': INPUT / 'original-independent-stat.json',
    'od05x_inputs/original-model-stat.json': INPUT / 'original-model-stat.json',
}.items():
    selected.append({'path': target, 'class': 'LOCAL_META', 'source': source.relative_to(ROOT).as_posix()})
save(HERE / 'logs/reviewed-source-selection.json', {'basis': 'Exact prior code selection reconciled against fresh reviewed HEAD hashes; exact original manifest pins; explicit new tests reviewed A',
     'files': selected, 'file_count': len(selected), 'new_tests_explicit_A': review['new_functions']})
print(json.dumps({'selected': len(selected), 'stale_prior_receipt_pins': stale}))
