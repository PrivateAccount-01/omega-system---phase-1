"""Fresh process experiments and missing-first independent corpus check."""
import json,sys,uuid
from pathlib import Path
import control
kind=sys.argv[1]
here=control.HERE
if kind=='win':
    prefix=[sys.executable,'-B']
    script=lambda name:str(here/name)
    copy=json.loads((control.LOGS/'copy.json').read_text())['root']
    missing=str(Path(copy).parent/('omega-od04-process-missing-'+uuid.uuid4().hex))
else:
    prefix=['wsl','--exec','/home/parilrupani/omega-od02v-37b3vimd/venv312/bin/python','-B']
    script=lambda name:'/mnt/e/omega system - phase 1/docs/omegadata_v2/implementation/od04r/20261115T181120Z/'+name
    copy=json.loads((control.LOGS/'linux-copy.json').read_text())['copy']
    missing='/home/parilrupani/omega-od04-process-missing-'+uuid.uuid4().hex
# The independent oracle must first reject a nonexistent separately expected corpus.
assert control.command(kind+'-oracle-missing-negative',prefix+[script('independent_oracle.py'),missing])==1
assert control.command(kind+'-process',prefix+[script('process_experiments.py'),copy,kind+'-fresh'])==0
raw=(control.LOGS/(kind+'-process.txt')).read_text()
result=json.loads(raw[raw.index('{\n'):])
control.save(kind+'-process-result.json',result)
assert result['passed'] and result['forced_crashes']==5
assert control.command(kind+'-oracle-positive',prefix+[script('independent_oracle.py'),result['root']])==0
