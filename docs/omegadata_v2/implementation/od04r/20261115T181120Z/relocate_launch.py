import json,sys
import control
kind=sys.argv[1]
root=json.loads((control.LOGS/(kind+'-process-result.json')).read_text())['root']
if kind=='win':
 prefix=[sys.executable,'-B'];script=lambda name:str(control.HERE/name)
else:
 prefix=['wsl','--exec','/home/parilrupani/omega-od02v-37b3vimd/venv312/bin/python','-B']
 script=lambda name:'/mnt/e/omega system - phase 1/docs/omegadata_v2/implementation/od04r/20261115T181120Z/'+name
assert control.command(kind+'-relocate',prefix+[script('relocate_disposable.py'),root])==0
raw=(control.LOGS/(kind+'-relocate.txt')).read_text()
meta=json.loads(raw[raw.index('{'):])
assert control.command(kind+'-oracle-moved-negative',prefix+[script('independent_oracle.py'),root])==1
assert control.command(kind+'-oracle-moved-positive',prefix+[script('independent_oracle.py'),meta['moved']])==0
