import hashlib,json,os,subprocess,sys,time,uuid
from pathlib import Path
from datetime import UTC,datetime
B=Path(__file__).resolve().parent;S=B/'staged/repo'
os.chdir(B)
RT='/home/parilrupani/omega-od02v-37b3vimd/venv312'
BASE=json.loads(next((B/'staged').glob('receipt-*.json')).read_bytes())
ALLOWED=set()
NEW=['tests/unit/test_od10_canonical_storage.py']
NEW += ['src/omegadata/canonical_storage/'+n+'.py' for n in ('__init__','contracts','schema','admission','store','query')]
NEW += ['scripts/od10_structural_experiments.py','scripts/od10_isolated_jobs.py']
(B/'logs').mkdir(exist_ok=True)
def save(p,v):
 with p.open('x') as f:json.dump(v,f,indent=2)
for job in sys.argv[1:]:
 tag=job+'-'+uuid.uuid4().hex[:10];out=B/tag;out.mkdir()
 rows=[]
 for r in BASE['files']:
  n=r['path'];p=S/n
  if n=='od05x_inputs/runtime-inventory.json':p=B/'runtime-inventory.json'
  elif n=='scripts/od05x_worker_jobs.py':p=B/'worker.py'
  st=p.lstat();assert not p.is_symlink() and st.st_nlink==1
  raw=p.read_bytes();pin=hashlib.sha256(raw).hexdigest()
  assert n in ALLOWED or n in ('scripts/od05x_worker_jobs.py','od05x_inputs/runtime-inventory.json') or pin==r['sha256'],n
  row={'path':n,'class':r['class'],'host':str(p),'device':st.st_dev,'sha256':pin,'bytes':len(raw)}
  if p==S/n and n!='scripts/od05x_isolated_runner.py':row.update(chunk_root=str(S),sandbox_source='/chunks/0/'+n)
  rows.append(row)
 for n in NEW:
  p=S/n
  if p.exists():
   raw=p.read_bytes();rows.append({'path':n,'class':'CODE','host':str(p),'device':p.lstat().st_dev,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
 manifest=B/'logs'/(tag+'-manifest.json');policy=B/'logs'/(tag+'-policy.json')
 save(manifest,{'schema_version':'od05x.inputs/v1','file_count':len(rows),'files':rows})
 save(policy,{'runtime':RT,'job':job,'outside_canary':str(B/'NON_MARKET_CANARY'),'parent_namespaces':{n:os.readlink('/proc/self/ns/'+n) for n in ('mnt','net','pid','user')}})
 argv=[RT+'/bin/python','-B',str(S/'scripts/od05x_isolated_runner.py'),'launch','--manifest',str(manifest),'--manifest-sha256',hashlib.sha256(manifest.read_bytes()).hexdigest(),'--policy',str(policy),'--output',str(out/'output')]
 start=datetime.now(UTC).isoformat();tick=time.monotonic();r=subprocess.run(argv,capture_output=True,text=True,timeout=900)
 result=out/'output/job/result.json';data=json.loads(result.read_bytes()) if result.exists() else None
 record={'cwd':str(B),'worker_cwd':'/work/repo','argv':argv,'start_utc':start,'end_utc':datetime.now(UTC).isoformat(),'seconds':time.monotonic()-tick,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'worker_result':data,'source_commit':'641f1ebc54d4619e77f36afb4821b5986ef3a756','source_manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest()}
 save(B/'logs'/(tag+'-command.json'),record)
 print(json.dumps({'job':job,'tag':tag,'exit':r.returncode,'counts':data.get('counts') if data else None,'tail':data.get('stdout_stderr','')[-8000:] if data and r.returncode else r.stderr[-2000:]}),flush=True)



