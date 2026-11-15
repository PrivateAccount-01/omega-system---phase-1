import json,shutil,tempfile,subprocess,sys
from pathlib import Path
import control
source=Path(json.loads((control.LOGS/'copy.json').read_text())['root'])
target=Path(tempfile.mkdtemp(prefix='omega-od04r-win311-'))/'repo'
shutil.copytree(source,target)
control.save('win311-copy.json',{'root':str(target)})
py='C:/Users/Paril Rupani/AppData/Local/Temp/vscode-agent-codex-sandbox-DeDZJD/omega-od02v-copy-78jr_vg3/venv311/Scripts/python.exe'
raise SystemExit(control.command('win311-matrix-launch',[py,'-B',str(control.HERE/'matrix.py'),'win311-final',str(target)]))
