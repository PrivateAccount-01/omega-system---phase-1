import hashlib,json
from pathlib import Path
from datetime import UTC,datetime
B=Path('/home/parilrupani/omega-od07-final-20261119T175351Z');raw=(B/'staged2/repo/tests/unit/test_od07_final.py').read_bytes()
(B/'scope-negative-source.py').write_bytes(raw)
(B/'scope-freeze.json').write_text(json.dumps({'utc':datetime.now(UTC).isoformat(),'sha256':hashlib.sha256(raw).hexdigest()},indent=2))
