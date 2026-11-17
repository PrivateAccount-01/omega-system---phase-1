"""Bounded exact mounts through the same OS-proved stage API; no manual copying."""
import hashlib
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
here = Path(__file__).parent
root = here.parents[4]
runtime = '/home/parilrupani/omega-od02v-37b3vimd/venv312'
selection = json.loads((here / 'logs/reviewed-source-selection.json').read_bytes())['files']
groups = json.loads((here / 'inputs/groups.json').read_bytes())
pins = {g['repository_root'] + '/' + n: (sha, size) for g in groups.values() for n, sha, size in g['entries']}
base_rows = [r for r in selection if r['source'] not in pins]
metadata = [r for r in selection if r['source'] in pins]
def save(p, v):
    with p.open('x') as f: json.dump(v, f, indent=2)
cache = {'locations': {}, 'chunks': [], 'purpose': 'Explicit verified source reuse only; each stage destination is fresh'}
for part in range(0, len(metadata), 1800):
    tag = 'chunk-' + str(part // 1800) + '-' + uuid.uuid4().hex[:8]
    base = Path('/home/parilrupani') / ('omega-od05x-' + tag)
    base.mkdir(mode=0o700)
    sentinel = base / 'protected-NON_MARKET_CANARY'
    sentinel.write_bytes(b'NON_MARKET_CANARY')
    rows = []
    for row in base_rows + metadata[part:part + 1800]:
        source = root / row['source']
        if row['source'] in pins:
            sha, size = pins[row['source']]
        else:
            raw = source.read_bytes()
            sha, size = hashlib.sha256(raw).hexdigest(), len(raw)
        rows.append({'path': row['path'], 'class': row['class'], 'host': str(source),
                     'sha256': sha, 'bytes': size, 'device': source.lstat().st_dev})
    manifest = here / 'logs' / (tag + '-manifest.json')
    policy = here / 'logs' / (tag + '-policy.json')
    save(manifest, {'schema_version': 'od05x.inputs/v1', 'file_count': len(rows), 'files': rows})
    save(policy, {'runtime': runtime, 'job': 'stage_only', 'outside_canary': str(sentinel),
                  'parent_namespaces': {n: os.readlink('/proc/self/ns/' + n) for n in ('mnt', 'net', 'pid', 'user')}})
    argv = [runtime + '/bin/python', '-B', str(root / 'scripts/od05x_isolated_runner.py'), 'launch',
            '--manifest', str(manifest), '--manifest-sha256', hashlib.sha256(manifest.read_bytes()).hexdigest(),
            '--policy', str(policy), '--output', str(base / 'output')]
    tick = time.monotonic()
    start = datetime.now(UTC).isoformat()
    r = subprocess.run(argv, capture_output=True, text=True)
    receipts = list((base / 'output').glob('receipt-*.json'))
    result = {'argv': argv, 'start_utc': start, 'end_utc': datetime.now(UTC).isoformat(),
              'elapsed_seconds': time.monotonic() - tick, 'exit_code': r.returncode,
              'stdout': r.stdout, 'stderr': r.stderr}
    for name in ('launcher-result.json', 'native-probes.json'):
        p = base / 'output' / name
        if p.exists(): result[name] = json.loads(p.read_bytes())
    save(here / 'logs' / (tag + '-command.json'), result)
    print(json.dumps({'part': part, 'exit': r.returncode, 'result': result.get('launcher-result.json', {}).get('stderr', r.stdout)[-2000:]}), flush=True)
    if r.returncode != 0 or len(receipts) != 1:
        sys.exit(1)
    receipt = receipts[0]
    body = json.loads(receipt.read_bytes())
    save(here / 'logs' / (tag + '-receipt.json'), body)
    chunk_root = base / 'output/repo'
    actual = {p.relative_to(chunk_root).as_posix() for p in chunk_root.rglob('*') if p.is_file()}
    assert actual == {r['path'] for r in rows}
    cache['chunks'].append({'root': str(chunk_root), 'receipt': str(receipt),
        'receipt_sha256': hashlib.sha256(receipt.read_bytes()).hexdigest()})
    for row in rows:
        if row['path'] in pins:
            cache['locations'][row['path']] = {'host': str(chunk_root / row['path']),
                'root': str(chunk_root), 'sha256': row['sha256'], 'bytes': row['bytes']}
assert set(cache['locations']) == set(pins)
save(here / 'inputs/validated-native-source-chunks.json', cache)
print(json.dumps({'canonical_staged_metadata': len(cache['locations']), 'chunks': len(cache['chunks'])}))
