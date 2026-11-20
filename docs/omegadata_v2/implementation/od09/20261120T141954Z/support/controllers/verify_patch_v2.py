import difflib,hashlib,json,subprocess,time
from pathlib import Path
from datetime import UTC,datetime
B=Path(__file__).resolve().parent;S=B/'staged/repo'
m=json.loads((B/'preservation-final.json').read_bytes());base=Path('/home/parilrupani/omega-od05xr1-r1-afb1e01c18/output/repo');old=Path('/home/parilrupani/omega-od08-20261119T184624Z/staged2/repo')
# Preserve an actual independent reproduction of the package-only patch syntax defect.
r=subprocess.run(['/usr/bin/git','--no-optional-locks','apply','--check',str(B/'implementation-final.patch')],cwd=B/'combined-patch-replay',capture_output=True,text=True,timeout=20)
(B/'patch-first-failure.json').write_text(json.dumps({'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'utc':datetime.now(UTC).isoformat(),'cause':'Missing final newline in retained upstream test source was not represented with a unified-diff EOF marker. Application source unchanged.'},indent=2))
def patch(rows,source):
 result=[]
 for row in sorted(rows,key=lambda r:r['path']):
  name=row['path'];before=(source/name).read_bytes().decode().splitlines(keepends=True) if row.get('before_sha256') is not None else []
  after=(S/name).read_bytes().decode().splitlines(keepends=True)
  for line in difflib.unified_diff(before,after,fromfile='a/'+name if row.get('before_sha256') is not None else '/dev/null',tofile='b/'+name):
   result.append(line if line.endswith('\n') else line+'\n\\ No newline at end of file\n')
 return ''.join(result).encode()
(B/'implementation-v2.patch').write_bytes(patch(m['combined_delivery'],base))
for phase in ('A','B'):(B/('stage-'+phase.lower()+'-v2.patch')).write_bytes(patch([r for r in m['changes'] if r['stage']==phase],old))
root=B/'combined-patch-replay-v2';root.mkdir();commands=[]
for row in m['combined_delivery']:
 if row['before_sha256']:
  raw=(base/row['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['before_sha256']
  p=root/row['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
for option in ('--check',None):
 argv=['/usr/bin/git','--no-optional-locks','apply']+([option] if option else [])+[str(B/'implementation-v2.patch')]
 tick=time.monotonic();start=datetime.now(UTC).isoformat();r=subprocess.run(argv,cwd=root,capture_output=True,text=True,timeout=20)
 commands.append(dict(argv=argv,cwd=str(root),start_utc=start,end_utc=datetime.now(UTC).isoformat(),seconds=time.monotonic()-tick,exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr))
 (B/'patch-replay-v2-command.json').write_text(json.dumps(commands,indent=2));assert r.returncode==0,commands
for row in m['combined_delivery']:assert hashlib.sha256((root/row['path']).read_bytes()).hexdigest()==row['after_sha256'],row['path']
record={'status':'PASS','replayed_files':len(m['combined_delivery']),'commands':commands,'original_checkout_accessed':False,'git_object_store_used':False,'source_inputs':'Exact approved code-only before-hash files; corrected EOF-aware unified diff only','patch_sha256':hashlib.sha256((B/'implementation-v2.patch').read_bytes()).hexdigest()}
(B/'patch-replay-v2.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))