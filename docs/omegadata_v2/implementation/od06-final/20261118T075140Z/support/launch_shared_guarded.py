"""Add one exact anonymous disposable DB mount to unchanged OD05X launcher.
No source, original archive, credential, incident or signing root is exposed.
"""
import hashlib,json,os,stat,subprocess,sys,time
from pathlib import Path
B=Path('/home/parilrupani/omega-od06-final-20261118T075140Z')
S=B/'staged2/repo';ROOT=B/'shared-canary-database-accepted'
sys.path.insert(0,str(S/'scripts'))
import od05x_isolated_runner as launcher
args=sys.argv
manifest=Path(args[args.index('--manifest')+1]);pin=args[args.index('--manifest-sha256')+1]
policy=Path(args[args.index('--policy')+1]);output=Path(args[args.index('--output')+1])
job=json.loads(policy.read_bytes())['job']
assert job in {'dbinit','dbcrash','dbrecover','dbcompete-a','dbcompete-b','dbfinal'}
assert ROOT.is_dir() and not ROOT.is_symlink() and ROOT.stat().st_mode&0o077==0
assert json.loads((ROOT/'NON_MARKET_DATABASE.json').read_bytes())=={'schema_version':'od06.shared-canary/v1','market_data':False,'financial_eligible':False}
allowed={'NON_MARKET_DATABASE.json','ledger.sqlite','ledger.sqlite-journal','ledger.sqlite-wal','ledger.sqlite-shm','write-ready.json'}
for p in ROOT.iterdir():
 assert p.name in allowed and not p.is_symlink()
 try:st=p.lstat()
 except FileNotFoundError:continue
 assert stat.S_ISREG(st.st_mode) and st.st_nlink==1
original=subprocess.run

def invoke(argv,**kwargs):
 assert argv[0]=='/usr/bin/bwrap'
 pivot=argv.index('--remount-ro')
 argv=argv[:pivot]+['--bind',str(ROOT),'/work/shared-db']+argv[pivot:]
 if job!='dbcrash':return original(argv,**kwargs)
 ready=ROOT/'write-ready.json';assert not ready.exists()
 proc=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 begin=time.monotonic()
 while not ready.exists() and proc.poll() is None and time.monotonic()-begin<30:time.sleep(.02)
 assert ready.exists(),'WRITE_BARRIER_NOT_REACHED'
 barrier=json.loads(ready.read_bytes());assert barrier['stage']=='UNCOMMITTED_INSERT'
 proc.kill();stdout,stderr=proc.communicate(timeout=10)
 record={'job':job,'host_bwrap_pid':proc.pid,'guest_barrier':barrier,'native_returncode':proc.returncode,
         'controlled_signal':'SIGKILL','stage':'AFTER_INSERT_BEFORE_COMMIT','elapsed_seconds':time.monotonic()-begin,
         'shared_mount':str(ROOT),'original_mounted':False,'market_data':False}
 (output/'controlled-crash.json').write_text(json.dumps(record,indent=2))
 return subprocess.CompletedProcess(argv,proc.returncode,stdout,stderr)
subprocess.run=invoke
code=launcher.launch(manifest,pin,output,policy)
sys.exit(code)
