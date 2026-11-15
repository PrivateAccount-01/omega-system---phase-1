import json,sys
from pathlib import Path
import control
for label,meta,key in [('win314','copy.json','root'),('win311','win311-copy.json','root')]:
 root=json.loads((control.LOGS/meta).read_text())[key]
 assert control.command(label+'-all-source-final',[sys.executable,'-B',str(control.HERE/'source_identity.py'),root])==0
root=json.loads((control.LOGS/'linux-copy.json').read_text())['copy']
assert control.command('linux312-all-source-final',['wsl','--exec','/home/parilrupani/omega-od02v-37b3vimd/venv312/bin/python','-B','/mnt/e/omega system - phase 1/docs/omegadata_v2/implementation/od04r/20261115T181120Z/source_identity.py',root])==0
for label,args in [('main-diff',['git','diff','--name-status','main...HEAD']),('final-status',['git','status','--porcelain=v1','-uall']),('diff-check',['git','diff','--check'])]:
 assert control.command(label,args)==0
with (control.LOGS/'application.patch').open('xb') as out:
 import subprocess
 out.write(subprocess.check_output(['git','diff','--','src/omegadata/track_a/raw_archive.py','scripts/verify_raw_archive.py']))
control.save('ci-observed.json',{'sha':control.HEAD,'observation':'Read-only GitHub connector query during OD04R','combined_status':{'statuses':[]},'workflow_runs':[], 'limitation':'workflow wrapper filters pull_request-triggered runs and first page only; no successful feature-SHA CI was observed, not universal absence proof. No CI result covers local uncommitted corrections.'})
