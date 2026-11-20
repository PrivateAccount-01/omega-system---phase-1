from pathlib import Path
from datetime import datetime,UTC
import hashlib,json
B=Path('/home/parilrupani/omega-od08-20261119T184624Z');p=B/'staged2/repo/tests/unit/test_od08_universe.py'
with p.open('a') as f:f.write('''

@pytest.mark.parametrize('case',['future-announcement','future-publication','intraday-before','intraday-at'])
def test_source_time_boundaries(case):
    from omegadata.universe.temporal import get_known_upcoming_changes
    c,x,m,cov,p,run=setup_case()
    if case.startswith('future'):
        values={'announcement_at':K+timedelta(seconds=1)} if case=='future-announcement' else {'published_at':K+timedelta(seconds=1)}
        changed=replace(m,claim=replace(m.claim,valid_from=D+timedelta(days=1)),**values)
        out=get_known_upcoming_changes(replace(x,memberships=(changed,)),D,K)
        assert out[0][1]=='BLOCKED_AVAILABILITY'
    else:
        effective=K+timedelta(hours=1)
        changed=replace(m,effective_at=effective,effective_convention='EXPLICIT_TIMESTAMP')
        instant=effective-timedelta(seconds=1) if case=='intraday-before' else effective
        out=run(replace(x,memberships=(changed,)),instant,K+timedelta(hours=2),p,'source-pin')
        assert out.selected_revision_ids==(() if case=='intraday-before' else ('m-a',))
''')
s=p.read_bytes();(B/'time-negative-source.py').write_bytes(s);(B/'time-freeze.json').write_text(json.dumps({'utc':datetime.now(UTC).isoformat(),'sha256':hashlib.sha256(s).hexdigest(),'cases':86,'reason':'Future publication/announcement and explicit timestamp business-valid boundaries'},indent=2))
