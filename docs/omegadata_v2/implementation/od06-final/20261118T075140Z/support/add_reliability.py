from pathlib import Path
S=Path('/home/parilrupani/omega-od06-final-20261118T075140Z/staged2/repo')
p=S/'src/omegadata/identity_adapters.py';v=p.read_text()
start=v.index('    by_id={c.membership_id:c for c in claims}')
end=v.index('    selected = tuple(sorted(',start)
block=v[start:end]
# Standalone lineage validation never needs an invented historical query timestamp.
function='def membership_revision_ends(claims: tuple[MembershipClaim,...]) -> dict[str,datetime]:\n'
function+='    if len({c.membership_id for c in claims})!=len(claims):raise ValueError("DUPLICATE_MEMBERSHIP")\n'
function+=block+'    return ends\n\n\n'
v=v[:start]+'    ends=membership_revision_ends(claims)\n'+v[end:]
v=v.replace('def strict_universe(',function+'def strict_universe(')
p.write_text(v)
p=S/'src/omegadata/identity_repository.py';v=p.read_text().replace('MembershipClaim, StrictUniverse, strict_universe','MembershipClaim, StrictUniverse, membership_revision_ends, strict_universe')
start=v.index('                strict_universe((*old,value)')
end=v.index('            self._evidence(conn,value.evidence)',start)
v=v[:start]+'                membership_revision_ends((*old,value))\n'+v[end:]
p.write_text(v)
p=S/'scripts/od06_database_experiments.py'
p.write_text('''"""Anonymous disposable SQLite process experiments, never a financial fixture."""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from omegadata.identity import Evidence, IdentifierClaim, Issuer, Listing, Security
from omegadata.identity_repository import PersistentRepository


def shared_contract() -> dict[str, Any]:
    return {'schema_version':'od06.shared-canary/v1','market_data':False,'financial_eligible':False}


def run(config: dict[str, Any]) -> int:
    import od05x_isolated_runner as boundary
    capability=boundary.assert_boundary()
    root=Path('/work/shared-db')
    assert json.loads((root/'NON_MARKET_DATABASE.json').read_bytes())==shared_contract()
    out=Path('/work/job');out.mkdir()
    db=PersistentRepository('sqlite+pysqlite:////work/shared-db/ledger.sqlite',disposable_root=root)
    e=Evidence('canary-e','NON_MARKET_CANARY','UNVERIFIED','PERMITTED','canary-review')
    c=IdentifierClaim('claim-a','listing-a','CANARY-X','TOKEN','SERIES',date(2001,1,1),None,
        datetime(2001,1,1,tzinfo=UTC),None,e)
    job=config['job'];status='PASS'
    if job=='dbinit':
        db.append_entities((Issuer('issuer-a'),),(Security('security-a','issuer-a'),),
                           (Listing('listing-a','security-a','CANARY-X'),))
        db.append_identity_claim(c)
    elif job=='dbcrash':
        import omegadata.identity_repository as module
        original=db._put
        def pause(conn: Any,table: Any,key: str,value: Any,extra: Any,idempotent: bool=False) -> bool:
            result=original(conn,table,key,value,extra,idempotent)
            if table is module.claims:
                (root/'write-ready.json').write_text(json.dumps({'stage':'UNCOMMITTED_INSERT','pid':os.getpid()}))
                while True:time.sleep(0.02)
            return result
        db._put=pause  # type: ignore[method-assign]
        db.append_identity_correction(replace(c,claim_id='uncommitted',known_from=c.known_from+timedelta(days=1),supersedes_claim_id='claim-a'))
    elif job=='dbrecover':
        assert db.get_claim_revisions('claim-a')==(c,)
        assert db.serialize_history().find('uncommitted')==-1
        assert db.resolve_listing('CANARY-X','TOKEN','SERIES',c.valid_from,c.known_from,'CANARY_ONLY').state=='RESOLVED'
    elif job in {'dbcompete-a','dbcompete-b'}:
        correction=replace(c,claim_id=job,known_from=c.known_from+timedelta(days=1),supersedes_claim_id='claim-a')
        try:db.append_identity_correction(correction);status='COMMITTED'
        except ValueError:status='REFUSED_COMPETING_SUCCESSOR'
    elif job=='dbfinal':
        family=db.get_claim_revisions('claim-a')
        assert len(family)==2 and family[1].claim_id in {'dbcompete-a','dbcompete-b'}
        assert not db.validate_identity_consistency()
    else:raise ValueError('UNREVIEWED_DATABASE_EXPERIMENT')
    db.close()
    result={'job':job,'exit_code':0,'counts':{},'status':status,'python':sys.version,
            'boundary':capability,'stdout_stderr':'NON_MARKET_CANARY_SQLITE_ONLY','pid':os.getpid()}
    (out/'result.json').write_text(json.dumps(result,indent=2))
    return 0
''')
B=S.parent.parent
p=B/'run.py';v=p.read_text().replace("'tests/unit/test_od06_foundation.py']","'tests/unit/test_od06_foundation.py','scripts/od06_database_experiments.py']");p.write_text(v)
p=B/'final_worker.py';v=p.read_text();v=v.replace("    job = config['job']", "    job = config['job']\n    if job.startswith('db'):\n        import od06_database_experiments\n        return od06_database_experiments.run(config)");p.write_text(v)
