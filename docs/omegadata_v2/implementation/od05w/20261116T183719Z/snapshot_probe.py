"""Reprobe observed canary-stat drift without altering refusal checks."""
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

here=Path(__file__).resolve().parent
loc=json.loads((here/'logs/locations.json').read_text())
worktree=Path(loc['repo']);corpus=Path(loc['canary'])
sys.path[:0]=[str(worktree/'src')]
from omegadata.parsers.local_archive_presence import PresenceObservation, InventoryError
from omegadata.parsers.archive_candidate_inventory import ExpectedMetadata
spec=importlib.util.spec_from_file_location('control',here/'control.py')
control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)
g=json.loads((worktree/'od05v_inputs/groups.json').read_text())['cache']
allowed=[corpus/g['repository_root']/name for name,_,_ in g['entries']]
state=control.activate_guard(corpus,Path(tempfile.mkdtemp(prefix='omega-od05w-drift-')),allowed)
results=[]
for attempt in range(8):
    before=PresenceObservation._fingerprint(corpus/g['repository_root'])
    observation=PresenceObservation(corpus,'cache',ExpectedMetadata(tuple(tuple(r) for r in g['entries'])),version=1)
    try:
        observation.get();observation.get();status='PASS'
    except InventoryError as error:status=error.reason_code
    after=PresenceObservation._fingerprint(corpus/g['repository_root'])
    changes=[{'path':p.relative_to(corpus).as_posix(),'before':v,'after':after.get(p)} for p,v in before.items() if after.get(p)!=v]
    results.append({'attempt':attempt+1,'status':status,'observed_changes':changes})
state['active']=False
control.save('snapshot-drift-reprobe.json',{'class':'NON_MARKET_CANARY','initial_failure':'win314-r3-accepted-A.json P03 INPUT_CHANGED','initial_differing_stat_fields':'NOT_CAPTURED; unknown cause','reprobe':results,'security_check_relaxed':False,'market_payload_bytes_read':0})
print(json.dumps(results,indent=2))
