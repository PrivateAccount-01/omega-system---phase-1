import hashlib,json
from pathlib import Path
from datetime import UTC,datetime
B=Path('/home/parilrupani/omega-od07-20261119T171019Z');p=B/'staged2/repo/tests/unit/test_od07_adjustments.py'
raw=p.read_bytes();(B/'review-negative-test-source.py').write_bytes(raw)
(B/'review-freeze.json').write_text(json.dumps({'utc':datetime.now(UTC).isoformat(),'sha256':hashlib.sha256(raw).hexdigest(),'before_corrections':True},indent=2))
