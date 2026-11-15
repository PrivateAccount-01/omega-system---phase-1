"""Prove missing evidence refuses; then independently count persistent corpus."""
import json
import control

oldraw=(control.LOGS/'linux-process-accepted.txt').read_text()
old=json.loads(oldraw[oldraw.index('{\n'):])
newraw=(control.LOGS/'linux-process-persistent.txt').read_text()
new=json.loads(newraw[newraw.index('{\n'):])
assert new['passed']
prefix=['wsl','--exec','/home/parilrupani/omega-od02v-37b3vimd/venv312/bin/python','-B',
    '/mnt/e/omega system - phase 1/docs/omegadata_v2/implementation/od04/20261115T124835Z/measure_corpus.py']
assert control.command('linux-missing-corpus-negative',prefix+[old['root']])!=0
assert control.command('linux-corpus-persistent',prefix+[new['root']])==0
