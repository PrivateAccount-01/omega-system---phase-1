"""One bounded WSL original-mount v2 scan, no provider/payload access."""
import importlib.util
import json
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

here=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('control',here/'control.py')
control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)
native=Path(sys.argv[1]);original=here.parents[4]
sys.path[:0]=[str(native/'src')]
from omegadata.parsers.archive_candidate_inventory import ExpectedMetadata, InventoryError
from omegadata.parsers.local_archive_presence import ROOTS, scan_presence
groups=json.loads((native/'od05v_inputs/groups.json').read_text())
allowed=[original/g['repository_root']/n for g in groups.values() for n,_,_ in g['entries']]
state=control.activate_guard(original,Path(tempfile.mkdtemp(prefix='omega-od05w-mount-')),allowed)
out={}
for label,group in groups.items():
    profile={};tick=time.monotonic()
    try:
        result=scan_presence(original,label,expected=ExpectedMetadata(tuple(tuple(r) for r in group['entries'])),version=2,profile=profile)
        out[label]={'state':'RUN','exit_code':0,'counts':result['counts']}
    except InventoryError as error:
        out[label]={'state':'LINUX_ORIGINAL_MOUNT_FULL_SCAN_PERFORMANCE_BLOCKED' if error.reason_code=='BUDGET' else 'BLOCKED','exit_code':2,'reason':error.reason_code}
    out[label].update(profile=profile,elapsed_seconds=time.monotonic()-tick)
state['active']=False
control.save('linux-original-mount-v2.json',{'utc':datetime.now(UTC).isoformat(),'class':'LOCAL_META','results':out,'payload_bytes_read':0})
print(json.dumps(out,indent=2))
