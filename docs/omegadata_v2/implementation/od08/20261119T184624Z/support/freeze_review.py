from pathlib import Path
from datetime import UTC,datetime
import json,hashlib
B=Path('/home/parilrupani/omega-od08-20261119T184624Z');p=B/'staged2/repo/tests/unit/test_od08_universe.py'
with p.open('a') as f:f.write('''

@pytest.mark.parametrize('case',['context-checksum','replay-restart','omitted-ledger','omitted-coverage','order-observations','complete-transition','listing-granularity','actual-rollback','migration-empty','read-only-backfill','closed-session','same-instant-correction','replay-bool','future-definition','ranking-tie'])
def test_independent_review(case,tmp_path):
    from omegadata.universe.repository import UniverseRepository,M,schema
    from omegadata.universe import temporal as t,eligibility as e,snapshots as s
    from sqlalchemy import text,create_engine
    c,x,m,cov,p,run=setup_case()
    if case=='context-checksum':
        db=UniverseRepository('sqlite:///:memory:',disposable_root=tmp_path);db.seed_context(x,p);db.pin_context('pin',x,D,K,p)
        with db.transaction() as con:
            con.exec_driver_sql('DROP TRIGGER od08_context_update')
            con.exec_driver_sql("UPDATE od08_context SET payload=payload||' '")
        with pytest.raises(ValueError):db.admit_snapshot('pin',query(x))
    elif case=='replay-restart':
        url='sqlite:///'+str(tmp_path/'replay.sqlite');db=UniverseRepository(url,disposable_root=tmp_path);db.seed_context(x,p);db.pin_context('pin',x,D,K,p);db.admit_snapshot('pin',query(x));db.close();db=UniverseRepository(url,disposable_root=tmp_path);assert db.replay_context('pin').snapshot_digest==query(x).snapshot_digest
    elif case in {'omitted-ledger','omitted-coverage'}:
        db=UniverseRepository('sqlite:///:memory:',disposable_root=tmp_path);db.seed_context(x,p)
        with pytest.raises(ValueError):db.pin_context('pin',replace(x,**({'memberships':()} if case=='omitted-ledger' else {'coverage':()})),D,K,p)
    elif case=='order-observations':
        a=observation(x);b=replace(a,observation_id='other',session_date=D-timedelta(days=1));policy=replace(p,view='RESEARCH');assert query(replace(x,observations=(a,b)),policy=policy).snapshot_digest==query(replace(x,observations=(b,a)),policy=policy).snapshot_digest
    elif case=='complete-transition':
        end=D+timedelta(days=2);member=replace(m,claim=replace(m.claim,valid_to=end));coverage=replace(cov,transitions=(c.CoverageTransition('m-a','security-a','REMOVE',end),),ending_member_identities=())
        y=replace(x,memberships=(member,),coverage=(coverage,));assert query(y).coverage_state=='COMPLETE_FOR_DECLARED_NON_MARKET_SCOPE';assert query(y,day=end).member_identities==() and query(y,day=end).coverage_state=='COMPLETE_FOR_DECLARED_NON_MARKET_SCOPE'
    elif case=='listing-granularity':
        from omegadata.identity import Listing
        old=x.identity.claims[0];otherlisting=Listing('listing-b','security-a','CANARY-X');otherclaim=replace(old,claim_id='claim-b',listing_id='listing-b',series='OTHER');identity=replace(x.identity,listings=(*x.identity.listings,otherlisting),claims=(*x.identity.claims,otherclaim));other=replace(m,claim=replace(m.claim,membership_id='m-b',series='OTHER'),event_id='event-b',listing_id='listing-b');coverage=replace(cov,expected_member_identities=('listing-a','listing-b'),ending_member_identities=('listing-a','listing-b'));y=replace(x,definition=replace(x.definition,identity_granularity='LISTING'),identity=identity,memberships=(m,other),coverage=(coverage,));assert query(y).included_member_ids==('listing-a','listing-b')
    elif case=='actual-rollback':
        db=UniverseRepository('sqlite:///:memory:',disposable_root=tmp_path);db.seed_context(x,p)
        with pytest.raises(RuntimeError),db.transaction() as con:
            db._put(con,__import__('omegadata.universe.repository',fromlist=['policies']).policies,'new-policy',replace(p,policy_version='new-policy'));raise RuntimeError('CONTROLLED_INTERRUPT')
        with db.engine.connect() as con:assert con.scalar(text("SELECT count(*) FROM od08_policy WHERE id='new-policy'"))==0
    elif case=='migration-empty':
        db=UniverseRepository('sqlite:///:memory:',disposable_root=tmp_path);db.rollback_empty();db.close()
    elif case=='read-only-backfill':
        from omegadata.universe.compatibility import source_dependent_backfill
        with pytest.raises(PermissionError):source_dependent_backfill()
    elif case=='closed-session':
        from omegadata.session_calendar import SessionClaim
        session=SessionClaim('closed','CANARY-X',D,'CLOSED','Asia/Kolkata','calendar',x.definition.evidence,K,None)
        y=replace(x,calendar=replace(x.calendar,claims=(session,)));out=query(y,policy=replace(p,view='EXECUTION'));assert out.member_identities==('security-a',) and out.decisions[0].status=='BLOCKED_TRADABILITY'
    elif case=='same-instant-correction':
        child=replace(m,claim=replace(m.claim,membership_id='bad',supersedes_membership_id='m-a'),revision_number=2)
        with pytest.raises(ValueError):query(replace(x,memberships=(m,child)))
    elif case=='replay-bool':
        with pytest.raises(ValueError):s.replay_universe_decisions(x,((D,K),),p,max_steps=True)
    elif case=='future-definition':
        with pytest.raises(ValueError):query(replace(x,definition=replace(x.definition,known_from=K+timedelta(seconds=1))))
    elif case=='ranking-tie':
        first=c.RankingCandidate('security-a',Decimal(10),observation(x));out=e.reconstruct((first,),1,K,x);assert out[1]==('security-a',) and out[0]=='RECONSTRUCTED_PROVISIONAL'

@pytest.mark.parametrize('case',['valid-adjustment','wrong-profile','future-context','persist-adjustment'])
def test_od07_bound_integration(case,tmp_path):
    from test_od07_final import setup_bound
    from omegadata.adjustments.bound_chain import calculate_bound_chain
    from omegadata.universe.repository import UniverseRepository
    from omegadata.universe import contracts as c
    from omegadata.identity_adapters import MembershipClaim
    pin=setup_bound()[8];raw=pin.raw.raw;result=calculate_bound_chain(pin);e=raw.evidence;known=pin.context.known_at;day=pin.context.valid_at
    claim=MembershipClaim('m-bound','BOUND_CONTROL',raw.symbol,raw.series,raw.exchange,raw.trade_date,None,raw.known_from,None,e)
    member=c.MembershipRevision(claim,'event','math-source','artifact','record',raw.security_id,raw.listing_id)
    definition=c.UniverseDefinition('BOUND_CONTROL','Anonymous bound contract','CUSTOM_POLICY_UNIVERSE','SECURITY','method',('math-source',),(raw.exchange,),raw.trade_date,None,raw.known_from,None,e)
    coverage=c.UniverseCoverage('cov','BOUND_CONTROL','math-source','ref','method',raw.trade_date,day+timedelta(days=1),raw.known_from,None,'COMPLETE_FOR_DECLARED_NON_MARKET_SCOPE',(raw.security_id,),e,'independent-control',granularity='COMPLETE_CHANGE_HISTORY',ending_member_identities=(raw.security_id,),ending_reference='end')
    obs=c.AvailabilityObservation('bound-observation','CONTROL_ONLY',raw.listing_id,raw.trade_date,None,raw.known_from,None,raw.known_from,None,None,'math-source','raw-artifact',e,interval_completed_at=raw.known_from,record_identity='record',adjustment=result,adjustment_pin=pin)
    x=c.UniverseContext('source-pin',definition,(member,),(coverage,),pin.context.identity_repository,pin.context.calendar,(obs,),mode='CANARY_ONLY')
    policy=c.EligibilityPolicy('bound-policy','RESEARCH',require_observations=True,require_adjustment=True)
    if case=='wrong-profile':policy=replace(policy,required_profile='TOTAL_RETURN')
    if case=='future-context':known-=timedelta(days=1)
    from omegadata.universe.snapshots import get_universe_as_of
    out=get_universe_as_of(x,day,known,policy,'source-pin')
    assert out.decisions[0].status==('BLOCKED_AVAILABILITY' if case in {'wrong-profile','future-context'} else 'INCLUDED')
    assert not out.financial_accepted
    if case=='persist-adjustment':
        db=UniverseRepository('sqlite:///:memory:',disposable_root=tmp_path);db.seed_context(x,policy);db.pin_context('bound-pin',x,day,known,policy);db.admit_snapshot('bound-pin',out);assert db.replay_context('bound-pin').snapshot_digest==out.snapshot_digest
''')
s=p.read_bytes();(B/'review-negative-source.py').write_bytes(s);(B/'review-freeze.json').write_text(json.dumps({'utc':datetime.now(UTC).isoformat(),'sha256':hashlib.sha256(s).hexdigest(),'cases':82,'reason':'Executable review of context storage, exact bindings, bounded replay and real OD07 typed integration using anonymous math controls'},indent=2))
