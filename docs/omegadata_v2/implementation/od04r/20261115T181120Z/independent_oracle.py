"""Separately pinned stdlib oracle. Never imports the archive implementation."""
import hashlib
import json
import sys
from pathlib import Path

from process_guard import install

root = Path(sys.argv[1]).resolve()
assert root.name.startswith('omega-od04-process-')
install(root)
assert root.is_dir(), 'MISSING_EVIDENCE_ROOT'
EXPECTED_COUNTS = {'same': (3, 1), 'different': (3, 3), 'conflict': (1, 1),
                   'before_stage': (1, 1), 'after_stage': (1, 1), 'after_object': (1, 1),
                   'after_observation': (1, 1), 'before_commit': (1, 1), 'benchmark': (6, 3)}
assert sum(n for n, m in EXPECTED_COUNTS.values()) == 18
assert sum(m for n, m in EXPECTED_COUNTS.values()) == 13

def unique(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result, 'DUPLICATE_JSON_KEY'
        result[key] = value
    return result

def parse(raw):
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(AssertionError('NONFINITE_JSON')))

def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()

markers = list(root.rglob('commits/*.json'))
objects = [p for p in root.rglob('objects/sha256/*/*/*') if p.is_file()]
assert len(markers) == 18 and len(objects) == 13, 'INCOMPLETE_EVIDENCE_CORPUS'
rows = []
counts = {key: [0, 0] for key in EXPECTED_COUNTS}
for marker in markers:
    archive = marker.parent.parent
    case = archive.parent.name if archive.name == 'archive' else archive.name
    assert case in EXPECTED_COUNTS
    counts[case][0] += 1
    commit_raw = marker.read_bytes()
    commit = parse(commit_raw)
    assert commit_raw == canonical(commit), 'NONCANONICAL_COMMIT'
    assert commit['schema_version'] == 'raw-commit/v1' and commit['state'] == 'COMMITTED'
    raw = (archive / 'observations' / marker.name).read_bytes()
    obs = parse(raw)
    assert raw == canonical(obs), 'NONCANONICAL_OBSERVATION'
    assert obs['schema_version'] == 'raw-observation/v1'
    assert obs['observation_id'] == obs['request']['operation_id'] == commit['observation_id'] == marker.stem
    assert hashlib.sha256(raw).hexdigest() == commit['observation_sha256']
    assert obs['object'] == commit['object']
    assert obs['request']['source_mode'] == 'SYNTHETIC_TEST_ONLY'
    assert obs['request']['source_key'] == 'NSE_EQUITY_BHAVCOPY'
    assert obs['request']['business_date'] == '2026-04-10'
    assert obs['published_at'] is None and obs['source_reference'] == 'SOURCE_REFERENCE_PENDING'
    if case == 'benchmark':
        number = int(marker.stem, 16)
        assert 100 <= number <= 105
        size = [4096, 65536, 1048576][(number - 100) // 2]
        expected = (b'SYNTHETIC_TEST_ONLY' * (size // 19 + 1))[:size]
    elif case == 'different':
        assert int(marker.stem, 16) in (1, 2, 3)
        expected = marker.stem.encode()
    elif case == 'conflict':
        assert marker.stem == '6' * 32
        # The winning candidate is nondeterministic; both separately pinned inputs are allowed.
        expected = None
    else:
        expected = b'SYNTHETIC_TEST_ONLY-raw'
    obj = commit['object']
    digest = obj['sha256']
    relative = f'objects/sha256/{digest[:2]}/{digest[2:4]}/{digest}'
    assert obj['relative_path'] == relative
    data = (archive / relative).read_bytes()
    if expected is None:
        assert data in (b'SYNTHETIC_TEST_ONLY-raw', b'6' * 32)
    else:
        assert data == expected, 'PINNED_INPUT_MISMATCH'
    assert hashlib.sha256(data).hexdigest() == digest and len(data) == obj['size']
    rows.append({'case': case, 'id': marker.stem, 'bytes': len(data), 'sha256': digest})
for path in objects:
    archive = path.parents[4]
    case = archive.parent.name if archive.name == 'archive' else archive.name
    counts[case][1] += 1
    assert hashlib.sha256(path.read_bytes()).hexdigest() == path.name
assert counts == {k: list(v) for k, v in EXPECTED_COUNTS.items()}, 'CASE_COUNT_MISMATCH'
print(json.dumps({'observations': 18, 'objects': 13, 'counts': counts,
                  'all_full_hashes_sizes_canonical_links_and_pinned_inputs_verified': True,
                  'identities': sorted(rows, key=lambda r: (r['case'], r['id']))}, indent=2))
