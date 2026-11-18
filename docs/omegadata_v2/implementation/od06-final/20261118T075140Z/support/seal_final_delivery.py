"""Seal the exact code-only final OD06 delivery; no original checkout access."""
import hashlib,json,stat
from datetime import UTC,datetime
from pathlib import Path
B=Path('/home/parilrupani/omega-od06-final-20261118T075140Z');S=B/'staged2/repo'
def load(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
prep=load(B/'report-preparation.json')
r=max((load(p) for p in (B/'logs').glob('report-*-command.json')),key=lambda r:r['end_utc'])
assert r['exit_code']==0 and r['worker_result']['exit_code']==0
receipt=json.loads(r['worker_result']['stdout_stderr'])
assert set(receipt['files'])==set(prep['files'])
root=Path(r['argv'][r['argv'].index('--output')+1])/'final-report'
E=B/'delivery/docs/omegadata_v2/implementation/od06-final/20261118T075140Z';E.mkdir(parents=True)
files={n:root/n for n in prep['files']}
for n in prep['files']:assert sha(files[n])==receipt['sha256'][n]
support=['setup.py','bootstrap.py','bootstrap-result2.json','inputs2.json','policy2.json','prior-evidence-read.json',
'adoption.json','run.py','final_worker.py','freeze.py','freeze_review.py','freeze_reliability.py',
'freeze_semantic.py','freeze_controller.py','freeze_trust_root.py','negative-first-freeze.json','review-freeze.json',
'reliability-freeze.json','semantic-freeze.json','controller-freeze.json','trust-root-freeze.json',
'apply_foundation_changes.py','fix_review.py','add_reliability.py','prepare_verification.py','make_formatter.py',
'format_code.py','static_ruff.py','fix_ruff.py','fix_style.py','fix_experiment_syntax.py','prepare_guarded_experiments.py',
'fix_owner_trust_root.py','prepare_shared_final.py','launch_shared.py','launch_shared_final.py','launch_shared_guarded.py',
'shared_experiments.py','shared_experiments_final.py','accepted_process_experiments.py','run_shared.py',
'run_shared_final.py','run_shared_guarded.py','accepted-process-experiments.json','inspect_consumers.py',
'fix_consumer_inspection.py','prepare_final_inspection.py','inspect_consumers_final.py','complete-consumer-inventory.json',
'complete-consumer-inventory-final.json','runtime-inventory.json','build_final_dossier.py','report-preparation.json',
'report-input-index.json','source-changes.json','combined-delivery-manifest.json','seal_final_delivery.py']
for n in support:files['support/'+n]=B/n
files['implementation.patch']=B/'implementation.patch'
for row in prep['delivery']:
 p=S/row['path'];assert sha(p)==row['after_sha256'];files['code/'+row['path']]=p
for p in (B/'logs').iterdir():
 assert p.is_file() and p.suffix=='.json';files['logs/'+p.name]=p
for p in (B/'logs').glob('foundation-*-command.json'):
 c=load(p)
 if c['exit_code']!=0:
  m=load(p.with_name(p.name.replace('-command.json','-manifest.json')))
  pin=next(r['sha256'] for r in m['files'] if r['path']=='tests/unit/test_od06_foundation.py')
  source=Path(c['argv'][c['argv'].index('--output')+1])/'repo/tests/unit/test_od06_foundation.py'
  assert sha(source)==pin
  files['negative-sources/'+pin+'.py']=source
for p in (B/'logs').glob('dbcrash-*-command.json'):
 c=load(p);proof=Path(c['argv'][c['argv'].index('--output')+1])/'controlled-crash.json'
 if proof.exists():files['logs/'+p.name.replace('-command.json','-controlled-crash.json')]=proof
pins={}
for name,p in sorted(files.items()):
 assert p.is_relative_to(B) and not p.is_symlink()
 info=p.lstat();assert stat.S_ISREG(info.st_mode) and info.st_nlink==1 and info.st_size<8_000_000
 raw=p.read_bytes();assert len(raw)==info.st_size
 out=E/name;out.parent.mkdir(parents=True,exist_ok=True)
 with out.open('xb') as f:f.write(raw)
 assert sha(out)==hashlib.sha256(raw).hexdigest()
 pins[name]={'bytes':len(raw),'sha256':sha(out)}
for name,body in [('report-render-receipt.json',receipt),('export-verification.json',
 {'utc':datetime.now(UTC).isoformat(),'files_verified':len(files),'phase_changes':len(prep['phase_changes']),
  'combined_delivery_files':len(prep['delivery']),'source_application_integrated_in_data_free_snapshot':True,
  'original_checkout_integrated':False,'commit_push_release':False,'original_payload_hashing':False})]:
 out=E/name
 with out.open('x') as f:json.dump(body,f,indent=2)
 pins[name]={'bytes':out.stat().st_size,'sha256':sha(out)}
seal=E/'evidence-sha256.json'
with seal.open('x') as f:json.dump({'schema_version':'od06.final.evidence/v1','utc':datetime.now(UTC).isoformat(),'files':pins,'excluded':['evidence-sha256.json']},f,indent=2)
for n,row in pins.items():assert sha(E/n)==row['sha256'] and (E/n).stat().st_size==row['bytes']
print(json.dumps({'directory':str(E),'sealed_files':len(pins),'seal_sha256':sha(seal),'financial_verdict':'BLOCKED_REAL_DATA','engineering_verdict':'PASS'}))
