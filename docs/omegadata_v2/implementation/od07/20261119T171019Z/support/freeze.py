import hashlib,json
from pathlib import Path
from datetime import UTC,datetime
B=Path('/home/parilrupani/omega-od07-20261119T171019Z');p=B/'staged2/repo/tests/unit/test_od07_adjustments.py'
raw=p.read_bytes();(B/'negative-first-test-source.py').write_bytes(raw)
(B/'negative-first-freeze.json').write_text(json.dumps({'utc':datetime.now(UTC).isoformat(),'path':str(p),'sha256':hashlib.sha256(raw).hexdigest(),'application_implementation_present':(B/'staged2/repo/src/omegadata/adjustments').exists(),'class':'NON_MARKET_MATH_AND_ENGINEERING'},indent=2))
