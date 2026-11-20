from pathlib import Path
from datetime import UTC,datetime
import hashlib,json
B=Path('/home/parilrupani/omega-od08-20261119T184624Z');p=B/'staged2/repo/tests/unit/test_od08_universe.py'
with p.open('a') as f:f.write('''

@pytest.mark.parametrize('case',['source-scope','expected-identities','transitions'])
def test_immutable_source_contracts(case):
    c,x,m,cov,p,run=setup_case()
    with pytest.raises(ValueError):
        if case=='source-scope':replace(x.definition,source_scope=['control-source'])
        elif case=='expected-identities':replace(cov,expected_member_identities=['security-a'])
        else:replace(cov,transitions=[])
''')
raw=p.read_bytes();(B/'immutable-negative-source.py').write_bytes(raw);(B/'immutable-freeze.json').write_text(json.dumps({'utc':datetime.now(UTC).isoformat(),'sha256':hashlib.sha256(raw).hexdigest(),'cases':92,'reason':'Definition/coverage source contracts must reject mutable list inputs'},indent=2))
