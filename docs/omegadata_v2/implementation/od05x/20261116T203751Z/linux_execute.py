"""Trusted Linux coordinator. Launches only the new exact-mount entrypoint."""
import hashlib
import json
import os
import subprocess
import sys
import time
import uuid
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parents[4]
RUNTIME = Path('/home/parilrupani/omega-od02v-37b3vimd/venv312')
selection_path = HERE / 'logs/reviewed-source-selection-v2.json'
if not selection_path.exists():
    selection_path = HERE / 'logs/reviewed-source-selection.json'
selection = json.loads(selection_path.read_bytes())['files']
groups = json.loads((HERE / 'inputs/groups.json').read_bytes())
metadata_pins = {g['repository_root'] + '/' + n: (sha, length)
                 for g in groups.values() for n, sha, length in g['entries']}
baseline = json.loads((HERE / 'logs/read-and-preservation-before.json').read_bytes())['code_and_metadata_before']

def save(path, value):
    with path.open('x', encoding='utf-8') as f: json.dump(value, f, indent=2)

for job in sys.argv[1:]:
    run = uuid.uuid4().hex[:12]
    base = Path('/home/parilrupani') / ('omega-od05x-' + run)
    base.mkdir(mode=0o700)
    canary = base / 'protected-NON_MARKET_CANARY'
    canary.write_bytes(b'NON_MARKET_CANARY')
    files = []
    cache_file = HERE / 'inputs/validated-native-source.json'
    cached = json.loads(cache_file.read_bytes()) if cache_file.exists() else None
    chunk_file = HERE / 'inputs/validated-native-source-chunks.json'
    staged_chunks = json.loads(chunk_file.read_bytes()) if chunk_file.exists() else None
    chunk_numbers = {}
    if staged_chunks:
        for chunk in staged_chunks['chunks']:
            receipt_raw = Path(chunk['receipt']).read_bytes()
            assert hashlib.sha256(receipt_raw).hexdigest() == chunk['receipt_sha256']
            receipt = json.loads(receipt_raw)
            chunk_root = Path(chunk['root'])
            actual = {p.relative_to(chunk_root).as_posix()
                      for p in chunk_root.rglob('*') if p.is_file()}
            assert actual == {r['path'] for r in receipt['files']}, 'UNREVIEWED_CHUNK_FILE'
            for entry in receipt['files']:
                p = chunk_root / entry['path']
                assert p.lstat().st_nlink == 1 and not p.is_symlink(), 'CHUNK_LINK_CHANGED'
                raw = p.read_bytes()
                assert len(raw) == entry['bytes'] and hashlib.sha256(raw).hexdigest() == entry['sha256'], 'CHUNK_PIN_CHANGED'
    for row in selection:
        if staged_chunks and row['source'] in metadata_pins:
            pin = staged_chunks['locations'][row['path']]
            source = Path(pin['host'])
            if pin['root'] not in chunk_numbers:
                chunk_numbers[pin['root']] = len(chunk_numbers)
            files.append({'path': row['path'], 'class': row['class'], 'host': str(source),
                'device': source.lstat().st_dev, 'bytes': pin['bytes'], 'sha256': pin['sha256'],
                'chunk_root': pin['root'], 'sandbox_source': '/chunks/' + str(chunk_numbers[pin['root']]) + '/' + row['path']})
            continue
        reuse_metadata = cached is not None and row['source'] in metadata_pins
        source = Path(cached['root']) / row['path'] if reuse_metadata else ROOT / row['source']
        if reuse_metadata:
            pin = cached['pins'][row['path']]
            sha, length = pin['sha256'], pin['bytes']
        elif row['source'] in metadata_pins:
            sha, length = metadata_pins[row['source']]
        else:
            raw = source.read_bytes()
            sha, length = hashlib.sha256(raw).hexdigest(), len(raw)
            if row['source'] in baseline:
                assert sha == baseline[row['source']], 'REVIEWED_BASELINE_CHANGED'
        files.append({'path': row['path'], 'class': row['class'], 'host': str(source),
                      'device': source.lstat().st_dev, 'bytes': length, 'sha256': sha})
    if (HERE / 'inputs/runtime-inventory.json').exists():
        source = HERE / 'inputs/runtime-inventory.json'
        raw = source.read_bytes()
        files.append({'path': 'od05x_inputs/runtime-inventory.json', 'class': 'LOCAL_META',
                      'host': str(source), 'device': source.lstat().st_dev,
                      'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
    manifest = HERE / 'logs' / (job + '-' + run + '-manifest.json')
    save(manifest, {'schema_version': 'od05x.inputs/v1', 'file_count': len(files), 'files': files})
    policy = HERE / 'logs' / (job + '-' + run + '-policy.json')
    save(policy, {'runtime': str(RUNTIME), 'job': job, 'outside_canary': str(canary),
                  'parent_namespaces': {n: os.readlink('/proc/self/ns/' + n) for n in ('mnt', 'net', 'pid', 'user')}})
    argv = [str(RUNTIME / 'bin/python'), '-B', str(ROOT / 'scripts/od05x_isolated_runner.py'),
            'launch', '--manifest', str(manifest), '--manifest-sha256', hashlib.sha256(manifest.read_bytes()).hexdigest(),
            '--policy', str(policy), '--output', str(base / 'output')]
    tick = time.monotonic()
    start = datetime.now(UTC).isoformat()
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired as error:
        r = subprocess.CompletedProcess(argv, 124, error.stdout or '', error.stderr or '')
    log = {'argv': argv, 'start_utc': start, 'end_utc': datetime.now(UTC).isoformat(),
           'elapsed_seconds': time.monotonic() - tick, 'exit_code': r.returncode,
           'stdout': r.stdout, 'stderr': r.stderr, 'job': job,
           'worker_result': None, 'original_payloads_copied': 0}
    for name in ('job/result.json', 'native-probes.json', 'launcher-result.json',
                 'job/native-profile.json', 'job/identity-diagnostics.json', 'job/coverage.json'):
        path = base / 'output' / name
        if path.exists():
            body = json.loads(path.read_bytes())
            save(HERE / 'logs' / (job + '-' + run + '-' + Path(name).name), body)
            if name == 'job/result.json': log['worker_result'] = body
    receipts = list((base / 'output').glob('receipt-*.json'))
    for path in receipts:
        receipt = json.loads(path.read_bytes())
        save(HERE / 'logs' / (job + '-' + run + '-copy-receipt.json'), receipt)
        if not cache_file.exists():
            save(cache_file, {'root': str(base / 'output/repo'),
                 'receipt_log': job + '-' + run + '-copy-receipt.json',
                 'receipt_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                 'purpose': 'Explicit source-only reuse of a kernel-isolated canonical copy; every destination remains fresh',
                 'pins': {r['path']: r for r in receipt['files']}})
    save(HERE / 'logs' / (job + '-' + run + '-command.json'), log)
    print(json.dumps({'job': job, 'run': run, 'exit': r.returncode, 'stdout': r.stdout[-1500:],
                      'stderr': r.stderr[-1000:], 'counts': log['worker_result']['counts'] if log['worker_result'] else None}), flush=True)
    if job == 'collection' and log['worker_result'] and log['worker_result']['exit_code'] == 0:
        review_path = HERE / 'inputs/review-v2.json'
        if not review_path.exists(): review_path = HERE / 'inputs/review.json'
        review = json.loads(review_path.read_bytes())
        prior = review['old_inventory']
        expected = Counter(n.split('[', 1)[0] for n in prior)
        categories = {n.split('[', 1)[0]: c for n, c in prior.items()}
        for function, count in review['new_functions'].items():
            name = review.get('new_paths', {}).get(function, 'tests/unit/test_od05x_isolation.py') + '::' + function
            assert name not in expected
            expected[name] = count
            categories[name] = 'A'
        current = log['worker_result']['collected']
        assert Counter(row['nodeid'].split('[', 1)[0] for row in current) == expected
        inventory = {row['nodeid']: categories[row['nodeid'].split('[', 1)[0]] for row in current}
        assert all((inventory[row['nodeid']] == 'C') == row['realdata'] for row in current)
        target = HERE / 'inputs/runtime-inventory.json'
        if target.exists():
            assert json.loads(target.read_bytes()) == inventory, 'FROZEN_NODE_INVENTORY_CHANGED'
            save(HERE / 'logs' / ('collection-' + run + '-inventory-recheck.json'), inventory)
        else:
            save(target, inventory)
        print(json.dumps({'reviewed_collection': len(inventory), 'classes': dict(Counter(inventory.values()))}), flush=True)
