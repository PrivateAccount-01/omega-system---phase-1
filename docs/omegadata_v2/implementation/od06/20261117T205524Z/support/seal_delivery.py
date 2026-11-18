"""Exact allowlisted evidence export inside this data-free workspace only."""
import hashlib,json,stat
from datetime import UTC,datetime
from pathlib import Path
B=Path('/home/parilrupani/omega-od06-20261117T205524Z');S=B/'staged2/repo'
def load(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
prep=load(B/'report-preparation.json')
r=max((load(p) for p in (B/'logs').glob('report-*-command.json')),key=lambda r:r['end_utc'])
assert r['exit_code']==0 and r['worker_result']['exit_code']==0
root=Path(r['argv'][r['argv'].index('--output')+1])/'final-report'
receipt=json.loads(r['worker_result']['stdout_stderr']);assert set(receipt['files'])==set(prep['artifacts'])
E=B/'delivery/docs/omegadata_v2/implementation/od06/20261117T205524Z'
E.mkdir(parents=True)
files={n:root/n for n in prep['artifacts']}
for n in prep['artifacts']:assert sha(files[n])==receipt['sha256'][n]
for n in ['bootstrap.py','bootstrap-result2.json','inputs2.json','policy2.json','adoption.json',
          'negative-first-freeze.json','negative-first-freeze-v2.json','adversarial-freeze.json',
          'review-freeze.json','intake-freeze.json','run.py','final_worker.py','runtime-inventory.json',
          'static_ruff.py','fix_ruff.py','prepare_reports.py','prepare_final.py','report-preparation.json',
          'source-changes.json','report-input-index.json','seal_delivery.py']:
 files['support/'+n]=B/n
files['implementation.patch']=B/'implementation.patch'
for row in prep['changes']:
 p=S/row['path'];assert sha(p)==row['after_sha256'];files['code/'+row['path']]=p
for p in (B/'logs').iterdir():
 assert p.is_file() and p.suffix=='.json'
 files['logs/'+p.name]=p
for p in (B/'logs').glob('od06-*-command.json'):
 c=load(p)
 if c['exit_code']!=0:
  m=load(p.with_name(p.name.replace('-command.json','-manifest.json')))
  row=next(r for r in m['files'] if r['path']=='tests/unit/test_od06_contracts.py')
  source=Path(c['argv'][c['argv'].index('--output')+1])/'repo/tests/unit/test_od06_contracts.py'
  assert sha(source)==row['sha256']
  files['negative-sources/'+row['sha256']+'.py']=source
pins={}
for n,p in sorted(files.items()):
 assert p.is_relative_to(B) and not p.is_symlink()
 st=p.lstat();assert stat.S_ISREG(st.st_mode) and st.st_nlink==1 and st.st_size<8_000_000
 data=p.read_bytes();assert len(data)==st.st_size
 out=E/n;out.parent.mkdir(parents=True,exist_ok=True)
 with out.open('xb') as f:f.write(data)
 assert sha(out)==hashlib.sha256(data).hexdigest()
 pins[n]={'bytes':len(data),'sha256':sha(out)}
for name,value in [('report-render-receipt.json',receipt),('export-verification.json',
 {'utc':datetime.now(UTC).isoformat(),'files_verified':len(files),'market_payload_reads':0,
  'market_payload_read_scope':'This exporter has only exact generated code/metadata inputs in B; no original paths opened',
  'source_changes':prep['changes'],'original_checkout_integration':False,
  'controller_transport_issue':'Windows UNC edit timed out and empty prepare_reports.py preserved; native preparation used subsequently; no source/data mutation',
  'report_exit_code':0})]:
 out=E/name
 with out.open('x') as f:json.dump(value,f,indent=2)
 pins[name]={'bytes':out.stat().st_size,'sha256':sha(out)}
seal=E/'evidence-sha256.json'
with seal.open('x') as f:json.dump({'schema_version':'od06.evidence/v1','utc':datetime.now(UTC).isoformat(),'files':pins,'excluded':['evidence-sha256.json']},f,indent=2)
for n,meta in pins.items():assert sha(E/n)==meta['sha256'] and (E/n).stat().st_size==meta['bytes']
print(json.dumps({'evidence_directory':str(E),'sealed_files':len(pins),'seal_sha256':sha(seal),'new_source_file_count':len(prep['changes'])}))
