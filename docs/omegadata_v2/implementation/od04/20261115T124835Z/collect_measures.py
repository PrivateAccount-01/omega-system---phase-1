import json
import sys
from pathlib import Path
import control

here=Path(__file__).resolve().parent
for mode in ['win','linux']:
    raw=(here/'logs'/(mode+'-process-accepted.txt')).read_text()
    info=json.loads(raw[raw.index('{\n'):])
    assert info['passed']
    if mode=='win':
        command=[sys.executable,'-B',str(here/'measure_corpus.py'),info['root']]
    else:
        command=['wsl','--exec','/home/parilrupani/omega-od02v-37b3vimd/venv312/bin/python','-B',
            '/mnt/e/omega system - phase 1/docs/omegadata_v2/implementation/od04/20261115T124835Z/measure_corpus.py',info['root']]
    assert control.command(mode+'-corpus-reference',command)==0
