"""Trusted source-manifest review and independent host stat-only inventory."""
import hashlib
import json
import os
import stat
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path.cwd()
HERE = Path(__file__).parent
OLD = ROOT / 'docs/omegadata_v2/implementation/od05w/20261116T183719Z'
INPUT = HERE / 'inputs'
INPUT.mkdir()
sys.path.insert(0, str(ROOT / 'src'))
sys.dont_write_bytecode = True
from omegadata.parsers.archive_candidate_inventory import ExpectedMetadata
from omegadata.parsers.local_archive_presence import scan_presence

def load(p):
    return json.loads(p.read_bytes())

def save(p, v):
    with p.open('x', encoding='utf-8') as f:
        json.dump(v, f, indent=2)

pins_path = ROOT / 'docs/omegadata_v2/implementation/od05t/20261116T100613Z/logs/frozen-metadata-pins.json'
groups = load(pins_path)['groups']
allowed = {os.path.normcase(str((ROOT / g['repository_root'] / n).absolute()))
           for g in groups.values() for n, _, _ in g['entries']}
def audit(event, args):
    if event == 'open' and not isinstance(args[0], int):
        p = Path(os.path.abspath(os.fsdecode(args[0])))
        if p.is_relative_to(ROOT / 'data') and os.path.normcase(str(p)) not in allowed:
            raise PermissionError('OD05X_ORIGINAL_PAYLOAD_READ_REFUSED')
        if any(s in {'gnupg', 'private-keys-v1.d', 'openpgp-revocs.d'} for s in p.parts):
            raise PermissionError('OD05X_PRIVATE_READ_REFUSED')
sys.addaudithook(audit)
reports = {}
profiles = {}
model = {}
tick = time.monotonic()
for label, group in groups.items():
    profile = {}
    report = scan_presence(ROOT, label, expected=ExpectedMetadata(tuple(tuple(r) for r in group['entries'])),
                           version=2, profile=profile)
    reports[label], profiles[label] = report, profile
    for row in report['rows']:
        p = ROOT / row['payload_relative']
        s = p.lstat()
        model[row['payload_relative']] = {'size': s.st_size, 'mtime_ns': s.st_mtime_ns,
            'ino': s.st_ino, 'nlink': s.st_nlink, 'matched': row['filesystem_size_matches_manifest'],
            'regular': row['regular_file'], 'group': label}
model_elapsed = time.monotonic() - tick
# Separate traversal from frozen original manifests, independently of the model rows.
independent = {}
counts = {'seed': 0, 'cache': 0, 'present': 0, 'size_matched': 0,
          'hardlinked': 0, 'single_link': 0, 'missing': 0}
tick = time.monotonic()
for label, group in groups.items():
    for name, sha, length in group['entries']:
        raw = (ROOT / group['repository_root'] / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == sha and len(raw) == length
        meta = json.loads(raw)
        relative = meta['artifact_path'].replace('\\', '/')
        assert relative.startswith(group['repository_root'] + '/') and '..' not in Path(relative).parts
        path = ROOT / relative
        for parent in path.parents:
            if parent.is_relative_to(ROOT):
                s = parent.lstat()
                assert stat.S_ISDIR(s.st_mode) and not getattr(s, 'st_file_attributes', 0) & 0x400
        s = path.lstat()
        regular = stat.S_ISREG(s.st_mode) and not getattr(s, 'st_file_attributes', 0) & 0x400
        row = {'size': s.st_size, 'mtime_ns': s.st_mtime_ns, 'ino': s.st_ino, 'nlink': s.st_nlink,
               'matched': regular and s.st_size == meta['bytes_downloaded'], 'regular': bool(regular), 'group': label}
        independent[relative] = row
        counts[label] += 1
        counts['present'] += bool(regular)
        counts['size_matched'] += bool(row['matched'])
        counts['hardlinked'] += regular and s.st_nlink != 1
        counts['single_link'] += regular and s.st_nlink == 1
        counts['missing'] += not regular
assert independent == model
for label, rows in (('independent', independent), ('model', model)):
    save(INPUT / ('original-' + label + '-stat.json'), {'utc': datetime.now(UTC).isoformat(),
         'class': 'LOCAL_META', 'rows': rows, 'counts': counts, 'original_payload_bytes_read': 0})
save(HERE / 'logs/original-windows-profile.json', {'model_profiles': profiles,
     'model_elapsed_seconds': model_elapsed, 'independent_elapsed_seconds': time.monotonic() - tick,
     'counts': counts, 'payload_bytes_read': 0, 'max_seconds': 30})
save(INPUT / 'groups.json', groups)
old_inventory = load(OLD / 'test-dependency-inventory.json')['linux312']
before = load(HERE / 'logs/read-and-preservation-before.json')['code_and_metadata_before']
old_hashes = {n: h for n, h in before.items() if n.startswith('tests/') and n.endswith('.py')}
review = {'old_inventory': old_inventory, 'old_test_hashes': old_hashes,
          'new_test_source_sha256': hashlib.sha256((ROOT / 'tests/unit/test_od05x_isolation.py').read_bytes()).hexdigest(),
          'new_functions': {
              'test_x01_missing_sandbox_fail_closed': 1, 'test_x02_incorrect_capability_refused': 1,
              'test_x03_x06_native_os_denial': 5, 'test_x07_single_staging_entrypoint': 1,
              'test_x08_manifest_refusal': 5, 'test_x09_link_escape_refused': 3,
              'test_x10_mutation_refused': 2, 'test_x11_no_output_overwrite': 1,
              'test_x12_identity_diagnostic': 1, 'test_x13_concurrent_invalidation': 1,
              'test_x14_native_not_original': 1, 'test_x15_unknown_nodes_not_arbitrary_A': 1,
              'test_x16_B_C_preserved': 1, 'test_x17_preservation_fail_closed': 1,
              'test_x18_separate_gatekeeper_axes': 1, 'test_x15_collected_inventory_and_source_pins': 1,
              'test_x16_original_B_C_identities_preserved': 1, 'test_x17_fresh_original_stat_reconciliation': 1}}
save(INPUT / 'review.json', review)
save(INPUT / 'preservation.json', {n: h for n, h in before.items() if
    n.startswith(('config/', 'tests/fixtures/')) or n in {
    'tests/unit/test_adjustment_reference_corpus.py', 'tests/unit/test_universe_manager.py',
    'src/omegadata/track_a/raw_archive.py', 'src/omegadata/track_a/source_rights.py',
    'src/omegadata/track_a/source_registry.py', 'src/omegadata/track_a/acquisition.py'}})
selected = []
for row in load(OLD / 'logs/accepted-copy-manifest.json')['files']:
    n = row['path']
    if n.startswith(('src/', 'scripts/', 'tests/', 'config/')) or n in {'pyproject.toml', 'README.md'}:
        assert hashlib.sha256((ROOT / n).read_bytes()).hexdigest() == row['sha256']
        selected.append({'path': n, 'class': row['class'], 'source': n})
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
save(HERE / 'logs/reviewed-source-selection.json', {'basis': 'Prior exact reviewed code/config/fixture selection, independently frozen original metadata pins, explicit phase additions; no recursive extension selection',
     'files': selected, 'file_count': len(selected), 'new_tests_explicit_A': review['new_functions']})
print(json.dumps({'counts': counts, 'manifest_files': len(selected), 'new_test_cases': sum(review['new_functions'].values())}))
