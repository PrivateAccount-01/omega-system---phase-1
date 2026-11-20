"""NON_MARKET_STRUCTURAL_CONTROL and PURE_MATHEMATICAL_TEST; no source observations."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal, localcontext
import pytest
from test_od08_universe import setup_case, observation, query, D, K


def test_required_observation_cannot_be_omitted(tmp_path):
    from omegadata.universe.repository import UniverseRepository
    c,x,m,cov,p,run=setup_case()
    p=replace(p,view='RESEARCH',require_observations=True)
    x=replace(x,observations=(observation(x),))
    db=UniverseRepository('sqlite:///:memory:',disposable_root=tmp_path)
    db.seed_context(x,p)
    with pytest.raises(ValueError,match='OBSERVATION_SET'):
        db.pin_context('omitted',replace(x,observations=()),D,K,p)


def test_intraday_cannot_use_date_only_coverage():
    c,x,m,cov,p,run=setup_case()
    boundary=K+timedelta(hours=2)
    m=replace(m,effective_convention='EXPLICIT_TIMESTAMP',effective_at=boundary)
    x=replace(x,memberships=(m,))
    out=query(x,day=boundary,known=boundary)
    assert out.coverage_state not in {'COMPLETE_VERIFIED','COMPLETE_FOR_DECLARED_NON_MARKET_SCOPE'}


def test_contradictory_effective_date_refused():
    c,x,m,cov,p,run=setup_case()
    with pytest.raises(ValueError,match='EFFECTIVE'):
        replace(m,effective_convention='EXPLICIT_TIMESTAMP',effective_at=K+timedelta(days=3))


def liquid_case():
    from omegadata.session_calendar import CoverageClaim,SessionClaim,VerifiedCalendar
    c,x,m,cov,p,run=setup_case()
    sessions=tuple(SessionClaim('s'+str(i),'CANARY-X',D+timedelta(days=i),'REGULAR','Asia/Kolkata','v',x.definition.evidence,K,None,closes_at=K+timedelta(days=i,hours=1)) for i in range(3))
    coverage=CoverageClaim('c','CANARY-X',D,D+timedelta(days=3),K,None,x.definition.evidence,'v','COMPLETE')
    x=replace(x,calendar=VerifiedCalendar(sessions,(coverage,)))
    p=c.LiquidityPolicy('v',3,1,Decimal(0),Decimal(0),Decimal('0.3'),'CONTROL_UNIT','CONTROL_ONLY','RAW_UNADJUSTED','RAW')
    return c,x,m,p


@pytest.mark.parametrize('count',[1,2,3])
def test_liquidity_nonterminating_ratio(count):
    from omegadata.universe.eligibility import liquidity
    c,x,m,p=liquid_case()
    rows=tuple(observation(x,observation_id='o'+str(i),session_date=D+timedelta(days=i),volume=Decimal(i+1)) for i in range(count))
    results=[]
    for prec in (6,28,60):
        with localcontext() as ctx:
            ctx.prec=prec
            status,diag=liquidity(m,x,rows,D+timedelta(days=2),K+timedelta(days=3),p)
            assert status=='ELIGIBLE'
            results.append(diag)
    assert results[0]==results[1]==results[2]


@pytest.mark.parametrize('kind',['ANNOUNCEMENT','DAILY_CLOSE'])
def test_future_economic_time_is_type_specific(kind):
    from omegadata.universe.temporal import availability
    c,x,m,cov,p,run=setup_case()
    o=observation(x,observation_type=kind,economic_effective_time=K+timedelta(days=1))
    assert availability(o,K,c.AvailabilityPolicy(),x)==('AVAILABLE' if kind=='ANNOUNCEMENT' else 'BLOCKED_AVAILABILITY')


@pytest.mark.parametrize('field',['security','listing','exchange','session','record','volume','basis','future','missing_pin','correct'])
def test_strict_adjustment_binding(field):
    from test_od07_final import setup_bound
    from omegadata.adjustments import bound_contracts as bc
    from omegadata.adjustments.bound_chain import calculate_bound_chain
    from omegadata.adjustments.contracts import digest
    from omegadata.universe.observation_binding import AdjustmentBinding, validate_binding
    from omegadata.universe.contracts import AvailabilityObservation
    parts=setup_bound(basis=bc.BasisPolicy('VOLUME','BACKWARD_ADJUSTED',D+timedelta(days=5)))
    pin=parts[8];result=calculate_bound_chain(pin);raw=pin.raw.raw
    o=AvailabilityObservation('obs','CONTROL_ONLY',raw.listing_id,raw.trade_date,None,raw.known_from,None,raw.known_from,None,None,pin.raw.source_id,raw.artifact_id,raw.evidence,interval_completed_at=raw.known_from,record_identity=pin.raw.source_record_identity,volume=result.calculation.adjusted_volume,currency=raw.currency,price_unit=pin.raw.price_unit,price_basis='RAW_UNADJUSTED',volume_basis='BACKWARD_ADJUSTED',adjustment=result,adjustment_pin=pin)
    binding=AdjustmentBinding('obs',pin.raw.source_record_identity,raw.artifact_id,raw.security_id,raw.listing_id,raw.exchange,raw.trade_date,pin.raw.observation_id,digest(pin.raw),pin.snapshot_id,result.output_digest,'VOLUME',result.adjustment_basis,result.basis_date,raw.currency,pin.raw.price_unit,'SHARES','volume',o.volume,pin.context.known_at)
    if field=='security':binding=replace(binding,security_id='other')
    if field=='listing':o=replace(o,listing_id='other')
    if field=='exchange':binding=replace(binding,exchange='other')
    if field=='session':o=replace(o,session_date=D+timedelta(days=9))
    if field=='record':o=replace(o,record_identity='other')
    if field=='volume':o=replace(o,volume=o.volume+Decimal(1))
    if field=='basis':binding=replace(binding,adjustment_basis='FORWARD_ADJUSTED')
    if field=='future':binding=replace(binding,knowledge_cutoff=pin.context.known_at+timedelta(days=1))
    if field=='missing_pin':o=replace(o,adjustment_pin=None)
    assert validate_binding(o,binding,pin.context.known_at)==('ELIGIBLE_NON_MARKET' if field=='correct' else 'BLOCKED_OBSERVATION_BINDING')
