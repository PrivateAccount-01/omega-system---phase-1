"""Seal explicit code-only OD07 deliverables. No original checkout access or Git."""
import hashlib,json,stat
from datetime import UTC,datetime
from pathlib import Path
B=Path('/home/parilrupani/omega-od07-20261119T171019Z');S=B/'staged2/repo'
def load(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
prep=load(B/'report-preparation.json')
r=max((load(p) for p in (B/'logs').glob('report-*-command.json')),key=lambda r:r['end_utc'])
assert r['exit_code']==0 and r['worker_result']['exit_code']==0
receipt=json.loads(r['worker_result']['stdout_stderr']);assert set(receipt['files'])==set(prep['files'])
rendered=Path(r['argv'][r['argv'].index('--output')+1])/'final-report'
E=B/'delivery/docs/omegadata_v2/implementation/od07/20261119T171019Z';E.mkdir(parents=True)
items={n:rendered/n for n in prep['files']}
for n in prep['files']:assert sha(items[n])==receipt['sha256'][n]
# Enumerate only this task's known controller files, never the original repository.
support=['setup.py','bootstrap.py','bootstrap-result2.json','inputs2.json','policy2.json','upstream-evidence-read.json','adoption.json','run.py','final_worker.py','freeze.py','freeze_review.py','freeze_integrity.py','freeze_sql.py','freeze_decimal.py','negative-first-freeze.json','review-freeze.json','integrity-freeze.json','sql-freeze.json','decimal-freeze.json','implement.py','fix_review.py','fix_timezone.py','fix_integrity.py','fix_static.py','fix_sql.py','fix_decimal.py','format_code.py','static_ruff.py','prepare_final_verification.py','inspect_legacy.py','legacy-audit-source-inventory.json','upstream-manifest.json','final-source-manifest.json','phase-source-changes.json','combined-delivery-manifest.json','runtime-inventory.json','reviewed-new-tests.json','reviewed-new-tests-95-historical.json','reviewed-new-tests-99-historical.json','new-test-classification-review.json','new-test-classification-95-historical.json','new-test-classification-99-historical.json','build_dossier.py','report-preparation.json','report-input-index.json','seal_delivery.py']
for n in support:items['support/'+n]=B/n
items['implementation.patch']=B/'implementation.patch'
for row in prep['delivery']:
 p=S/row['path'];assert sha(p)==row['after_sha256'];items['code/'+row['path']]=p
for p in (B/'logs').iterdir():
 assert p.is_file() and p.suffix=='.json'
 items['logs/'+p.name]=p
for p in (B/'logs').glob('od07-*-command.json'):
 c=load(p)
 if c['exit_code']!=0 and c.get('worker_result'):
  m=load(p.with_name(p.name.replace('-command.json','-manifest.json')))
  pin=next(r['sha256'] for r in m['files'] if r['path']=='tests/unit/test_od07_adjustments.py')
  source=Path(c['argv'][c['argv'].index('--output')+1])/'repo/tests/unit/test_od07_adjustments.py'
  assert sha(source)==pin
  items['negative-sources/'+pin+'.py']=source
pins={}
for n,p in sorted(items.items()):
 assert p.is_relative_to(B) and not p.is_symlink() and p.suffix in {'.json','.md','.py','.patch'}
 st=p.lstat();assert stat.S_ISREG(st.st_mode) and st.st_nlink==1 and st.st_size<8_000_000
 raw=p.read_bytes();assert len(raw)==st.st_size
 out=E/n;out.parent.mkdir(parents=True,exist_ok=True)
 with out.open('xb') as f:f.write(raw)
 assert sha(out)==hashlib.sha256(raw).hexdigest()
 pins[n]={'bytes':len(raw),'sha256':sha(out)}
for n,body in [('report-render-receipt.json',receipt),('export-verification.json',{'utc':datetime.now(UTC).isoformat(),'verified_files':len(items),'phase_changes':8,'combined_delivery_files':24,'live_safe_snapshot':True,'original_checkout_integrated':False,'commit_push_release':False,'original_payload_reads_hashes_copies':0})]:
 p=E/n
 with p.open('x') as f:json.dump(body,f,indent=2)
 pins[n]={'bytes':p.stat().st_size,'sha256':sha(p)}
seal=E/'evidence-sha256.json'
with seal.open('x') as f:json.dump({'schema_version':'od07.evidence/v1','utc':datetime.now(UTC).isoformat(),'files':pins,'excluded':['evidence-sha256.json']},f,indent=2)
for n,row in pins.items():assert sha(E/n)==row['sha256'] and (E/n).stat().st_size==row['bytes']
print(json.dumps({'directory':str(E),'sealed_files':len(pins),'total_files':len(pins)+1,'seal_sha256':sha(seal),'engineering':'PASS','financial':'BLOCKED_REAL_DATA'}))
