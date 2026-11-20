import importlib.util,json,hashlib,os,signal,time,traceback
from pathlib import Path
from datetime import datetime,UTC
B=Path(__file__).parent
spec=importlib.util.spec_from_file_location('launcher',B/'staged/repo/scripts/od10_isolated_jobs.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
commands=sorted((B/'logs').glob('stage_only-*-command.json'),key=lambda p:p.stat().st_mtime)
r=json.loads(commands[-1].read_bytes());assert r['exit_code']==0
T=Path(r['argv'][-1])/'launcher-result.json';H=hashlib.sha256(T.read_bytes()).hexdigest();P=Path(r['argv'][r['argv'].index('--policy')+1])
O=B/('process-experiments-'+datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ'));O.mkdir();records=[]
def save(p,v):p.write_text(json.dumps(v,indent=2))
def launch(root,name,role):
 out=root/name;p,record=mod.start_worker(T,H,P,out,root/'shared',O,role);record['start_utc']=datetime.now(UTC).isoformat();return p,record,out

def finish(job,kill=False):
 p,r,out=job
 if kill:os.killpg(p.pid,signal.SIGKILL)
 stdout,stderr=p.communicate(timeout=60);r.update(exit_code=p.returncode,stdout=stdout,stderr=stderr,end_utc=datetime.now(UTC).isoformat())
 f=out/'job/result.json';r['result']=json.loads(f.read_bytes()) if f.exists() else None
 probes=out/'native-probes.json';r['native_probes']=json.loads(probes.read_bytes()) if probes.exists() else None
 records.append(r);save(out.parent/(out.name+'-completion.json'),r)
 if not kill and (p.returncode!=0 or r['result'] is None):raise RuntimeError(str(out)+': '+stderr[-1500:])
 return r

def waitpaths(paths,jobs):
 deadline=time.monotonic()+40
 while not all(p.exists() for p in paths):
  for j in jobs:
   if j[0].poll() is not None:finish(j);raise RuntimeError('WORKER_EXITED_BEFORE_BARRIER')
  if time.monotonic()>deadline:
   for j in jobs:
    if j[0].poll() is None:finish(j,kill=True)
   raise TimeoutError(str(paths))
  time.sleep(.02)
def root(name):
 p=O/name;p.mkdir();(p/'shared').mkdir();(p/'shared/NON_MARKET_SHARED.json').write_text('{"class":"OD10_NON_MARKET_SHARED/v1"}');finish(launch(p,'initial',{'mode':'initial'}));return p
try:
 for phase in ['before_write','during_file_write','after_file_write_before_validation','after_validation_before_install','after_install_before_catalog_commit','during_catalog_transaction','after_catalog_commit_before_acknowledgement']:
  p=root(phase);attempt=launch(p,'attempt',{'mode':'attempt','phase':phase});waitpaths([p/'shared/reached.json'],[attempt])
  reader=finish(launch(p,'reader',{'mode':'reader'}))
  assert bool(reader['result']['operation_visible'])==(phase=='after_catalog_commit_before_acknowledgement')
  finish(attempt,kill=True);recovery=finish(launch(p,'recovery',{'mode':'recover'}));assert recovery['result']['old_bytes_preserved']
  print('KILL_RECOVER_PASS',phase,flush=True)
 for name,same_op,same_value in [('identical',True,True),('changed_operation_payload',True,False),('competing_parent',False,False)]:
  p=root(name);a=launch(p,'writer-a',{'mode':'race','name':'a','operation':'race','value':'1.25'})
  b=launch(p,'writer-b',{'mode':'race','name':'b','operation':'race' if same_op else 'race-b','value':'1.25' if same_value else '2.5'})
  waitpaths([p/'shared/ready-a.json',p/'shared/ready-b.json'],[a,b]);(p/'shared/go.json').write_text('{}')
  ar=finish(a)['result'];br=finish(b)['result'];outcomes=sorted([ar['outcome'],br['outcome']])
  assert outcomes==(['COMMITTED','COMMITTED'] if same_value else ['COMMITTED','REFUSED'])
  if same_value:assert ar['version']==br['version']
  assert ar['old_bytes_preserved'] and br['old_bytes_preserved'];print('PROCESS_RACE_PASS',name,flush=True)
 save(O/'summary.json',{'status':'PASS','records':records,'killed_phases':7,'races':3,'certification':'PROCESS_TERMINATION_NOT_HARDWARE_POWER_LOSS','financial_observations':0})
except BaseException:
 save(O/'summary.json',{'status':'FAIL','records':records,'traceback':traceback.format_exc()});raise