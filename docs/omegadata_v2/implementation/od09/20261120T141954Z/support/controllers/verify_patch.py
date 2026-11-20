import hashlib,json,subprocess,time
from pathlib import Path
from datetime import UTC,datetime
B=Path(__file__).resolve().parent
m=json.loads((B/'preservation-final.json').read_bytes())
root=B/'combined-patch-replay';root.mkdir()
base=Path('/home/parilrupani/omega-od05xr1-r1-afb1e01c18/output/repo')
for row in m['combined_delivery']:
 if row['before_sha256']:
  raw=(base/row['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['before_sha256']
  p=root/row['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
commands=[]
for option in ('--check',None):
 argv=['/usr/bin/git','--no-optional-locks','apply']+([option] if option else [])+[str(B/'implementation-final.patch')]
 tick=time.monotonic();start=datetime.now(UTC).isoformat();r=subprocess.run(argv,cwd=root,capture_output=True,text=True,timeout=20)
 commands.append(dict(argv=argv,cwd=str(root),start_utc=start,end_utc=datetime.now(UTC).isoformat(),seconds=time.monotonic()-tick,exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr))
 assert r.returncode==0,commands
for row in m['combined_delivery']:
 assert hashlib.sha256((root/row['path']).read_bytes()).hexdigest()==row['after_sha256'],row['path']
record={'status':'PASS','replayed_files':len(m['combined_delivery']),'commands':commands,'original_checkout_accessed':False,'git_object_store_used':False,'source_inputs':'Exact approved code-only before-hash files; delivered unified diff only'}
(B/'patch-replay.json').write_text(json.dumps(record,indent=2))
print(json.dumps(record))