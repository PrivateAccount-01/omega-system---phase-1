import json,hashlib,difflib,subprocess,time
from pathlib import Path
from datetime import UTC,datetime
B=Path(__file__).parent;S=B/'staged/repo';base=Path('/home/parilrupani/omega-od05xr1-r1-afb1e01c18/output/repo')
up=json.loads((B/'upstream-adoption.json').read_bytes())
new=['src/omegadata/canonical_storage/'+n+'.py' for n in ('__init__','contracts','schema','admission','store','query')]+['scripts/od10_structural_experiments.py','scripts/od10_isolated_jobs.py','tests/unit/test_od10_canonical_storage.py']
combined=list(up['combined_files']);changes=[]
for n in new:
 assert not (base/n).exists()
 raw=(S/n).read_bytes();row={'path':n,'before_sha256':None,'after_sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'state':'APPLIED_AND_TESTED_DATA_FREE_SNAPSHOT'}
 changes.append(row);combined.append(row)
assert len(combined)==60
for r in combined:assert hashlib.sha256((S/r['path']).read_bytes()).hexdigest()==r['after_sha256']
oldpins=json.loads((B/'upstream-pins.json').read_bytes())
for n,h in oldpins.items():assert hashlib.sha256((S/n).read_bytes()).hexdigest()==h,n
pres={'reviewed_head':up['reviewed_head'],'safe_workspace':str(S),'upstream_unchanged':len(oldpins),'changes':changes,'combined_delivery':combined,'original_checkout_integrated':False,'original_payload_access':False}
(B/'preservation-final.json').write_text(json.dumps(pres,indent=2))
def patch(rows):
 result=[]
 for r in sorted(rows,key=lambda x:x['path']):
  n=r['path'];before=(base/n).read_bytes().decode().splitlines(keepends=True) if r.get('before_sha256') else []
  after=(S/n).read_bytes().decode().splitlines(keepends=True)
  for line in difflib.unified_diff(before,after,fromfile='a/'+n if before else '/dev/null',tofile='b/'+n):result.append(line if line.endswith('\n') else line+'\n\\ No newline at end of file\n')
 return ''.join(result).encode()
(B/'implementation.patch').write_bytes(patch(combined));(B/'od10-only.patch').write_bytes(patch(changes))
root=B/'combined-patch-replay-v2';root.mkdir();commands=[]
for r in combined:
 if r.get('before_sha256'):
  raw=(base/r['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==r['before_sha256']
  p=root/r['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
for opt in ('--check',None):
 argv=['/usr/bin/bwrap','--unshare-all','--die-with-parent','--new-session','--cap-drop','ALL','--clearenv','--ro-bind','/usr','/usr','--symlink','usr/lib','/lib','--symlink','usr/lib64','/lib64','--dev','/dev','--proc','/proc','--ro-bind',str(B/'implementation.patch'),'/patch','--bind',str(root),'/replay','--chdir','/replay','/usr/bin/git','--no-optional-locks','apply']+([opt] if opt else [])+['/patch']
 start=datetime.now(UTC).isoformat();tick=time.monotonic();r=subprocess.run(argv,capture_output=True,text=True,timeout=30)
 commands.append({'argv':argv,'start_utc':start,'end_utc':datetime.now(UTC).isoformat(),'seconds':time.monotonic()-tick,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr});assert r.returncode==0,commands
for r in combined:assert hashlib.sha256((root/r['path']).read_bytes()).hexdigest()==r['after_sha256']
(B/'patch-replay.json').write_text(json.dumps({'status':'PASS','replayed_files':60,'commands':commands,'git_object_store_mounted':False,'original_checkout_mounted':False,'patch_sha256':hashlib.sha256((B/'implementation.patch').read_bytes()).hexdigest()},indent=2))
print('60-file combined patch replay PASS; 3852 upstream identities retained')