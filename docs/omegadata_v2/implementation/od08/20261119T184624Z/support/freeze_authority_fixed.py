from pathlib import Path
from datetime import datetime,UTC
import hashlib,json
B=Path('/home/parilrupani/omega-od08-20261119T184624Z');p=B/'staged2/repo/tests/unit/test_od08_universe.py';s=p.read_text()
s=s.replace('"persist-adjustment"','"persist-adjustment", "persist-authority-object"',1)
s=s.replace('    pin = setup_bound()[8]\n','    pin = setup_bound()[8]\n    if case == "persist-authority-object":\n        from omegadata.identity_authority import EvidenceAuthority\n        pin=replace(pin,context=replace(pin.context,authority=EvidenceAuthority.unconfigured()))\n')
s=s.replace('    if case == "persist-adjustment":','    if case in {"persist-adjustment", "persist-authority-object"}:')
p.write_text(s);raw=p.read_bytes();(B/'authority-negative-source.py').write_bytes(raw);(B/'authority-freeze.json').write_text(json.dumps({'utc':datetime.now(UTC).isoformat(),'sha256':hashlib.sha256(raw).hexdigest(),'cases':92,'reason':'A legitimate unconfigured typed EvidenceAuthority object must persist without granting rights. Earlier helper parse failure did not execute this addition.'},indent=2))
