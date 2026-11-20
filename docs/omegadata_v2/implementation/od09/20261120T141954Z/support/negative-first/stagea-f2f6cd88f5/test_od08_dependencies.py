"""NON_MARKET_STRUCTURAL_CONTROL and PURE_MATHEMATICAL_TEST; no source observations."""

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal, localcontext

import pytest
from test_od08_universe import D, K, observation, query, setup_case


def test_required_observation_cannot_be_omitted(tmp_path):
    from omegadata.universe.repository import UniverseRepository

    c, x, m, cov, p, run = setup_case()
    p = replace(p, view="RESEARCH", require_observations=True)
    x = replace(x, observations=(observation(x),))
    db = UniverseRepository("sqlite:///:memory:", disposable_root=tmp_path)
    db.seed_context(x, p)
    with pytest.raises(ValueError, match="OBSERVATION_SET"):
        db.pin_context("omitted", replace(x, observations=()), D, K, p)


def test_intraday_cannot_use_date_only_coverage():
    c, x, m, cov, p, run = setup_case()
    boundary = K + timedelta(hours=2)
    m = replace(m, effective_convention="EXPLICIT_TIMESTAMP", effective_at=boundary)
    x = replace(x, memberships=(m,))
    out = query(x, day=boundary, known=boundary)
    assert out.coverage_state not in {"COMPLETE_VERIFIED", "COMPLETE_FOR_DECLARED_NON_MARKET_SCOPE"}


def test_contradictory_effective_date_refused():
    c, x, m, cov, p, run = setup_case()
    with pytest.raises(ValueError, match="EFFECTIVE"):
        replace(m, effective_convention="EXPLICIT_TIMESTAMP", effective_at=K + timedelta(days=3))


def liquid_case():
    from omegadata.session_calendar import CoverageClaim, SessionClaim, VerifiedCalendar

    c, x, m, cov, p, run = setup_case()
    sessions = tuple(
        SessionClaim(
            "s" + str(i),
            "CANARY-X",
            D + timedelta(days=i),
            "REGULAR",
            "Asia/Kolkata",
            "v",
            x.definition.evidence,
            K,
            None,
            closes_at=K + timedelta(days=i, hours=1),
        )
        for i in range(3)
    )
    coverage = CoverageClaim(
        "c", "CANARY-X", D, D + timedelta(days=3), K, None, x.definition.evidence, "v", "COMPLETE"
    )
    x = replace(x, calendar=VerifiedCalendar(sessions, (coverage,)))
    p = c.LiquidityPolicy(
        "v",
        3,
        1,
        Decimal(0),
        Decimal(0),
        Decimal("0.3"),
        "CONTROL_UNIT",
        "CONTROL_ONLY",
        "RAW_UNADJUSTED",
        "RAW",
    )
    return c, x, m, p


@pytest.mark.parametrize("count", [1, 2, 3])
def test_liquidity_nonterminating_ratio(count):
    from omegadata.universe.eligibility import liquidity

    c, x, m, p = liquid_case()
    rows = tuple(
        observation(
            x,
            observation_id="o" + str(i),
            session_date=D + timedelta(days=i),
            volume=Decimal(i + 1),
        )
        for i in range(count)
    )
    results = []
    for prec in (6, 28, 60):
        with localcontext() as ctx:
            ctx.prec = prec
            status, diag = liquidity(m, x, rows, D + timedelta(days=2), K + timedelta(days=3), p)
            assert status == "ELIGIBLE"
            results.append(diag)
    assert results[0] == results[1] == results[2]


@pytest.mark.parametrize("kind", ["ANNOUNCEMENT", "DAILY_CLOSE"])
def test_future_economic_time_is_type_specific(kind):
    from omegadata.universe.temporal import availability

    c, x, m, cov, p, run = setup_case()
    o = observation(x, observation_type=kind, economic_effective_time=K + timedelta(days=1))
    assert availability(o, K, c.AvailabilityPolicy(), x) == (
        "AVAILABLE" if kind == "ANNOUNCEMENT" else "BLOCKED_AVAILABILITY"
    )


@pytest.mark.parametrize(
    "field",
    [
        "security",
        "listing",
        "exchange",
        "session",
        "record",
        "volume",
        "basis",
        "future",
        "missing_pin",
        "correct",
    ],
)
def test_strict_adjustment_binding(field):
    from test_od07_final import setup_bound

    from omegadata.adjustments import bound_contracts as bc
    from omegadata.adjustments.bound_chain import calculate_bound_chain
    from omegadata.adjustments.contracts import digest
    from omegadata.universe.contracts import AvailabilityObservation
    from omegadata.universe.observation_binding import AdjustmentBinding, validate_binding

    parts = setup_bound(basis=bc.BasisPolicy("VOLUME", "BACKWARD_ADJUSTED", D + timedelta(days=5)))
    pin = parts[8]
    result = calculate_bound_chain(pin)
    raw = pin.raw.raw
    o = AvailabilityObservation(
        "obs",
        "CONTROL_ONLY",
        raw.listing_id,
        raw.trade_date,
        None,
        raw.known_from,
        None,
        raw.known_from,
        None,
        None,
        pin.raw.source_id,
        raw.artifact_id,
        raw.evidence,
        interval_completed_at=raw.known_from,
        record_identity=pin.raw.source_record_identity,
        volume=result.calculation.adjusted_volume,
        currency=raw.currency,
        price_unit=pin.raw.price_unit,
        price_basis="RAW_UNADJUSTED",
        volume_basis="BACKWARD_ADJUSTED",
        adjustment=result,
        adjustment_pin=pin,
    )
    binding = AdjustmentBinding(
        "obs",
        pin.raw.source_record_identity,
        raw.artifact_id,
        raw.security_id,
        raw.listing_id,
        raw.exchange,
        raw.trade_date,
        pin.raw.observation_id,
        digest(pin.raw),
        pin.snapshot_id,
        result.output_digest,
        "VOLUME",
        result.adjustment_basis,
        result.basis_date,
        raw.currency,
        pin.raw.price_unit,
        "SHARES",
        "volume",
        o.volume,
        pin.context.known_at,
    )
    if field == "security":
        binding = replace(binding, security_id="other")
    if field == "listing":
        o = replace(o, listing_id="other")
    if field == "exchange":
        binding = replace(binding, exchange="other")
    if field == "session":
        o = replace(o, session_date=D + timedelta(days=9))
    if field == "record":
        o = replace(o, record_identity="other")
    if field == "volume":
        o = replace(o, volume=o.volume + Decimal(1))
    if field == "basis":
        binding = replace(binding, adjustment_basis="FORWARD_ADJUSTED")
    if field == "future":
        binding = replace(binding, knowledge_cutoff=pin.context.known_at + timedelta(days=1))
    if field == "missing_pin":
        o = replace(o, adjustment_pin=None)
    assert validate_binding(o, binding, pin.context.known_at) == (
        "ELIGIBLE_NON_MARKET" if field == "correct" else "BLOCKED_OBSERVATION_BINDING"
    )


@pytest.mark.parametrize("case", ["duplicate", "conflict", "unrelated", "future", "partial"])
def test_observation_set_scope(case, tmp_path):
    from omegadata.universe.repository import UniverseRepository

    c, x, m, cov, p, run = setup_case()
    first = observation(x)
    p = replace(p, view="RESEARCH", require_observations=True)
    extra = replace(first, observation_id="extra", volume=Decimal(2))
    if case == "unrelated":
        extra = replace(extra, listing_id="other")
    if case == "future":
        extra = replace(extra, known_from=K + timedelta(days=1))
    if case == "partial":
        scope = c.ObservationScope(
            x.definition.universe_id,
            ("listing-a",),
            ("CONTROL_ONLY",),
            (D,),
            ("control-source",),
            "RAW_UNADJUSTED",
            "RAW",
            ("extra",),
        )
        p = replace(p, observation_scope=scope)
    x = replace(x, observations=(first, extra))
    db = UniverseRepository("sqlite:///:memory:", disposable_root=tmp_path)
    db.seed_context(x, p)
    supplied = replace(x, observations=(first, first) if case == "duplicate" else (first,))
    if case in {"duplicate", "conflict"}:
        with pytest.raises(ValueError, match="OBSERVATION_SET"):
            db.pin_context("pin", supplied, D, K, p)
    else:
        db.pin_context("pin", supplied, D, K, p)


@pytest.mark.parametrize("offset", [-1, 0, 1])
def test_exact_intraday_coverage(offset):
    c, x, m, cov, p, run = setup_case()
    boundary = K + timedelta(hours=2)
    m = replace(m, effective_convention="EXPLICIT_TIMESTAMP", effective_at=boundary)
    transition = c.CoverageTransition(m.revision_id, "security-a", "ADD", D, effective_at=boundary)
    cov = replace(
        cov,
        expected_member_identities=(),
        transitions=(transition,),
        temporal_precision="TIMESTAMP",
    )
    x = replace(x, memberships=(m,), coverage=(cov,))
    out = query(x, day=boundary + timedelta(seconds=offset), known=boundary)
    assert out.coverage_state == "COMPLETE_FOR_DECLARED_NON_MARKET_SCOPE"
    assert out.member_identities == (() if offset < 0 else ("security-a",))


def test_wrong_intraday_transition_identity():
    c, x, m, cov, p, run = setup_case()
    boundary = K + timedelta(hours=2)
    m = replace(m, effective_convention="EXPLICIT_TIMESTAMP", effective_at=boundary)
    t = c.CoverageTransition(
        m.revision_id, "security-a", "ADD", D, effective_at=boundary - timedelta(seconds=1)
    )
    cov = replace(
        cov, expected_member_identities=(), transitions=(t,), temporal_precision="TIMESTAMP"
    )
    assert (
        query(
            replace(x, memberships=(m,), coverage=(cov,)), day=boundary, known=boundary
        ).coverage_state
        != "COMPLETE_FOR_DECLARED_NON_MARKET_SCOPE"
    )


@pytest.mark.parametrize("value", [Decimal("1E10000"), Decimal("NaN"), Decimal("-1")])
def test_liquidity_malformed_policy_typed(value):
    c, x, m, p = liquid_case()
    with pytest.raises(ValueError):
        replace(p, minimum_observation_coverage=value)


def test_announced_future_event_needs_no_completed_session():
    from omegadata.universe.temporal import availability

    c, x, m, cov, p, run = setup_case()
    o = observation(
        x,
        observation_type="ANNOUNCEMENT",
        economic_effective_time=K + timedelta(days=2),
        interval_completed_at=None,
    )
    assert availability(o, K, c.AvailabilityPolicy(), x) == "AVAILABLE"


def test_liquidity_required_set_ignores_out_of_window(tmp_path):
    from omegadata.universe.repository import UniverseRepository

    c, x, m, lp = liquid_case()
    old = observation(x, observation_id="old", session_date=D - timedelta(days=10))
    o = observation(x)
    p = c.EligibilityPolicy("window", "LIQUIDITY", require_observations=True, liquidity_policy=lp)
    stored = replace(x, observations=(o, old))
    db = UniverseRepository("sqlite:///:memory:", disposable_root=tmp_path)
    db.seed_context(stored, p)
    db.pin_context(
        "window", replace(x, observations=(o,)), D + timedelta(days=2), K + timedelta(days=3), p
    )


@pytest.mark.parametrize('reference_time',['missing','exact','different'])
def test_timestamp_snapshot_requires_exact_reference_instant(reference_time):
    c,x,m,cov,p,run=setup_case();point=K+timedelta(hours=2)
    stamp=None if reference_time=='missing' else point if reference_time=='exact' else point+timedelta(seconds=1)
    m=replace(m,effective_convention='EXPLICIT_TIMESTAMP',effective_at=K)
    cov=replace(cov,granularity='SNAPSHOT',valid_to=D+timedelta(days=1),temporal_precision='TIMESTAMP',snapshot_at=stamp)
    result=query(replace(x,memberships=(m,),coverage=(cov,)),day=point,known=point)
    assert (result.coverage_state=='COMPLETE_FOR_DECLARED_NON_MARKET_SCOPE')==(reference_time=='exact')


def test_date_only_boundary_does_not_invent_intraday_instant():
    c,x,m,cov,p,run=setup_case()
    result=query(x,day=K+timedelta(hours=2),known=K+timedelta(hours=2))
    assert result.coverage_state not in {'COMPLETE_VERIFIED','COMPLETE_FOR_DECLARED_NON_MARKET_SCOPE'}
