import subprocess,json,time
from pathlib import Path
from datetime import UTC,datetime
B=Path(__file__).resolve().parent;S=B/'staged/repo';RT='/home/parilrupani/omega-od02v-37b3vimd/venv312'
paths=['src/omegadata/canonical_storage/'+n+'.py' for n in ('__init__','contracts','schema','admission','store','query')]+['tests/unit/test_od10_canonical_storage.py','scripts/od10_structural_experiments.py','scripts/od10_isolated_jobs.py']
prefix=['/usr/bin/bwrap','--unshare-all','--die-with-parent','--new-session','--cap-drop','ALL','--clearenv','--ro-bind','/usr','/usr','--symlink','usr/lib','/lib','--symlink','usr/lib64','/lib64','--ro-bind',RT,RT,'--proc','/proc','--dev','/dev','--tmpfs','/tmp','--bind',str(S),'/repo','--chdir','/repo',RT+'/bin/ruff']
for args in (['check','--fix','--no-cache',*paths],['format',*paths]):
 start=datetime.now(UTC).isoformat();r=subprocess.run(prefix+args,capture_output=True,text=True,timeout=60)
 with (B/'logs'/('format-'+str(time.time_ns())+'.json')).open('x') as f:json.dump({'argv':prefix+args,'start':start,'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr},f)
 print(r.returncode,r.stdout[-1000:])


