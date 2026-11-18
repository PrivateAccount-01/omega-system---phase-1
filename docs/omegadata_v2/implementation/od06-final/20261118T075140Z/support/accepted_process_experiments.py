"""Fail-closed orchestration of exact OS-isolated disposable DB experiments."""
import json,subprocess,sys
from pathlib import Path
from datetime import UTC,datetime
B=Path('/home/parilrupani/omega-od06-final-20261118T075140Z');S=B/'staged2/repo'
sys.path.insert(0,str(S/'scripts'))
from od06_experiment_contract import experiment_stage_accepted
root=B/'shared-canary-database-accepted';root.mkdir(mode=0o700)
(root/'NON_MARKET_DATABASE.json').write_text(json.dumps({'schema_version':'od06.shared-canary/v1','market_data':False,'financial_eligible':False}))
s=(B/'run.py').read_text().replace("str(S/'scripts/od05x_isolated_runner.py')","str(B/'launch_shared_guarded.py')")
(B/'run_shared_guarded.py').write_text(s)
P='/home/parilrupani/omega-od02v-37b3vimd/venv312/bin/python'
records={}

def check(job,completed,before):
    candidates=[p for p in (B/'logs').glob(job+'-*-command.json') if p.name not in before]
    assert completed.returncode==0 and len(candidates)==1,(job,completed.returncode,candidates)
    r=json.loads(candidates[0].read_bytes())
    crash=None
    if job=='dbcrash':
        output=Path(r['argv'][r['argv'].index('--output')+1])
        crash=json.loads((output/'controlled-crash.json').read_bytes())
    assert experiment_stage_accepted(job,r['exit_code'],r['worker_result'],crash),('STAGE_REFUSED',job,r)
    records[job]={'command_log':candidates[0].name,'exit_code':r['exit_code'],'worker_result':r['worker_result'],'crash':crash}
    print(json.dumps({'checked_job':job,'accepted':True,'exit':r['exit_code']}),flush=True)

for job in ['dbinit','dbcrash','dbrecover']:
    before={p.name for p in (B/'logs').glob('*-command.json')}
    result=subprocess.run([P,'-B',str(B/'run_shared_guarded.py'),job],capture_output=True,text=True)
    check(job,result,before)
before={p.name for p in (B/'logs').glob('*-command.json')}
processes={job:subprocess.Popen([P,'-B',str(B/'run_shared_guarded.py'),job],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for job in ['dbcompete-a','dbcompete-b']}
for job,process in processes.items():
    stdout,stderr=process.communicate(timeout=120)
    check(job,subprocess.CompletedProcess(process.args,process.returncode,stdout,stderr),before)
assert sorted(records[j]['worker_result']['status'] for j in processes)==['COMMITTED','REFUSED_COMPETING_SUCCESSOR']
before={p.name for p in (B/'logs').glob('*-command.json')}
result=subprocess.run([P,'-B',str(B/'run_shared_guarded.py'),'dbfinal'],capture_output=True,text=True)
check('dbfinal',result,before)
with (B/'accepted-process-experiments.json').open('x') as f:json.dump({'utc':datetime.now(UTC).isoformat(),'status':'PASS','shared_canary_root':str(root),'records':records,'scope':'Disposable non-market database only; native OS worker restrictions retained'},f,indent=2)
