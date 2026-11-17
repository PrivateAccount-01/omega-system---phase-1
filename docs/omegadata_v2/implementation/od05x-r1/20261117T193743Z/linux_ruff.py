"""Trusted static Ruff on a receipt-pinned canonical data-free source copy."""
import hashlib
import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

HERE=Path(__file__).resolve().parent
runtime='/home/parilrupani/omega-od02v-37b3vimd/venv312'
commands=[]
for p in (HERE/'logs').glob('r1-*-command.json'):
    row=json.loads(p.read_bytes())
    if row['exit_code']==0:
        commands.append(row)
latest=max(commands,key=lambda r:r['end_utc'])
receipt=latest['receipts'][0]
raw=Path(receipt['path']).read_bytes()
assert hashlib.sha256(raw).hexdigest()==receipt['sha256']
root=Path(receipt['path']).parent/'repo'
for row in json.loads(raw)['files']:
    p=root/row['path']
    assert not p.is_symlink() and p.lstat().st_nlink==1
    assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
argv=['/usr/bin/bwrap','--unshare-all','--die-with-parent','--new-session','--cap-drop','ALL',
      '--clearenv','--ro-bind','/usr','/usr','--symlink','usr/lib','/lib','--symlink','usr/lib64','/lib64',
      '--ro-bind',runtime,runtime,'--proc','/proc','--dev','/dev','--tmpfs','/tmp',
      '--ro-bind',str(root/'src'),'/repo/src','--ro-bind',str(root/'scripts'),'/repo/scripts',
      '--ro-bind',str(root/'tests'),'/repo/tests','--ro-bind',str(root/'pyproject.toml'),'/repo/pyproject.toml',
      '--chdir','/repo',runtime+'/bin/ruff','check','--no-cache','src/omegadata','scripts','tests']
start,tick=datetime.now(UTC).isoformat(),time.monotonic()
r=subprocess.run(argv,capture_output=True,text=True,timeout=60)
record={'argv':argv,'start_utc':start,'end_utc':datetime.now(UTC).isoformat(),
        'elapsed_seconds':time.monotonic()-tick,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr,
        'source_receipt':receipt,'scope':'STATIC_TOOL_ONLY; filesystem/network namespaces; no child-denial certification'}
tag='linux-static-ruff-'+datetime.now(UTC).strftime('%H%M%S')+'.json'
with (HERE/'logs'/tag).open('x') as f:
    json.dump(record,f,indent=2)
print(json.dumps(record))
