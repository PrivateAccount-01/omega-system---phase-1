"""Explicit export list: generated reports/code/evidence only; no original reads."""
import base64,hashlib,json,stat
from pathlib import Path
B=Path('/home/parilrupani/omega-od05-final-20261117T201612Z');S=B/'staged2/repo'
prep=json.loads((B/'report-preparation.json').read_bytes())
commands=[json.loads(p.read_bytes()) for p in (B/'logs').glob('report-*-command.json')]
r=max(commands,key=lambda r:r['end_utc']);assert r['exit_code']==0
root=Path(r['argv'][r['argv'].index('--output')+1])/'final-report'
receipt=json.loads(r['worker_result']['stdout_stderr']);assert set(receipt['files'])==set(prep['files'])
files={n:root/n for n in prep['files']}
for n in prep['files']:assert hashlib.sha256(files[n].read_bytes()).hexdigest()==receipt['sha256'][n]
files['report-render-receipt.json']=B/'report-render-receipt.json';files['report-render-receipt.json'].write_text(json.dumps(receipt,indent=2))
for n in ['implementation.patch','code-delivery-manifest.json','negative-first-freeze.json','prior-read.json','source-implementation-inspection.json','runtime-inventory.json','report-preparation.json','bootstrap.py','bootstrap2.py','bootstrap-result.json','bootstrap-result2.json','inputs2.json','policy2.json','final_worker.py','run.py','run-before-manifest-fix.py','static_ruff.py','build_report_inputs.py']:
 files['support/'+n]=B/n
for row in prep['changes']:
 p=S/row['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==row['after_sha256'];files['code/'+row['path']]=p
files['implementation.patch']=B/'implementation.patch'
for p in sorted((B/'logs').iterdir()):
 assert p.is_file() and p.suffix=='.json';files['logs/'+p.name]=p
for n,p in files.items():
 assert p.is_relative_to(B) and not p.is_symlink();st=p.lstat();assert stat.S_ISREG(st.st_mode) and st.st_nlink==1 and st.st_size<8_000_000
 raw=p.read_bytes();assert len(raw)==st.st_size
 print(json.dumps({'path':n,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'base64':base64.b64encode(raw).decode()}),flush=True)
