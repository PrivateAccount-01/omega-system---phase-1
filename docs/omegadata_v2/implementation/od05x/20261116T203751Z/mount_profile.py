"""One trusted-host metadata-only mounted scan; no worker access to originals."""
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
here = Path(__file__).parent
root = here.parents[4]
sys.path.insert(0, str(root / 'src'))
sys.dont_write_bytecode = True
from omegadata.parsers.archive_candidate_inventory import ExpectedMetadata, InventoryError
from omegadata.parsers.local_archive_presence import scan_presence
groups = json.loads((here / 'inputs/groups.json').read_bytes())
allowed = {str(root / g['repository_root'] / n) for g in groups.values() for n, _, _ in g['entries']}
def guard(event, args):
    if event == 'open' and not isinstance(args[0], int):
        path = Path(os.path.abspath(os.fsdecode(args[0])))
        if path.is_relative_to(root / 'data') and str(path) not in allowed:
            raise PermissionError('ORIGINAL_PAYLOAD_REFUSED')
        if any(p in {'gnupg', 'private-keys-v1.d', 'openpgp-revocs.d'} for p in path.parts):
            raise PermissionError('PRIVATE_REFUSED')
sys.addaudithook(guard)
results = {}
for label, group in groups.items():
    profile = {}
    tick = time.monotonic()
    try:
        report = scan_presence(root, label, expected=ExpectedMetadata(tuple(tuple(r) for r in group['entries'])), version=2, profile=profile)
        result = {'exit_code': 0, 'state': 'LOCAL_META', 'counts': report['counts']}
    except InventoryError as e:
        result = {'exit_code': 2, 'state': 'LINUX_ORIGINAL_MOUNT_FULL_SCAN_PERFORMANCE_BLOCKED' if e.reason_code == 'BUDGET' else 'BLOCKED', 'reason': e.reason_code}
    result.update(profile=profile, elapsed_seconds=time.monotonic() - tick)
    results[label] = result
record = {'utc': datetime.now(UTC).isoformat(), 'scope': 'TRUSTED_HOST_METADATA_OBSERVER_NOT_TEST_WORKER',
          'payload_bytes_read': 0, 'max_seconds': 30, 'results': results}
with (here / 'logs/linux-original-mount-profile.json').open('x') as f: json.dump(record, f, indent=2)
print(json.dumps(record))
