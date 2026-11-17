"""Trusted R1 coordinator: exact reviewed sources and accepted Linux stage only."""
import ast
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

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
OLD = ROOT / 'docs/omegadata_v2/implementation/od05x/20261116T203751Z'
RUNTIME = '/home/parilrupani/omega-od02v-37b3vimd/venv312'

def save(p, v):
    with p.open('x', encoding='utf-8') as f:
        json.dump(v, f, indent=2)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

selection = json.loads((OLD / 'logs/reviewed-source-selection-v2.json').read_bytes())['files']
chunks = json.loads((OLD / 'inputs/validated-native-source-chunks.json').read_bytes())
locations = chunks['locations']
baseline = json.loads((HERE / 'inputs/code-preservation-before.json').read_bytes())
# Reused source trees contain ONLY previous canonical stage output; validate all
# files and receipt bytes, never reuse a previous execution destination.
for chunk in chunks['chunks']:
    receipt_raw = Path(chunk['receipt']).read_bytes()
    assert sha(receipt_raw) == chunk['receipt_sha256']
    receipt = json.loads(receipt_raw)
    base = Path(chunk['root'])
    assert {p.relative_to(base).as_posix() for p in base.rglob('*') if p.is_file()} == {r['path'] for r in receipt['files']}
    for row in receipt['files']:
        p = base / row['path']
        st = p.lstat()
        assert not p.is_symlink() and st.st_nlink == 1
        raw = p.read_bytes()
        assert len(raw) == row['bytes'] and sha(raw) == row['sha256']

for job in sys.argv[1:]:
    tag = job + '-' + uuid.uuid4().hex[:10]
    base = Path('/home/parilrupani') / ('omega-od05xr1-' + tag)
    base.mkdir(mode=0o700)
    canary = base / 'protected-NON_MARKET_CANARY'
    canary.write_bytes(b'NON_MARKET_CANARY')
    files, chunk_ids = [], {}
    for row in selection:
        name = row['path']
        if name in locations:
            loc = locations[name]
            host = Path(loc['host'])
            number = chunk_ids.setdefault(loc['root'], len(chunk_ids))
            files.append({'path': name, 'class': row['class'], 'host': str(host),
                          'device': host.lstat().st_dev, 'bytes': loc['bytes'], 'sha256': loc['sha256'],
                          'chunk_root': loc['root'], 'sandbox_source': '/chunks/' + str(number) + '/' + name})
            continue
        source = ROOT / row['source']
        raw = source.read_bytes()
        if row['source'] in baseline:
            assert sha(raw) == baseline[row['source']], 'BASELINE_CHANGED'
        if name == 'scripts/od05x_worker_jobs.py':
            # Exact reviewed extension delegates every old job unchanged.
            source = HERE / 'worker_extension.py'
            raw = source.read_bytes()
        files.append({'path': name, 'class': row['class'], 'host': str(source),
                      'device': source.lstat().st_dev, 'bytes': len(raw), 'sha256': sha(raw)})
    additions = {
        'scripts/od05x_base_worker_jobs.py': ROOT / 'scripts/od05x_worker_jobs.py',
        'tests/unit/test_od05xr1_windows_contract.py': ROOT / 'tests/unit/test_od05xr1_windows_contract.py',
    }
    if (ROOT / 'scripts/od05xr1_windows_backend.py').exists():
        additions['scripts/od05xr1_windows_backend.py'] = ROOT / 'scripts/od05xr1_windows_backend.py'
    if (HERE / 'inputs/runtime-inventory.json').exists():
        additions['od05x_inputs/runtime-inventory.json'] = HERE / 'inputs/runtime-inventory.json'
    for name, source in additions.items():
        assert name not in {r['path'] for r in files}
        raw = source.read_bytes()
        files.append({'path': name, 'class': 'LOCAL_META' if name.endswith('.json') else 'CODE',
                      'host': str(source), 'device': source.lstat().st_dev, 'bytes': len(raw), 'sha256': sha(raw)})
    manifest = HERE / 'logs' / (tag + '-manifest.json')
    policy = HERE / 'logs' / (tag + '-policy.json')
    save(manifest, {'schema_version': 'od05x.inputs/v1', 'file_count': len(files), 'files': files})
    save(policy, {'runtime': RUNTIME, 'job': job, 'outside_canary': str(canary),
                  'parent_namespaces': {n: os.readlink('/proc/self/ns/' + n) for n in ('mnt','net','pid','user')}})
    argv = [RUNTIME+'/bin/python', '-B', str(ROOT / 'scripts/od05x_isolated_runner.py'), 'launch',
            '--manifest', str(manifest), '--manifest-sha256', sha(manifest.read_bytes()),
            '--policy', str(policy), '--output', str(base / 'output')]
    start, tick = datetime.now(UTC).isoformat(), time.monotonic()
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired as error:
        r = subprocess.CompletedProcess(argv, 124, str(error.stdout or ''), str(error.stderr or ''))
    result = {'argv': argv, 'cwd': str(ROOT), 'start_utc': start,
              'end_utc': datetime.now(UTC).isoformat(), 'elapsed_seconds': time.monotonic()-tick,
              'exit_code': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr,
              'job': job, 'manifest_sha256': sha(manifest.read_bytes()), 'worker_result': None}
    for name in ('job/result.json','native-probes.json','launcher-result.json','job/coverage.json',
                 'job/identity-diagnostics.json','job/native-profile.json'):
        p = base / 'output' / name
        if p.exists():
            data = json.loads(p.read_bytes())
            save(HERE / 'logs' / (tag + '-' + p.name), data)
            if name == 'job/result.json':
                result['worker_result'] = data
    receipts = list((base / 'output').glob('receipt-*.json'))
    result['receipts'] = [{'path': str(p), 'sha256': sha(p.read_bytes()),
                           'file_count': json.loads(p.read_bytes())['file_count']} for p in receipts]
    save(HERE / 'logs' / (tag + '-command.json'), result)
    worker = result['worker_result']
    print(json.dumps({'job': job, 'tag': tag, 'exit_code': r.returncode,
                      'counts': worker.get('counts') if worker else None,
                      'error_tail': (worker['stdout_stderr'][-2000:] if worker and r.returncode else r.stderr[-1500:])}), flush=True)
    if job == 'collection' and worker and not worker['exit_code']:
        prior = json.loads((OLD / 'inputs/runtime-inventory.json').read_bytes())
        categories = {n.split('[',1)[0]: c for n,c in prior.items()}
        expected = Counter(n.split('[',1)[0] for n in prior)
        # Explicit review: these are nonfinancial Windows contract/canary tests.
        functions = {'test_win01_no_backend_before_input_read':1, 'test_win02_false_VM_report_refused':1,
                     'test_windows_native_execution_requires_approved_VM':7, 'test_win07_exact_source_contract':4,
                     'test_win08_changed_hash_refused':1, 'test_win09_win10_native_identity_contract':4,
                     'test_win11_windows_path_hazards':13, 'test_win11_case_alias':1,
                     'test_win12_win13_identity_change_refused':2, 'test_win14_fresh_destination':1,
                     'test_win16_reviewed_runtime_inventory':1, 'test_win17_linux_source_contract_retained':1,
                     'test_win19_financial_and_incident_gates':1, 'test_win07_positive_exact_manifest':1,
                     'test_win10_positive_identity_contract':1}
        tree = ast.parse((ROOT / 'tests/unit/test_od05xr1_windows_contract.py').read_bytes())
        assert {n.name for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')} == set(functions)
        for function, count in functions.items():
            n = 'tests/unit/test_od05xr1_windows_contract.py::' + function
            expected[n], categories[n] = count, 'A'
        current = worker['collected']
        assert Counter(r['nodeid'].split('[',1)[0] for r in current) == expected, 'UNREVIEWED_COLLECTION'
        inventory = {r['nodeid']: categories[r['nodeid'].split('[',1)[0]] for r in current}
        assert all((inventory[r['nodeid']] == 'C') == r['realdata'] for r in current)
        p = HERE / 'inputs/runtime-inventory.json'
        if p.exists():
            assert json.loads(p.read_bytes()) == inventory
        else:
            save(p, inventory)
        save(HERE / 'logs' / (tag + '-inventory-source-pins.json'), {
            'runtime': worker['python'], 'classes': dict(Counter(inventory.values())),
            'test_hashes': {r['path']:r['sha256'] for r in files if r['path'].startswith('tests/')},
            'inventory': inventory})
        print(json.dumps({'collected':len(inventory), 'classes':dict(Counter(inventory.values()))}), flush=True)
