from pathlib import Path
import hashlib,json
from datetime import UTC,datetime
B=Path('/home/parilrupani/omega-od06-final-20261118T075140Z');p=B/'staged2/repo/tests/unit/test_od06_foundation.py'
(B/'trust-root-freeze.json').write_text(json.dumps({'utc':datetime.now(UTC).isoformat(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'new_cases':1,'stage':'Before configured owner-reviewed authority root enforcement; mocked rights isolates authenticity, no actual permission'},indent=2))
