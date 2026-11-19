import hashlib,json
from pathlib import Path
from datetime import UTC,datetime
B=Path('/home/parilrupani/omega-od07-final-20261119T175351Z');p=B/'staged2/repo/tests/unit/test_od07_final.py';raw=p.read_bytes()
(B/'negative-first-source.py').write_bytes(raw)
(B/'negative-first-freeze.json').write_text(json.dumps({'utc':datetime.now(UTC).isoformat(),'sha256':hashlib.sha256(raw).hexdigest(),'application_corrections_started':False,'families':28},indent=2))
