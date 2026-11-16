"""Actual CLI workers, guarded in-process before invoking the main entry point."""
import contextlib
import json
import os
import runpy
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT=Path.cwd();HERE=Path(__file__).resolve().parent;LOGS=HERE/'logs'
sys.path.insert(0,str(ROOT/'src'))
# Warm imports before the audit guard. Never import an acquisition job.
from omegadata.parsers.local_archive_presence import ROOTS

label=sys.argv[1]
group=json.loads((ROOT/'docs/omegadata_v2/implementation/od05t/20261116T100613Z/logs/frozen-metadata-pins.json').read_text())['groups'][label]
external=Path(tempfile.mkdtemp(prefix='omega-od05v-cli-'))
pins=external/'pins.json';pins.write_text(json.dumps({'schema_version':'od05t.pins/v1','files':group['entries']}),encoding='utf-8')
output=external/'report'
args=[str(ROOT/'scripts/audit_local_archive_presence.py'),'--root',label,'--expected-pins',str(pins),'--output-dir',str(output)]
argv=[sys.executable,'-B',*args]
active=True
def audit(event,items):
    if not active:return
    if event.startswith('socket.') or event in {'subprocess.Popen','os.system','os.posix_spawn'}:raise RuntimeError('EGRESS_DENIED')
    if event=='open' and not isinstance(items[0],int):
        path,mode,flags=items;p=Path(os.fsdecode(path)).absolute()
        if p.is_relative_to(ROOT/'data') and not p.name.endswith('.manifest.json'):raise RuntimeError('MARKET_PAYLOAD_DENIED')
        if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND) and not p.is_relative_to(external):raise RuntimeError('PROTECTED_WRITE')
sys.addaudithook(audit)
started=datetime.now(UTC).isoformat();sys.argv=args
try:
    with (external/'stdout.json').open('x',encoding='utf-8') as out,contextlib.redirect_stdout(out):
        try:runpy.run_path(args[0],run_name='__main__')
        except SystemExit as e:code=int(e.code or 0)
finally:active=False
body=json.loads((output/'presence.json').read_text())
with (LOGS/('cli-'+label+'.json')).open('x',encoding='utf-8') as f:
    json.dump({'command':argv,'guarded_worker':[sys.executable,'-B',str(Path(__file__)),label],
      'cwd':str(ROOT),'start_utc':started,'end_utc':datetime.now(UTC).isoformat(),'exit_code':code,
      'counts':body['counts'],'fresh_external_output':True,'payload_bytes_read':0},f,indent=2)
print(label,code,body['counts'])
raise SystemExit(0 if code==(2 if label=='seed' else 0) else 1)
