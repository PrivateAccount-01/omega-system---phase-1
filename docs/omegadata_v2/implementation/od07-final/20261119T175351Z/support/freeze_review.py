from pathlib import Path
import hashlib,json
from datetime import UTC,datetime
B=Path('/home/parilrupani/omega-od07-final-20261119T175351Z');p=B/'staged2/repo/tests/unit/test_od07_final.py';raw=p.read_bytes()
(B/'review-negative-source.py').write_bytes(raw)
(B/'review-freeze.json').write_text(json.dumps({'utc':datetime.now(UTC).isoformat(),'sha256':hashlib.sha256(raw).hexdigest(),'note':'10 added probes before correction; existing D04 fixture action tag needs correction from SPLIT to BONUS, numerical expectation40 retained'},indent=2))
