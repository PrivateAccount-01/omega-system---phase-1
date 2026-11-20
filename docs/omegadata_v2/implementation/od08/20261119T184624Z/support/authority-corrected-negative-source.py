"""NON_MARKET_STRUCTURAL_CONTROL only; no actual index, security or observations."""

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from test_od06_contracts import D, K, system

GROUPS = [
    f"{p}{i:02}"
    for p, n in [
        ("U", 10),
        ("I", 6),
        ("C", 5),
        ("A", 5),
        ("L", 5),
        ("E", 4),
        ("R", 2),
        ("P", 6),
        ("S", 4),
    ]
    for i in range(1, n + 1)
]


def setup_case(**kw):
    from omegadata.identity_adapters import MembershipClaim
    from omegadata.session_calendar import VerifiedCalendar
    from omegadata.universe import contracts as c
    from omegadata.universe.snapshots import get_universe_as_of

    m, e, identity, claim = system()
    legacy = MembershipClaim(
        "m-a", "CONTROL_SCOPE", "TOKEN", "SERIES", "CANARY-X", D, None, K, None, e
    )
    member = c.MembershipRevision(
        legacy,
        "event-a",
        "control-source",
        "artifact-a",
        "record-a",
        security_id="security-a",
        listing_id="listing-a",
    )
    definition = c.UniverseDefinition(
        "CONTROL_SCOPE",
        "Anonymous bookkeeping scope",
        "CUSTOM_POLICY_UNIVERSE",
        "SECURITY",
        "method-v1",
        ("control-source",),
        ("CANARY-X",),
        D,
        None,
        K,
        None,
        e,
    )
    coverage = c.UniverseCoverage(
        "coverage-a",
        "CONTROL_SCOPE",
        "control-source",
        "coverage-artifact",
        "method-v1",
        D,
        D + timedelta(days=20),
        K,
        None,
        "COMPLETE_FOR_DECLARED_NON_MARKET_SCOPE",
        ("security-a",),
        e,
        "reference-a",
        granularity="COMPLETE_CHANGE_HISTORY",
        ending_member_identities=("security-a",),
        ending_reference="end-reference",
    )
    policy = c.EligibilityPolicy("membership-v1", "MEMBERSHIP")
    context = c.UniverseContext(
        "source-pin",
        definition,
        (member,),
        (coverage,),
        identity,
        VerifiedCalendar(),
        mode="CANARY_ONLY",
    )
    context = replace(context, **kw)
    return c, context, member, coverage, policy, get_universe_as_of


def query(ctx=None, day=D, known=K, policy=None):
    c, x, m, coverage, p, run = setup_case()
    return run(ctx or x, day, known, policy or p, "source-pin")


def observation(x, **kw):
    from omegadata.universe.contracts import AvailabilityObservation

    e = x.definition.evidence
    o = AvailabilityObservation(
        "observation-a",
        "CONTROL_ONLY",
        "listing-a",
        D,
        K,
        K,
        K,
        K,
        None,
        K,
        "control-source",
        "observation-artifact",
        e,
        interval_completed_at=K,
        volume=Decimal(0),
        turnover=Decimal(0),
        currency="CONTROL_UNIT",
        price_unit="CONTROL_ONLY",
        price_basis="RAW_UNADJUSTED",
        volume_basis="RAW",
        record_identity="record",
    )
    return replace(o, **kw)


@pytest.mark.parametrize("group", GROUPS)
def test_acceptance(group, tmp_path):
    c, x, m, coverage, p, run = setup_case()
    from omegadata.universe import eligibility as e
    from omegadata.universe import temporal as t
    from omegadata.universe.repository import UniverseRepository

    if group == "U01":
        out = query(x)
        assert (
            out.selected_revision_ids == ("m-a",)
            and out.included_member_ids == ("security-a",)
            and out.accounted_count == 1
        )
    elif group == "U02":
        bad = replace(coverage, expected_member_identities=("different-security",))
        out = query(replace(x, coverage=(bad,)))
        assert (
            out.coverage_state == "CONFLICTING"
            and out.decisions[0].status == "BLOCKED_REFERENCE_COVERAGE"
        )
    elif group == "U03":
        changed = replace(m, claim=replace(m.claim, valid_from=D + timedelta(days=1)))
        assert query(replace(x, memberships=(changed,))).selected_revision_ids == ()
        assert query(
            replace(x, memberships=(changed,)), day=D + timedelta(days=1)
        ).selected_revision_ids == ("m-a",)
    elif group == "U04":
        changed = replace(m, claim=replace(m.claim, valid_to=D + timedelta(days=1)))
        assert (
            query(
                replace(x, memberships=(changed,)), day=D + timedelta(days=1)
            ).selected_revision_ids
            == ()
        )
    elif group == "U05":
        future = replace(m, claim=replace(m.claim, valid_from=D + timedelta(days=2)))
        y = replace(x, memberships=(future,))
        assert query(y).selected_revision_ids == ()
        assert t.get_known_upcoming_changes(y, D, K)[0][1] == "KNOWN_AND_NOT_YET_EFFECTIVE"
    elif group == "U06":
        changed = replace(m, claim=replace(m.claim, known_from=None))
        assert (
            query(replace(x, memberships=(changed,))).decisions[0].status == "BLOCKED_AVAILABILITY"
        )
    elif group in {"U07", "U08", "U09", "U10"}:
        correction = replace(
            m,
            claim=replace(
                m.claim,
                membership_id="m-b",
                known_from=K + timedelta(days=1),
                valid_from=D + timedelta(days=2),
                supersedes_membership_id="m-a",
            ),
            revision_number=2,
            event_type="CANCEL" if group == "U09" else "CORRECTION",
        )
        y = replace(x, memberships=(m, correction))
        if group == "U07":
            assert query(y).snapshot_digest == query(x).snapshot_digest
        elif group == "U08":
            assert query(y, known=K + timedelta(days=1)).selected_revision_ids == ()
        elif group == "U09":
            assert (
                query(y, day=D + timedelta(days=3), known=K + timedelta(days=3)).included_member_ids
                == ()
            )
        else:
            with pytest.raises(ValueError):
                query(
                    replace(
                        y,
                        memberships=(
                            m,
                            correction,
                            replace(
                                correction, claim=replace(correction.claim, membership_id="m-c")
                            ),
                        ),
                    )
                )
    elif group in {"I01", "I02", "I03", "I04", "I05", "I06"}:
        old = x.identity.claims[0]
        if group == "I01":
            renamed = replace(
                old, claim_id="rename", symbol="NEW", valid_from=D + timedelta(days=1)
            )
            identity = replace(
                x.identity, claims=(replace(old, valid_to=renamed.valid_from), renamed)
            )
            assert query(
                replace(x, identity=identity), day=D + timedelta(days=2)
            ).included_member_ids == ("security-a",)
        elif group == "I02":
            changed = replace(m, security_id="wrong")
            assert (
                query(replace(x, memberships=(changed,))).decisions[0].status
                == "UNRESOLVED_IDENTITY"
            )
        elif group == "I04":
            changed = replace(
                m, claim=replace(m.claim, symbol="MISSING"), security_id=None, listing_id=None
            )
            out = query(replace(x, memberships=(changed,)))
            assert out.accounted_count == 1 and out.decisions[0].status == "UNRESOLVED_IDENTITY"
        elif group == "I06":
            other = replace(
                m, claim=replace(m.claim, membership_id="duplicate"), event_id="event-b"
            )
            out = query(replace(x, memberships=(m, other)))
            assert (
                len(out.member_identities) == 1
                and not out.included_member_ids
                and all(d.status == "CONFLICTING_MEMBERSHIP" for d in out.decisions)
            )
        else:
            identity = replace(
                x.identity,
                claims=(replace(old, lifecycle="DELISTED" if group == "I03" else "SUSPENDED"),),
            )
            out = query(replace(x, identity=identity))
            assert out.included_member_ids == ("security-a",) and not out.execution_accepted
    elif group in {"C01", "C02", "C03", "C04", "C05"}:
        if group == "C01":
            assert (
                query(replace(x, coverage=(replace(coverage, state="PARTIAL"),))).coverage_state
                == "PARTIAL"
            )
        elif group == "C02":
            changed = replace(m, claim=replace(m.claim, valid_to=D + timedelta(days=2)))
            cov = replace(
                coverage,
                granularity="COMPLETE_CHANGE_HISTORY",
                ending_member_identities=(),
                ending_reference="ending",
            )
            assert (
                query(replace(x, memberships=(changed,), coverage=(cov,))).coverage_state
                == "PARTIAL"
            )
        elif group == "C03":
            assert (
                query(
                    replace(
                        x,
                        coverage=(
                            coverage,
                            replace(
                                coverage, coverage_id="other", expected_member_identities=("other",)
                            ),
                        ),
                    )
                ).coverage_state
                == "CONFLICTING"
            )
        elif group == "C04":
            assert query(replace(x, memberships=(), coverage=())).coverage_state == "UNKNOWN"
        else:
            assert (
                not query(x).financial_accepted
                and query(x).coverage_state == "COMPLETE_FOR_DECLARED_NON_MARKET_SCOPE"
            )
    elif group.startswith("A"):
        o = observation(x)
        changes = {
            "A01": {"known_from": K + timedelta(seconds=1)},
            "A02": {"published_at": K + timedelta(seconds=1)},
            "A03": {},
            "A04": {"interval_completed_at": K + timedelta(hours=1)},
            "A05": {"known_from": None},
        }[group]
        o = replace(o, **changes)
        policy = c.AvailabilityPolicy(
            "availability-v1",
            "CONSERVATIVE" if group == "A05" else "STRICT",
            bound=K if group == "A05" else None,
        )
        assert t.availability(o, K, policy, x) == (
            "AVAILABLE" if group == "A03" else "BLOCKED_AVAILABILITY"
        )
    elif group.startswith("L"):
        from omegadata.session_calendar import CoverageClaim, SessionClaim, VerifiedCalendar

        session = SessionClaim(
            "session",
            "CANARY-X",
            D,
            "REGULAR",
            "Asia/Kolkata",
            "calendar-v1",
            x.definition.evidence,
            K,
            None,
            closes_at=K + timedelta(hours=1),
        )
        cal = VerifiedCalendar(
            (session,),
            (
                CoverageClaim(
                    "range",
                    "CANARY-X",
                    D,
                    D + timedelta(days=1),
                    K,
                    None,
                    x.definition.evidence,
                    "calendar-v1",
                    "COMPLETE",
                ),
            ),
        )
        x = replace(x, calendar=cal)
        o = observation(
            x, interval_completed_at=K + timedelta(hours=1), known_from=K + timedelta(hours=1)
        )
        known = K + timedelta(hours=2)
        lp = c.LiquidityPolicy(
            "liquid-v1",
            1,
            1,
            Decimal(0),
            Decimal(0),
            Decimal(1),
            "CONTROL_UNIT",
            "CONTROL_ONLY",
            "RAW_UNADJUSTED",
            "RAW",
        )
        obs = (o,)
        if group == "L02":
            assert (
                e.liquidity(m, x, (replace(o, volume=None),), D, known, lp)[0]
                == "BLOCKED_LIQUIDITY_COVERAGE"
            )
        elif group == "L03":
            obs = (o, replace(o, observation_id="duplicate"))
        elif group == "L04":
            obs = (replace(o, currency="OTHER"),)
        elif group == "L05":
            obs = ()
        elif group == "L01":
            assert e.liquidity(m, x, obs, D, K, lp)[0] == "BLOCKED_LIQUIDITY_COVERAGE"
        assert e.liquidity(m, x, obs, D, known, lp)[0] == (
            "ELIGIBLE" if group in {"L01", "L02"} else "BLOCKED_LIQUIDITY_COVERAGE"
        )
    elif group.startswith("E"):
        if group == "E01":
            out = query(x, policy=replace(p, view="RESEARCH", require_observations=True))
            assert (
                out.member_identities == ("security-a",)
                and out.decisions[0].status == "BLOCKED_AVAILABILITY"
            )
        elif group == "E02":
            assert (
                query(x, policy=replace(p, view="EXECUTION")).decisions[0].status
                == "BLOCKED_TRADABILITY"
            )
        else:
            from test_od07_final import setup_bound

            from omegadata.adjustments.bound_chain import calculate_bound_chain

            pin = setup_bound()[8]
            bound = calculate_bound_chain(pin)
            assert (
                e.adjustment_eligible(bound, None, K, "PRICE_RETURN", "BACKWARD_ADJUSTED")
                == "BLOCKED_ADJUSTMENT_CONTEXT"
            )
    elif group.startswith("R"):
        candidate = c.RankingCandidate("security-a", Decimal(10), observation(x))
        if group == "R01":
            assert e.reconstruct((candidate,), 1, K, x)[0] == "RECONSTRUCTED_PROVISIONAL"
        else:
            with pytest.raises(ValueError):
                e.reconstruct((candidate, candidate), 1, K, x)
    elif group.startswith("P"):
        url = (
            "sqlite:///:memory:"
            if group not in {"P04", "P06"}
            else "sqlite:///" + str(tmp_path / "universe.sqlite")
        )
        db = UniverseRepository(url, disposable_root=tmp_path)
        db.seed_context(x, p)
        db.pin_context("pin", x, D, K, p)
        out = query(x)
        if group == "P01":
            db.admit_snapshot("pin", out)
            db.admit_snapshot("pin", out)
        elif group == "P02":
            with pytest.raises(ValueError):
                db.admit_snapshot("pin", replace(out, decisions=(), selected_revision_ids=()))
        elif group == "P03":
            with pytest.raises(ValueError):
                db.admit_snapshot("pin", replace(out, decision_digest="forged"))
        elif group == "P04":
            db.admit_snapshot("pin", out)
            db.close()
            db = UniverseRepository(url, disposable_root=tmp_path)
            assert db.get_snapshot(out.universe_snapshot_id) == out.canonical_json
        elif group == "P05":
            with pytest.raises(ValueError):
                db.pin_context("pin", replace(x, memberships=()), D, K, p)
            db.admit_snapshot("pin", out)
        else:
            correction = replace(
                m,
                claim=replace(
                    m.claim,
                    membership_id="m-b",
                    known_from=K + timedelta(days=1),
                    supersedes_membership_id="m-a",
                ),
                revision_number=2,
            )
            db.append_membership(correction)
            with pytest.raises(ValueError):
                db.append_membership(
                    replace(correction, claim=replace(correction.claim, membership_id="m-c"))
                )
        db.close()
    elif group == "S01":
        assert query(replace(x, mode="STRICT")).decisions[0].status == "BLOCKED_SOURCE_RIGHTS"
    elif group == "S02":
        assert not query(x).financial_accepted and not query(x).execution_accepted
    elif group == "S03":
        import od05x_isolated_runner as boundary

        assert boundary.assert_boundary()["verified"]
    elif group == "S04":
        from omegadata.identity_adapters import strict_universe

        old = strict_universe((m.claim,), x.identity, "CONTROL_SCOPE", D, K, "CANARY_ONLY")
        assert old.accounted_count == 1


@pytest.mark.parametrize(
    "case",
    [
        "order",
        "future-digest",
        "naive",
        "wrong-pin",
        "replay",
        "explain",
        "changed-policy",
        "unknown-schema",
        "nonempty-rollback",
        "foreign-key",
        "immutable",
        "bounds",
        "cancel-lineage",
        "provisional",
        "observation-future-digest",
        "definition-expired",
    ],
)
def test_review_controls(case, tmp_path):
    c, x, m, cov, p, run = setup_case()
    from omegadata.universe import snapshots as s
    from omegadata.universe.repository import UniverseRepository

    if case == "order":
        assert (
            query(replace(x, memberships=tuple(reversed(x.memberships)))).snapshot_digest
            == query(x).snapshot_digest
        )
    elif case == "future-digest":
        future = replace(
            m,
            claim=replace(
                m.claim,
                membership_id="future",
                known_from=K + timedelta(days=1),
                supersedes_membership_id="m-a",
            ),
            revision_number=2,
        )
        assert (
            query(replace(x, memberships=(m, future))).snapshot_digest == query(x).snapshot_digest
        )
    elif case == "naive":
        with pytest.raises(ValueError):
            query(x, known=K.replace(tzinfo=None))
    elif case == "wrong-pin":
        with pytest.raises(ValueError):
            run(x, D, K, p, "wrong")
    elif case == "replay":
        out = s.replay_universe_decisions(
            x, ((D, K), (D, K + timedelta(seconds=1))), p, max_steps=2
        )
        assert len(out) == 2
    elif case == "explain":
        assert s.explain_member_decision(query(x), "m-a").revision_id == "m-a"
    elif case == "bounds":
        with pytest.raises(ValueError):
            s.replay_universe_decisions(x, ((D, K),), p, max_steps=0)
    elif case == "cancel-lineage":
        with pytest.raises(ValueError):
            query(replace(x, memberships=(replace(m, revision_number=2),)))
    elif case == "provisional":
        assert (
            query(
                replace(
                    x,
                    memberships=(
                        replace(m, claim=replace(m.claim, status="RECONSTRUCTED_PROVISIONAL")),
                    ),
                )
            )
            .decisions[0]
            .status
            == "PROVISIONAL_ONLY"
        )
    elif case == "observation-future-digest":
        assert (
            query(
                replace(x, observations=(observation(x, known_from=K + timedelta(days=1)),))
            ).snapshot_digest
            == query(x).snapshot_digest
        )
    elif case == "definition-expired":
        with pytest.raises(ValueError):
            query(
                replace(x, definition=replace(x.definition, known_to=K + timedelta(seconds=1))),
                known=K + timedelta(seconds=1),
            )
    else:
        from sqlalchemy import text

        db = UniverseRepository("sqlite:///:memory:", disposable_root=tmp_path)
        db.seed_context(x, p)
        db.pin_context("pin", x, D, K, p)
        out = query(x)
        db.admit_snapshot("pin", out)
        if case == "changed-policy":
            with pytest.raises(ValueError):
                db.seed_context(x, replace(p, view="RESEARCH"))
        elif case == "nonempty-rollback":
            with pytest.raises(ValueError):
                db.rollback_empty()
        elif case == "foreign-key":
            with pytest.raises(IntegrityError), db.transaction() as con:
                con.execute(
                    text(
                        "INSERT INTO od08_decision(snapshot,revision,payload,digest) VALUES('missing','missing','x','x')"
                    )
                )
        elif case == "immutable":
            with pytest.raises(IntegrityError), db.transaction() as con:
                con.execute(text("DELETE FROM od08_membership"))
        elif case == "unknown-schema":
            with pytest.raises(IntegrityError), db.transaction() as con:
                con.execute(text("UPDATE od08_schema SET version='unknown'"))
        db.close()


@pytest.mark.parametrize(
    "case",
    [
        "context-checksum",
        "replay-restart",
        "omitted-ledger",
        "omitted-coverage",
        "order-observations",
        "complete-transition",
        "listing-granularity",
        "actual-rollback",
        "migration-empty",
        "read-only-backfill",
        "closed-session",
        "same-instant-correction",
        "replay-bool",
        "future-definition",
        "ranking-tie",
    ],
)
def test_independent_review(case, tmp_path):
    from sqlalchemy import text

    from omegadata.universe import eligibility as e
    from omegadata.universe import snapshots as s
    from omegadata.universe.repository import UniverseRepository

    c, x, m, cov, p, run = setup_case()
    if case == "context-checksum":
        db = UniverseRepository("sqlite:///:memory:", disposable_root=tmp_path)
        db.seed_context(x, p)
        db.pin_context("pin", x, D, K, p)
        with db.transaction() as con:
            con.exec_driver_sql("DROP TRIGGER od08_context_update")
            con.exec_driver_sql("UPDATE od08_context SET payload=payload||' '")
        with pytest.raises(ValueError):
            db.admit_snapshot("pin", query(x))
    elif case == "replay-restart":
        url = "sqlite:///" + str(tmp_path / "replay.sqlite")
        db = UniverseRepository(url, disposable_root=tmp_path)
        db.seed_context(x, p)
        db.pin_context("pin", x, D, K, p)
        db.admit_snapshot("pin", query(x))
        db.close()
        db = UniverseRepository(url, disposable_root=tmp_path)
        assert db.replay_context("pin").snapshot_digest == query(x).snapshot_digest
    elif case in {"omitted-ledger", "omitted-coverage"}:
        db = UniverseRepository("sqlite:///:memory:", disposable_root=tmp_path)
        db.seed_context(x, p)
        with pytest.raises(ValueError):
            db.pin_context(
                "pin",
                replace(
                    x, **({"memberships": ()} if case == "omitted-ledger" else {"coverage": ()})
                ),
                D,
                K,
                p,
            )
    elif case == "order-observations":
        a = observation(x)
        b = replace(a, observation_id="other", session_date=D - timedelta(days=1))
        policy = replace(p, view="RESEARCH")
        assert (
            query(replace(x, observations=(a, b)), policy=policy).snapshot_digest
            == query(replace(x, observations=(b, a)), policy=policy).snapshot_digest
        )
    elif case == "complete-transition":
        end = D + timedelta(days=2)
        member = replace(m, claim=replace(m.claim, valid_to=end))
        coverage = replace(
            cov,
            transitions=(c.CoverageTransition("m-a", "security-a", "REMOVE", end),),
            ending_member_identities=(),
        )
        y = replace(x, memberships=(member,), coverage=(coverage,))
        assert query(y).coverage_state == "COMPLETE_FOR_DECLARED_NON_MARKET_SCOPE"
        assert (
            query(y, day=end).member_identities == ()
            and query(y, day=end).coverage_state == "COMPLETE_FOR_DECLARED_NON_MARKET_SCOPE"
        )
    elif case == "listing-granularity":
        from omegadata.identity import Listing

        old = x.identity.claims[0]
        otherlisting = Listing("listing-b", "security-a", "CANARY-X")
        otherclaim = replace(old, claim_id="claim-b", listing_id="listing-b", series="OTHER")
        identity = replace(
            x.identity,
            listings=(*x.identity.listings, otherlisting),
            claims=(*x.identity.claims, otherclaim),
        )
        other = replace(
            m,
            claim=replace(m.claim, membership_id="m-b", series="OTHER"),
            event_id="event-b",
            listing_id="listing-b",
        )
        coverage = replace(
            cov,
            expected_member_identities=("listing-a", "listing-b"),
            ending_member_identities=("listing-a", "listing-b"),
        )
        y = replace(
            x,
            definition=replace(x.definition, identity_granularity="LISTING"),
            identity=identity,
            memberships=(m, other),
            coverage=(coverage,),
        )
        assert query(y).included_member_ids == ("listing-a", "listing-b")
    elif case == "actual-rollback":
        db = UniverseRepository("sqlite:///:memory:", disposable_root=tmp_path)
        db.seed_context(x, p)
        with pytest.raises(RuntimeError), db.transaction() as con:
            db._put(
                con,
                __import__("omegadata.universe.repository", fromlist=["policies"]).policies,
                "new-policy",
                replace(p, policy_version="new-policy"),
            )
            raise RuntimeError("CONTROLLED_INTERRUPT")
        with db.engine.connect() as con:
            assert con.scalar(text("SELECT count(*) FROM od08_policy WHERE id='new-policy'")) == 0
    elif case == "migration-empty":
        db = UniverseRepository("sqlite:///:memory:", disposable_root=tmp_path)
        db.rollback_empty()
        db.close()
    elif case == "read-only-backfill":
        from omegadata.universe.compatibility import source_dependent_backfill

        with pytest.raises(PermissionError):
            source_dependent_backfill()
    elif case == "closed-session":
        from omegadata.session_calendar import SessionClaim

        session = SessionClaim(
            "closed",
            "CANARY-X",
            D,
            "CLOSED",
            "Asia/Kolkata",
            "calendar",
            x.definition.evidence,
            K,
            None,
        )
        y = replace(x, calendar=replace(x.calendar, claims=(session,)))
        out = query(y, policy=replace(p, view="EXECUTION"))
        assert (
            out.member_identities == ("security-a",)
            and out.decisions[0].status == "BLOCKED_TRADABILITY"
        )
    elif case == "same-instant-correction":
        child = replace(
            m,
            claim=replace(m.claim, membership_id="bad", supersedes_membership_id="m-a"),
            revision_number=2,
        )
        with pytest.raises(ValueError):
            query(replace(x, memberships=(m, child)))
    elif case == "replay-bool":
        with pytest.raises(ValueError):
            s.replay_universe_decisions(x, ((D, K),), p, max_steps=True)
    elif case == "future-definition":
        with pytest.raises(ValueError):
            query(replace(x, definition=replace(x.definition, known_from=K + timedelta(seconds=1))))
    elif case == "ranking-tie":
        first = c.RankingCandidate("security-a", Decimal(10), observation(x))
        out = e.reconstruct((first,), 1, K, x)
        assert out[1] == ("security-a",) and out[0] == "RECONSTRUCTED_PROVISIONAL"


@pytest.mark.parametrize(
    "case", ["valid-adjustment", "wrong-profile", "future-context", "persist-adjustment", "persist-authority-object"]
)
def test_od07_bound_integration(case, tmp_path):
    from test_od07_final import setup_bound

    from omegadata.adjustments.bound_chain import calculate_bound_chain
    from omegadata.identity_adapters import MembershipClaim
    from omegadata.universe import contracts as c
    from omegadata.universe.repository import UniverseRepository

    pin = setup_bound()[8]
    if case == "persist-authority-object":
        from omegadata.identity_authority import EvidenceAuthority
        pin=replace(pin,context=replace(pin.context,authority=EvidenceAuthority.unconfigured()))
    raw = pin.raw.raw
    result = calculate_bound_chain(pin)
    e = raw.evidence
    known = pin.context.known_at
    day = pin.context.valid_at
    claim = MembershipClaim(
        "m-bound",
        "BOUND_CONTROL",
        raw.symbol,
        raw.series,
        raw.exchange,
        raw.trade_date,
        None,
        raw.known_from,
        None,
        e,
    )
    member = c.MembershipRevision(
        claim, "event", "math-source", "artifact", "record", raw.security_id, raw.listing_id
    )
    definition = c.UniverseDefinition(
        "BOUND_CONTROL",
        "Anonymous bound contract",
        "CUSTOM_POLICY_UNIVERSE",
        "SECURITY",
        "method",
        ("math-source",),
        (raw.exchange,),
        raw.trade_date,
        None,
        raw.known_from,
        None,
        e,
    )
    coverage = c.UniverseCoverage(
        "cov",
        "BOUND_CONTROL",
        "math-source",
        "ref",
        "method",
        raw.trade_date,
        day + timedelta(days=1),
        raw.known_from,
        None,
        "COMPLETE_FOR_DECLARED_NON_MARKET_SCOPE",
        (raw.security_id,),
        e,
        "independent-control",
        granularity="COMPLETE_CHANGE_HISTORY",
        ending_member_identities=(raw.security_id,),
        ending_reference="end",
    )
    obs = c.AvailabilityObservation(
        "bound-observation",
        "CONTROL_ONLY",
        raw.listing_id,
        raw.trade_date,
        None,
        raw.known_from,
        None,
        raw.known_from,
        None,
        None,
        "math-source",
        "raw-artifact",
        e,
        interval_completed_at=raw.known_from,
        record_identity="record",
        adjustment=result,
        adjustment_pin=pin,
    )
    x = c.UniverseContext(
        "source-pin",
        definition,
        (member,),
        (coverage,),
        pin.context.identity_repository,
        pin.context.calendar,
        (obs,),
        mode="CANARY_ONLY",
    )
    policy = c.EligibilityPolicy(
        "bound-policy", "RESEARCH", require_observations=True, require_adjustment=True
    )
    if case == "wrong-profile":
        policy = replace(policy, required_profile="TOTAL_RETURN")
    if case == "future-context":
        known -= timedelta(days=1)
    from omegadata.universe.snapshots import get_universe_as_of

    out = get_universe_as_of(x, day, known, policy, "source-pin")
    assert out.decisions[0].status == (
        "BLOCKED_AVAILABILITY" if case in {"wrong-profile", "future-context"} else "INCLUDED"
    )
    assert not out.financial_accepted
    if case in {"persist-adjustment", "persist-authority-object"}:
        db = UniverseRepository("sqlite:///:memory:", disposable_root=tmp_path)
        db.seed_context(x, policy)
        db.pin_context("bound-pin", x, day, known, policy)
        db.admit_snapshot("bound-pin", out)
        assert db.replay_context("bound-pin").snapshot_digest == out.snapshot_digest


@pytest.mark.parametrize(
    "case", ["future-announcement", "future-publication", "intraday-before", "intraday-at"]
)
def test_source_time_boundaries(case):
    from omegadata.universe.temporal import get_known_upcoming_changes

    c, x, m, cov, p, run = setup_case()
    if case.startswith("future"):
        values = (
            {"announcement_at": K + timedelta(seconds=1)}
            if case == "future-announcement"
            else {"published_at": K + timedelta(seconds=1)}
        )
        changed = replace(m, claim=replace(m.claim, valid_from=D + timedelta(days=1)), **values)
        out = get_known_upcoming_changes(replace(x, memberships=(changed,)), D, K)
        assert out[0][1] == "BLOCKED_AVAILABILITY"
    else:
        effective = K + timedelta(hours=1)
        changed = replace(m, effective_at=effective, effective_convention="EXPLICIT_TIMESTAMP")
        instant = effective - timedelta(seconds=1) if case == "intraday-before" else effective
        out = run(
            replace(x, memberships=(changed,)), instant, K + timedelta(hours=2), p, "source-pin"
        )
        assert out.selected_revision_ids == (() if case == "intraday-before" else ("m-a",))


def test_identity_selection_candidate_budget(monkeypatch):
    from omegadata.identity import Listing, MemoryIdentityRepository, Security

    c, x, m, cov, p, run = setup_case()
    securities = (
        Security("s0", "issuer-a"),
        Security("s1", "issuer-a"),
        Security("s2", "issuer-a"),
    )
    listings = tuple(
        Listing("l" + str(i), s.security_id, "CANARY-X") for i, s in enumerate(securities)
    )
    claims = tuple(
        replace(
            x.identity.claims[0],
            claim_id="i" + str(i),
            listing_id=listing.listing_id,
            symbol="T" + str(i),
        )
        for i, listing in enumerate(listings)
    )
    identity = replace(x.identity, securities=securities, listings=listings, claims=claims)
    members = tuple(
        replace(
            m,
            claim=replace(m.claim, membership_id="m" + str(i), symbol="T" + str(i)),
            event_id="event" + str(i),
            security_id=s.security_id,
            listing_id=listings[i].listing_id,
        )
        for i, s in enumerate(securities)
    )
    y = replace(
        x,
        identity=identity,
        memberships=members,
        coverage=(
            replace(
                cov,
                expected_member_identities=("s0", "s1", "s2"),
                ending_member_identities=("s0", "s1", "s2"),
            ),
        ),
    )
    examined = []
    original = MemoryIdentityRepository.resolve_listing

    def trace(repository, *args, **kwargs):
        examined.append(len(repository.claims))
        return original(repository, *args, **kwargs)

    monkeypatch.setattr(MemoryIdentityRepository, "resolve_listing", trace)
    assert query(y).included_member_ids == ("s0", "s1", "s2")
    assert sum(examined) <= 4 * len(members)


def test_two_connection_competing_corrections(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from omegadata.universe.repository import UniverseRepository

    c, x, m, cov, p, run = setup_case()
    url = "sqlite:///" + str(tmp_path / "competing.sqlite")
    first = UniverseRepository(url, disposable_root=tmp_path)
    first.seed_context(x, p)
    second = UniverseRepository(url, disposable_root=tmp_path)
    barrier = Barrier(2)

    def attempt(repository, name):
        child = replace(
            m,
            claim=replace(
                m.claim,
                membership_id=name,
                known_from=K + timedelta(days=1),
                supersedes_membership_id="m-a",
            ),
            revision_number=2,
        )
        barrier.wait(timeout=5)
        try:
            repository.append_membership(child)
            return "COMMITTED"
        except (ValueError, IntegrityError):
            return "REFUSED"

    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(attempt, first, "candidate-a")
        b = pool.submit(attempt, second, "candidate-b")
        assert sorted((a.result(), b.result())) == ["COMMITTED", "REFUSED"]
    first.close()
    second.close()


@pytest.mark.parametrize('case',['source-scope','expected-identities','transitions'])
def test_immutable_source_contracts(case):
    c,x,m,cov,p,run=setup_case()
    with pytest.raises(ValueError):
        if case=='source-scope':replace(x.definition,source_scope=['control-source'])
        elif case=='expected-identities':replace(cov,expected_member_identities=['security-a'])
        else:replace(cov,transitions=[])
