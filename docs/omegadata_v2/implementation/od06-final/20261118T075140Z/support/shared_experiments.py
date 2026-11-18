from pathlib import Path
import json,subprocess,sys
B=Path('/home/parilrupani/omega-od06-final-20261118T075140Z')
root=B/'shared-canary-database';root.mkdir(mode=0o700)
(root/'NON_MARKET_DATABASE.json').write_text(json.dumps({'schema_version':'od06.shared-canary/v1','market_data':False,'financial_eligible':False}))
s=(B/'run.py').read_text().replace("str(S/'scripts/od05x_isolated_runner.py')","str(B/'launch_shared.py')")
(B/'run_shared.py').write_text(s)
P='/home/parilrupani/omega-od02v-37b3vimd/venv312/bin/python'
for job in ['dbinit','dbcrash','dbrecover']:
 r=subprocess.run([P,'-B',str(B/'run_shared.py'),job],capture_output=True,text=True)
 print(r.stdout,r.stderr,flush=True)
 assert r.returncode==0
processes=[subprocess.Popen([P,'-B',str(B/'run_shared.py'),job],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for job in ['dbcompete-a','dbcompete-b']]
for p in processes:
 stdout,stderr=p.communicate(timeout=120);print(stdout,stderr,flush=True);assert p.returncode==0
r=subprocess.run([P,'-B',str(B/'run_shared.py'),'dbfinal'],capture_output=True,text=True)
print(r.stdout,r.stderr,flush=True);assert r.returncode==0
