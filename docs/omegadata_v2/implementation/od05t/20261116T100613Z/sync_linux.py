"""Synchronize only phase-owned files in the task-created Linux copy."""
import json
import shutil
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
target=Path(json.loads((HERE/'logs/linux-copy.json').read_text())['root'])
assert str(target).startswith('/home/parilrupani/omega-od05t-') and target.name=='repo'
for name in ('src/omegadata/parsers/archive_candidate_inventory.py','scripts/audit_existing_market_archive.py',
             'tests/unit/test_od05t_archive_inventory.py','tests/unit/od05t_metadata_oracle.py'):
    shutil.copyfile(ROOT/name,target/name)
print(target)
