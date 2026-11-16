"""Actual trusted CLI worker commands, outputs summarized without source records."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT=Path.cwd();HERE=Path(__file__).resolve().parent;LOGS=HERE/'logs'
group=json.loads((LOGS/'frozen-metadata-pins.json').read_text())['groups']['cache']
private=Path(tempfile.mkdtemp(prefix='omega-od05t-cli-'))
pinfile=private/'pins.json'
pinfile.write_text(json.dumps({'schema_version':'od05t.pins/v1','files':group['entries']}),encoding='utf-8')
script=ROOT/'scripts/audit_existing_market_archive.py'
root=ROOT/group['repository_root']
base=['--manifest-root',str(root),'--expected-pins',str(pinfile),'--metadata-only']
checks=[('help',['--help'],0),('invalid',['--unknown'],2),
    ('dry-run',base+['--dry-run'],0),('real-acceptance-refused',base+['--dry-run','--require-real-data'],3),
    ('populated-output',base+['--output-dir',str(private/'report')],0),
    ('existing-output-refused',base+['--output-dir',str(private/'report')],2),
    ('protected-output-refused',base+['--output-dir',str(root/'od05t-output-must-not-exist')],2),
    ('unknown-source-refused',base+['--dry-run','--source-key','NSE_FO_BHAVCOPY'],2)]
records=[]
for name,args,expected in checks:
    cmd=[sys.executable,'-B',str(script),*args];start=datetime.now(UTC).isoformat()
    result=subprocess.run(cmd,capture_output=True,text=True,env={**os.environ,'PYTHONPATH':str(ROOT/'src'),'PYTHONDONTWRITEBYTECODE':'1'})
    row={'name':name,'argv':cmd,'cwd':str(ROOT),'start_utc':start,'end_utc':datetime.now(UTC).isoformat(),
         'exit_code':result.returncode,'expected_exit_code':expected,'stdout_sha256':hashlib.sha256(result.stdout.encode()).hexdigest()}
    if result.stdout.startswith('{'):
        report=json.loads(result.stdout);report.pop('candidates',None);row['output']=report
    else:row['stdout']=result.stdout;row['stderr']=result.stderr
    records.append(row)
    assert result.returncode==expected,(name,result.returncode)
with (LOGS/'cli-process-probes.json').open('x',encoding='utf-8') as f:json.dump(records,f,indent=2)
print('Eight actual CLI process probes matched explicit expected exit codes.')
