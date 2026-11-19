"""Seal explicitly allowlisted data-free evidence; no original checkout access."""
import hashlib,json,stat
from pathlib import Path
from datetime import datetime,UTC
B=Path('/home/parilrupani/omega-od07-final-20261119T175351Z');S=B/'staged2/repo'
def load(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
prep=load(B/'report-preparation.json')
c=max((load(p) for p in (B/'logs').glob('report-*-command.json')),key=lambda r:r['end_utc'])
assert c['exit_code']==0 and c['worker_result']['exit_code']==0
receipt=json.loads(c['worker_result']['stdout_stderr']);assert set(receipt['files'])==set(prep['files'])
rendered=Path(c['argv'][c['argv'].index('--output')+1])/'final-report'
E=B/'delivery/docs/omegadata_v2/implementation/od07-final/20261119T175351Z';E.mkdir(parents=True)
items={n:rendered/n for n in prep['files']}
for n in prep['files']:assert sha(items[n])==receipt['sha256'][n]
support=['setup.py','bootstrap.py','bootstrap-result2.json','inputs2.json','policy2.json','prior-evidence-read.json','adoption.json','run.py','final_worker.py','freeze.py','freeze_review.py','freeze_scope.py','freeze_factor_review.py','negative-first-freeze.json','review-freeze.json','scope-freeze.json','factor-review-freeze.json','negative-first-source.py','review-negative-source.py','scope-negative-source.py','factor-review-source.py','extend_repository.py','extend_upstream.py','fix_review.py','fix_factor_review.py','type_fixes.py','type_fix2.py','type_fix3.py','format_code.py','static_ruff.py','inventory_review.py','runtime-inventory.json','reviewed-new-tests.json','new-test-classification-review.json','reviewed-new-tests-80-historical.json','new-test-classification-review-80-historical.json','final-source-manifest.json','phase-source-changes.json','combined-delivery-manifest.json','build_dossier.py','report-preparation.json','report-input-index.json','seal_delivery.py']
for n in support:items['support/'+n]=B/n
for n in ['implementation.patch','phase-only.patch']:items[n]=B/n
for row in prep['delivery']:
 p=S/row['path'];assert sha(p)==row['after_sha256'];items['code/'+row['path']]=p
for p in (B/'logs').iterdir():
 assert p.is_file() and p.suffix=='.json';items['logs/'+p.name]=p
for p in (B/'logs').glob('od07final-*-command.json'):
 c=load(p)
 if c['exit_code'] and c.get('worker_result'):
  m=load(p.with_name(p.name.replace('-command.json','-manifest.json')))
  pin=next(r['sha256'] for r in m['files'] if r['path']=='tests/unit/test_od07_final.py')
  source=Path(c['argv'][c['argv'].index('--output')+1])/'repo/tests/unit/test_od07_final.py'
  assert sha(source)==pin;items['negative-sources/'+pin+'.py']=source
pins={}
for n,p in sorted(items.items()):
 assert p.is_relative_to(B) and not p.is_symlink() and p.suffix in {'.py','.json','.md','.patch'}
 st=p.lstat();assert stat.S_ISREG(st.st_mode) and st.st_nlink==1 and st.st_size<8_000_000
 raw=p.read_bytes();assert len(raw)==st.st_size
 out=E/n;out.parent.mkdir(parents=True,exist_ok=True)
 with out.open('xb') as f:f.write(raw)
 assert sha(out)==hashlib.sha256(raw).hexdigest();pins[n]={'bytes':len(raw),'sha256':sha(out)}
for n,v in [('report-render-receipt.json',receipt),('export-verification.json',{'utc':datetime.now(UTC).isoformat(),'verified_files':len(items),'phase_changes':9,'combined_delivery_files':28,'live_safe_snapshot':True,'original_checkout_integrated':False,'commit_push_release':False,'new_original_payload_reads_hashes_copies':0})]:
 p=E/n
 with p.open('x') as f:json.dump(v,f,indent=2)
 pins[n]={'bytes':p.stat().st_size,'sha256':sha(p)}
p=E/'evidence-sha256.json'
with p.open('x') as f:json.dump({'schema_version':'od07-final.evidence/v1','utc':datetime.now(UTC).isoformat(),'files':pins,'excluded':['evidence-sha256.json']},f,indent=2)
for n,row in pins.items():assert sha(E/n)==row['sha256'] and (E/n).stat().st_size==row['bytes']
print(json.dumps({'directory':str(E),'sealed_files':len(pins),'total_files':len(pins)+1,'seal_sha256':sha(p),'engineering':'PASS','financial':'BLOCKED_REAL_DATA'}))
