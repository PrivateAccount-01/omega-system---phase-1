from pathlib import Path
from datetime import datetime,UTC
import hashlib,json
B=Path('/home/parilrupani/omega-od08-20261119T184624Z');p=B/'staged2/repo/tests/unit/test_od08_universe.py'
with p.open('a') as f:f.write('''

def test_identity_selection_candidate_budget(monkeypatch):
    from omegadata.identity import Security,Listing,MemoryIdentityRepository
    c,x,m,cov,p,run=setup_case()
    securities=(Security('s0','issuer-a'),Security('s1','issuer-a'),Security('s2','issuer-a'))
    listings=tuple(Listing('l'+str(i),s.security_id,'CANARY-X') for i,s in enumerate(securities))
    claims=tuple(replace(x.identity.claims[0],claim_id='i'+str(i),listing_id=l.listing_id,symbol='T'+str(i)) for i,l in enumerate(listings))
    identity=replace(x.identity,securities=securities,listings=listings,claims=claims)
    members=tuple(replace(m,claim=replace(m.claim,membership_id='m'+str(i),symbol='T'+str(i)),event_id='event'+str(i),security_id=s.security_id,listing_id=listings[i].listing_id) for i,s in enumerate(securities))
    y=replace(x,identity=identity,memberships=members,coverage=(replace(cov,expected_member_identities=('s0','s1','s2'),ending_member_identities=('s0','s1','s2')),))
    examined=[];original=MemoryIdentityRepository.resolve_listing
    def trace(repository,*args,**kwargs):
        examined.append(len(repository.claims));return original(repository,*args,**kwargs)
    monkeypatch.setattr(MemoryIdentityRepository,'resolve_listing',trace)
    assert query(y).included_member_ids==('s0','s1','s2')
    assert sum(examined)<=4*len(members)
''')
s=p.read_bytes();(B/'index-negative-source.py').write_bytes(s);(B/'index-freeze.json').write_text(json.dumps({'utc':datetime.now(UTC).isoformat(),'sha256':hashlib.sha256(s).hexdigest(),'cases':87,'reason':'Bound repeated identity candidate examination after measured full-ledger query work'},indent=2))
