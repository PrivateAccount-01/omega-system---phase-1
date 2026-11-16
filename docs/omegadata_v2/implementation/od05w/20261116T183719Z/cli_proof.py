"""Actual guarded CLI entry calls against original pinned manifest/stat inputs."""
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

here=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('control',here/'control.py')
control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)
loc=json.loads((here/'logs/locations.json').read_text());worktree=Path(loc['repo'])
sys.path[:0]=[str(worktree/'src')]
spec=importlib.util.spec_from_file_location('cli',worktree/'scripts/audit_local_archive_presence.py')
cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
original=here.parents[4]
groups=json.loads((worktree/'od05v_inputs/groups.json').read_text())
base=Path(tempfile.mkdtemp(prefix='omega-od05w-cli-'))
pinfile=base/'pins.json'
pinfile.write_text(json.dumps({'schema_version':'od05t.pins/v1','files':groups['seed']['entries']}))
allowed=[original/g['repository_root']/n for g in groups.values() for n,_,_ in g['entries']]
state=control.activate_guard(original,base,allowed)
results=[]
for extra in ([],['--report-version','1'],['--payload-integrity']):
    argv=['--root','seed','--expected-pins',str(pinfile),*extra]
    text=io.StringIO();tick=time.monotonic();started=datetime.now(UTC).isoformat()
    with contextlib.redirect_stdout(text):code=cli.main(argv,repo=original)
    parsed=json.loads(text.getvalue())
    results.append({'entry':'audit_local_archive_presence.main','argv':argv,'start_utc':started,'end_utc':datetime.now(UTC).isoformat(),'exit_code':code,'elapsed_seconds':time.monotonic()-tick,'schema_version':parsed.get('schema_version'),'counts':parsed.get('counts'),'refusal':parsed.get('reason_code'),'payload_bytes_read':parsed['payload_bytes_read']})
state['active']=False
assert [r['exit_code'] for r in results]==[0,2,2]
control.save('original-cli-proof.json',{'class':'LOCAL_META','results':results,'guard_denials':dict(state['denials'])})
print(json.dumps(results,indent=2))
