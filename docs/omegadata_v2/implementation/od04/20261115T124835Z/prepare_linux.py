"""Copy only already sanitized OD04 tree; reuse existing Linux environment."""
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

source=Path(sys.argv[1]);target=Path(tempfile.mkdtemp(prefix='omega-od04-',dir='/home/parilrupani'))/'repo'
shutil.copytree(source,target)
assert not (target/'.env').exists() and not (target/'artifacts').exists()
print(json.dumps({'copy':str(target),'python':sys.executable,'version':sys.version,
    'files':{p.relative_to(target).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
             for p in target.rglob('*') if p.is_file() and '__pycache__' not in p.parts}},indent=2))
