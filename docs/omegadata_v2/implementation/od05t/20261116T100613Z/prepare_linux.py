"""Copy the authorized disposable code/metadata corpus to native Linux storage."""
import json
import shutil
import sys
import tempfile
from pathlib import Path

target=Path(tempfile.mkdtemp(prefix='omega-od05t-',dir='/home/parilrupani'))/'repo'
shutil.copytree(sys.argv[1],target)
here=Path(__file__).resolve().parent
with (here/'logs/linux-copy.json').open('x',encoding='utf-8') as f:
    json.dump({'root':str(target),'python':sys.executable,'version':sys.version},f,indent=2)
print(target)
