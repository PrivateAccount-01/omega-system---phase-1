from pathlib import Path
import hashlib,json
from datetime import UTC,datetime
B=Path('/home/parilrupani/omega-od07-20261119T171019Z');raw=(B/'staged2/repo/tests/unit/test_od07_adjustments.py').read_bytes()
(B/'decimal-negative-test-source.py').write_bytes(raw)
(B/'decimal-freeze.json').write_text(json.dumps({'utc':datetime.now(UTC).isoformat(),'sha256':hashlib.sha256(raw).hexdigest()},indent=2))
