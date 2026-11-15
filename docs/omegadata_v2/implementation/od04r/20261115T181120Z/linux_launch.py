"""Fresh offline Linux copy and exact launcher logs; no provider calls."""
import json
from pathlib import Path
import control
here=control.HERE
copy=Path(json.loads((control.LOGS/'copy.json').read_text())['root'])
def linux(path):
    p=str(path).replace('\\','/')
    return '/mnt/'+p[0].lower()+p[2:]
py='/home/parilrupani/omega-od02v-37b3vimd/venv312/bin/python'
assert control.command('linux-prepare',['wsl','--exec',py,'-B',linux(here/'prepare_linux.py'),linux(copy)])==0
raw=(control.LOGS/'linux-prepare.txt').read_text()
meta=json.loads(raw[raw.index('{\n'):])
control.save('linux-copy.json',meta)
raise SystemExit(control.command('linux-matrix-launch',['wsl','--exec',py,'-B',linux(here/'matrix.py'),'linux312-final',meta['copy']]))
