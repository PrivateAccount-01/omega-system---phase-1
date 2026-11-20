"""Seal exact data-free rendered outputs, source pins and recorded execution evidence."""
import hashlib,json,stat
from pathlib import Path
from datetime import UTC,datetime
B=Path(__file__).resolve().parent;S=B/'staged/repo'
def load(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
state=load(B/'evidence-build-state.json');M=load(B/'preservation-final.json');pins=load(B/'final-source-pins-final.json')
assert all(sha(S/n)==h for n,h in pins.items())
rp=max((B/'logs').glob('report-*-command.json'),key=lambda p:load(p)['start_utc']);r=load(rp);assert r['exit_code']==0
receipt=json.loads(r['worker_result']['stdout_stderr']);assert receipt['git_calls']==0 and not receipt['original_repository_mounted'] and sorted(receipt['files'])==state['artifacts']
tag=rp.name.removesuffix('-command.json');rendered=B/tag/'output/final-report';root=Path(state['package_root']);root.mkdir(parents=True)
files={}
def put(source,name,expected=None):
 assert name not in files and '..' not in Path(name).parts and not Path(name).is_absolute()
 st=source.lstat();assert stat.S_ISREG(st.st_mode) and not source.is_symlink() and st.st_nlink==1,str(source)
 raw=source.read_bytes();h=hashlib.sha256(raw).hexdigest();assert expected is None or h==expected,(name,expected,h)
 dest=root/name;dest.parent.mkdir(parents=True,exist_ok=True)
 with dest.open('xb') as f:f.write(raw)
 files[name]={'sha256':h,'bytes':len(raw)}
def write(name,value):
 raw=(json.dumps(value,indent=2)+'\n').encode();p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(raw)
 files[name]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
for name in receipt['files']:put(rendered/name,name,receipt['sha256'][name])
for row in M['combined_delivery']:put(B/'source-delivery-final'/row['path'],'source/'+row['path'],row['after_sha256'])
for src,dst in [('implementation-v2.patch','implementation.patch'),('stage-a-v2.patch','stage-a.patch'),('stage-b-v2.patch','stage-b.patch')]:put(B/src,dst)
paths=set(state['record_files'])
paths.update(str(B/'logs'/(tag+suffix)) for suffix in ('-command.json','-manifest.json','-policy.json'))
for name in sorted(paths):p=Path(name);assert p.parent==B/'logs';put(p,'support/logs/'+p.name)
for tag in sorted(set(state['chosen_tags']+[tag]+[v['tag'] for v in state['negative_first']])):
 out=B/tag/'output'
 for leaf,dest in [('native-probes.json','native-probes.json'),('job/result.json','result.json'),('job/coverage.json','coverage.json')]:
  p=out/leaf
  if p.exists():put(p,'support/jobs/'+tag+'/'+dest)
for row in state['negative_first']:put(B/row['tag']/'output/repo'/row['test_path'],row['frozen_source'],row['test_sha256_before_fix'])
write('support/negative-first.json',state['negative_first'])
root_names=['upstream-adoption.json','upstream-pins.json','final-source-pins-final.json','preservation-final.json','final-ref-identity.json','sealed-classification.json','runtime-inventory.json','stagea-runtime-inventory.json','stagea-gate.json','stagea-source-inventory.json','legacy-source-audit-final.json','bootstrap-command.json','inputs.json','policy.json','tolerance-recovery.json','tolerance-empty-attempt.bin.txt','patch-first-failure.json','patch-replay-v2.json','patch-replay-v2-command.json','implementation-final.patch','evidence-build-state.json']
root_names += ['stagea-negative-first-freeze.json','stagea-extension-freeze.json','stagea-window-freeze.json','stagea-reference-instant-freeze.json','stagea-median-ratio-freeze.json','od09-negative-first-freeze.json','od09-review-freeze.json','od09-reprocess-freeze.json','od09-performance-freeze.json','od09-refusal-freeze.json','od09-upstream-proof-freeze.json','od09-completion-authority-freeze.json','od09-progress-freeze.json','od09-final-regression-freeze.json']
for name in root_names:put(B/name,'support/'+name)
for name in ('bootstrap.py','run.py','run_report.py','worker.py','static_ruff.py','build_evidence.py','package_evidence.py','prepare_preservation.py','prepare_preservation_final.py','verify_patch.py','verify_patch_v2.py','recover_tolerances.py','classify_sealed.py'):
 put(B/name,'support/controllers/'+name)
for name in ('od05w_safe_harness.py','od05x_isolated_runner.py','od05x_worker_jobs.py','od05x_base_worker_jobs.py','od05v_presence_oracle.py'):
 put(S/'scripts'/name,'support/accepted-runner/'+name,pins['scripts/'+name])
for p in (B/'staged').glob('receipt-*.json'):put(p,'support/'+p.name)
for name in ('manifest.json','summary.json'):put(B/'report-inputs'/name,'support/report-inputs/'+name)
write('support/render-receipt.json',receipt)
# Independent current-read preservation recheck: only previously enumerated approved evidence/code paths.
prior=Path('/home/parilrupani/omega-od08-20261119T184624Z/delivery/docs/omegadata_v2/implementation/od08/20261119T184624Z')
seal=load(prior/'evidence-sha256.json');assert all(sha(prior/n)==v['sha256'] for n,v in seal['files'].items())
put(prior/'evidence-sha256.json','support/prior-od08-evidence-seal.json')
write('support/final-boundary-reconciliation.json',{'utc':datetime.now(UTC).isoformat(),'prior_sealed_files_unchanged':len(seal['files']),'original_application_integrated':False,'original_financial_payloads_read_hashed_copied':0,'source_policy_changed':False,'incidents_self_approved':False,'final_source_pins_reverified':len(pins),'rendering':{'record':'support/logs/'+rp.name,'git_calls':0,'boundary':receipt['boundary']},'financial_acceptance':'BLOCKED_REAL_DATA','windows_native':'NOT_CERTIFIED','new_phase_execution':'NONE','commit_push_merge_release_sign_trade':'NOT_PERFORMED'})
# Seal contains every package file except itself; all writes were exclusive, no old evidence reused.
sealout={'schema_version':'omegadata.evidence-sha256/v1','utc':datetime.now(UTC).isoformat(),'files':dict(sorted(files.items()))}
with (root/'evidence-sha256.json').open('x') as f:json.dump(sealout,f,indent=2)
assert all(sha(root/n)==v['sha256'] for n,v in files.items())
result={'root':str(root),'sealed_files':len(files),'total_bytes':sum(v['bytes'] for v in files.values()),'seal_sha256':sha(root/'evidence-sha256.json'),'source_files':len(M['combined_delivery']),'reports':len(receipt['files']),'all_hashes_reverified':True}
(B/'final-package-verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))