import json,subprocess,time
from pathlib import Path
from datetime import UTC,datetime
B=Path('/home/parilrupani/omega-od07-final-20261119T175351Z');S=B/'staged2/repo';R='/home/parilrupani/omega-od02v-37b3vimd/venv312'
argv=['/usr/bin/bwrap','--unshare-all','--die-with-parent','--new-session','--cap-drop','ALL','--clearenv','--ro-bind','/usr','/usr','--symlink','usr/lib','/lib','--symlink','usr/lib64','/lib64','--ro-bind',R,R,'--proc','/proc','--dev','/dev','--tmpfs','/tmp','--ro-bind',str(S/'src'),'/repo/src','--ro-bind',str(S/'scripts'),'/repo/scripts','--ro-bind',str(S/'tests'),'/repo/tests','--ro-bind',str(S/'pyproject.toml'),'/repo/pyproject.toml','--chdir','/repo',R+'/bin/ruff','check','--no-cache','src/omegadata','scripts','tests']
start=datetime.now(UTC).isoformat();tick=time.monotonic();r=subprocess.run(argv,capture_output=True,text=True,timeout=60)
p=B/'logs'/('static-ruff-'+datetime.now(UTC).strftime('%H%M%S')+'.json');p.write_text(json.dumps(dict(argv=argv,start_utc=start,end_utc=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-tick,exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr,scope='STATIC_ONLY read-only data-free source mounts, no original mount; does not certify child execution policy'),indent=2));print(r.returncode,r.stdout[-3000:])
