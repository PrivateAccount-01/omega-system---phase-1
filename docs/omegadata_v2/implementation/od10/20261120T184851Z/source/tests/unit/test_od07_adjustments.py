"""OD07 NON_MARKET_MATH / anonymous invariant controls; zero authentic rows.
Expected factors are literal rational/Decimal known answers, never production outputs.
"""

import json
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, localcontext
from fractions import Fraction

import pytest
from sqlalchemy.exc import IntegrityError

D = date(2001, 1, 4)
K = datetime(2001, 1, 1, tzinfo=UTC)


def system():
    from omegadata.adjustments import contracts as c
    from omegadata.identity import (
        Evidence,
        IdentifierClaim,
        Issuer,
        Listing,
        MemoryIdentityRepository,
        Security,
    )
    from omegadata.session_calendar import CoverageClaim, SessionClaim, VerifiedCalendar

    e = Evidence("math-e", "NON_MARKET_CANARY", "UNVERIFIED", "PERMITTED", "math-review")
    repo = MemoryIdentityRepository(
        (Issuer("i"),),
        (Security("s", "i"),),
        (Listing("l", "s", "MATH"),),
        (IdentifierClaim("ic", "l", "MATH", "TOKEN", "TEST", date(2000, 1, 1), None, K, None, e),),
    )
    sessions = tuple(
        SessionClaim(
            "session-" + str(i),
            "MATH",
            D + timedelta(days=i),
            "CLOSED" if i in (-2, -1) else "REGULAR",
            "Asia/Kolkata",
            "cal-v1",
            e,
            K,
            None,
        )
        for i in range(-3, 10)
    )
    coverage = (
        CoverageClaim(
            "coverage",
            "MATH",
            D - timedelta(days=3),
            D + timedelta(days=10),
            K,
            None,
            e,
            "cal-v1",
            "COMPLETE",
        ),
    )
    cal = VerifiedCalendar(sessions, coverage)
    ctx = c.Context(
        D + timedelta(days=5),
        K + timedelta(days=20),
        "od06.identity/v1",
        "ev-v1",
        "cal-v1",
        "NON_MARKET_MATH",
        repo,
        cal,
    )
    a = c.Action(
        "a",
        "SPLIT",
        "s",
        "l",
        "MATH",
        e,
        "artifact-math",
        D,
        K,
        None,
        c.Split(Decimal("2")),
        source_id="math-source",
    )
    raw = c.Raw(
        "raw-math",
        "s",
        "l",
        "MATH",
        "TOKEN",
        "TEST",
        D - timedelta(days=4),
        K,
        Decimal("120"),
        Decimal("10"),
        "MATH_UNIT",
        e,
    )
    return c, ctx, a, raw


def chain(actions=None, ctx=None, raw=None, profile="PRICE_RETURN", direction="BACKWARD"):
    from omegadata.adjustments.chains import calculate_chain

    c, x, a, r = system()
    return calculate_chain(
        r if raw is None else raw,
        (a,) if actions is None else actions,
        c.Policy(profile, direction=direction),
        x if ctx is None else ctx,
    )


@pytest.mark.parametrize(
    "kind,args,want",
    [
        ("SPLIT", ("2",), "1/2"),
        ("SPLIT", ("0.2",), "5/1"),
        ("BONUS", ("1", "2"), "2/3"),
        ("BONUS", ("2", "1"), "1/3"),
        ("RIGHTS", ("4", "1", "100", "50"), "9/10"),
        ("RIGHTS", ("3", "2", "120", "30"), "7/10"),
        ("DIVIDEND_CASH", ("5", "95"), "19/20"),
        ("DIVIDEND_SPECIAL", ("20", "80"), "4/5"),
    ],
)
def test_math_oracle(kind, args, want):
    from omegadata.adjustments.factors import factor

    c, _, _, _ = system()
    ds = tuple(Decimal(x) for x in args)
    if kind == "SPLIT":
        p = c.Split(*ds)
    elif kind == "BONUS":
        p = c.Bonus(*ds)
    elif kind == "RIGHTS":
        p = c.Rights(
            ds[0],
            ds[1],
            ds[3],
            c.Reference(ds[2], D - timedelta(days=3), K, "prior", "MATH_UNIT"),
            "MATH_UNIT",
            True,
        )
    else:
        p = c.Dividend(
            ds[0], "MATH_UNIT", c.Reference(ds[1], D, K, "reinvest", "MATH_UNIT"), "EX_CLOSE_GROSS"
        )
    out = factor(kind, p, c.Policy("TOTAL_RETURN"))
    expected = Fraction(want)
    assert out.status == "CALCULATED"
    assert Fraction(out.numerator) / Fraction(out.denominator) == expected
    with localcontext() as context:
        context.prec = 80
        assert out.price_factor == Decimal(expected.numerator) / Decimal(expected.denominator)


@pytest.mark.parametrize(
    "group",
    [
        "M01",
        "M05",
        "M07",
        "M08",
        "M09",
        "T01",
        "T02",
        "T03",
        "T04",
        "T05",
        "T06",
        "T07",
        "C01",
        "C02",
        "C03",
        "C04",
        "C05",
        "C06",
        "S01",
        "S02",
        "S03",
        "S04",
    ],
)
def test_acceptance(group, tmp_path):
    from omegadata.adjustments.compatibility import legacy_action
    from omegadata.adjustments.factors import factor
    from omegadata.adjustments.temporal import select_revisions

    c, x, a, r = system()
    if group == "M01":
        out = factor("BONUS", c.Bonus(Decimal(2), Decimal(1)), c.Policy("PRICE_RETURN"))
        assert out.price_factor == Decimal("0." + "3" * 80)
        assert chain().adjusted_price == Decimal("60.000000")
    elif group == "M05":
        p = c.Rights(Decimal(4), Decimal(1), None, None, "MATH_UNIT", True)
        assert factor("RIGHTS", p, c.Policy("PRICE_RETURN")).status == "INVALID_PARAMETERS"
    elif group == "M07":
        p = c.Dividend(
            Decimal(5),
            "MATH_UNIT",
            c.Reference(Decimal(95), D, K, "ref", "MATH_UNIT"),
            "EX_CLOSE_GROSS",
        )
        assert factor("DIVIDEND_CASH", p, c.Policy("PRICE_RETURN")).status == "NOT_APPLICABLE"
        assert factor("DIVIDEND_CASH", p, c.Policy("TOTAL_RETURN")).price_factor == Decimal(".95")
    elif group == "M08":
        assert chain(profile="VOLUME").adjusted_volume == Decimal("20.0000")
        assert chain(profile="VOLUME").adjusted_price == r.price
    elif group == "M09":
        out = chain(profile="EXECUTION")
        assert out.adjusted_price == r.price and out.adjusted_volume == r.volume
        assert out.original_price_basis == "RAW" and not out.publication_eligibility
    elif group == "T01":
        assert (
            chain(ctx=replace(x, known_at=K - timedelta(seconds=1))).status == "BLOCKED_KNOWLEDGE"
        )
        assert chain(actions=(replace(a, known_from=None),)).status == "BLOCKED_KNOWLEDGE"
    elif group == "T02":
        assert (
            chain(actions=(replace(a, known_from=x.known_at + timedelta(seconds=1)),)).status
            == "BLOCKED_KNOWLEDGE"
        )
        assert (
            chain(actions=(replace(a, published_at=x.known_at + timedelta(seconds=1)),)).status
            == "BLOCKED_KNOWLEDGE"
        )
    elif group == "T03":
        p = c.Demerger(
            "successor",
            Decimal(1),
            c.Reference(Decimal(20), D, x.known_at + timedelta(seconds=1), "later", "MATH_UNIT"),
        )
        assert (
            chain(actions=(replace(a, action_type="DEMERGER_PARENT", parameters=p),)).status
            == "BLOCKED_KNOWLEDGE"
        )
    elif group == "T04":
        b = replace(
            a,
            action_id="b",
            action_revision=2,
            supersedes_action_id="a",
            known_from=K + timedelta(days=10),
            parameters=c.Split(Decimal(4)),
        )
        old = chain((a, b), ctx=replace(x, known_at=K + timedelta(days=9)))
        new = chain((a, b))
        assert old.adjusted_price == Decimal(60) and new.adjusted_price == Decimal(30)
        assert old.output_digest != new.output_digest and a.parameters.multiplier == 2
    elif group == "T05":
        b = replace(
            a,
            action_id="b",
            action_revision=2,
            supersedes_action_id="a",
            known_from=K + timedelta(days=10),
            review_status="REVOKED",
        )
        assert chain((a, b)).status == "BLOCKED_EVIDENCE"
        assert select_revisions((a, b), K + timedelta(days=9)) == (a,)
    elif group == "T06":
        p = c.Rights(
            Decimal(4),
            Decimal(1),
            Decimal(50),
            c.Reference(Decimal(100), D - timedelta(days=1), K, "wrong-day", "MATH_UNIT"),
            "MATH_UNIT",
            True,
        )
        assert chain((replace(a, action_type="RIGHTS", parameters=p),)).status == "BLOCKED_CALENDAR"
        p = replace(p, reference=replace(p.reference, session_date=D - timedelta(days=3)))
        assert chain((replace(a, action_type="RIGHTS", parameters=p),)).status == "CALCULATED"
    elif group == "T07":
        assert (
            chain(
                ctx=replace(x, identity_repository=replace(x.identity_repository, claims=()))
            ).status
            == "BLOCKED_IDENTITY"
        )
    elif group == "C01":
        b = replace(
            a,
            action_id="b",
            ex_date=D + timedelta(days=1),
            action_type="BONUS",
            parameters=c.Bonus(Decimal(1), Decimal(2)),
        )
        assert chain((a, b)).adjusted_price == Decimal(40)
        assert chain((b, a)).output_digest == chain((a, b)).output_digest
    elif group == "C02":
        b = replace(a, action_id="b", parameters=c.Split(Decimal(3)))
        assert chain((a, b)).status == "CONFLICTING_ACTIONS"
        assert chain((replace(a, sequence=1), replace(b, sequence=2))).adjusted_price == Decimal(20)
    elif group == "C03":
        with pytest.raises(ValueError):
            select_revisions((a, a), x.known_at)
        with pytest.raises(ValueError):
            select_revisions((replace(a, supersedes_action_id="absent"),), x.known_at)
    elif group == "C04":
        assert chain().output_digest == chain().output_digest
        assert "0.5" in chain().canonical_json and "120" in chain().canonical_json
        assert json.loads(chain().canonical_json)["consumer_profile"] == "PRICE_RETURN"
    elif group == "C05":
        before = repr((a, r))
        out = chain()
        assert repr((a, r)) == before
        with pytest.raises(FrozenInstanceError):
            out.adjusted_price = Decimal(0)
    elif group == "C06":
        bad = replace(
            a, action_id="bad", ex_date=D + timedelta(days=1), parameters=c.Split(Decimal(0))
        )
        out = chain((a, bad))
        assert out.status == "INVALID_PARAMETERS"
        assert (
            out.adjusted_price is None
            and out.cumulative_factor is None
            and out.adjustment_factor_chain == ()
        )
    elif group == "S01":
        assert (
            chain((replace(a, evidence=replace(a.evidence, permission="DENIED")),)).status
            == "BLOCKED_EVIDENCE"
        )
    elif group == "S02":
        forged = replace(
            a,
            evidence=replace(
                a.evidence, classification="SOURCE_DOCUMENT", authentication="VERIFIED"
            ),
        )
        assert chain((forged,), ctx=replace(x, mode="STRICT")).status == "BLOCKED_EVIDENCE"
        assert not chain().publication_eligibility
        with pytest.raises(TypeError):
            c.Result("CALCULATED", "bad", publication_eligibility=True)
    elif group == "S03":
        from types import SimpleNamespace

        row = SimpleNamespace(
            id=1, parameters={"issue_price": None}, created_at=K, ex_date=D, action_type="RIGHTS"
        )
        old = repr(row.__dict__)
        result = legacy_action(row)
        assert result.known_from is None and result.status == "BLOCKED_EVIDENCE"
        assert repr(row.__dict__) == old
    elif group == "S04":
        import od05x_isolated_runner

        proof = od05x_isolated_runner.assert_boundary()
        assert proof
        assert not __import__("pathlib").Path("/mnt/e").exists()


@pytest.mark.parametrize(
    "case",
    [
        "zero",
        "negative",
        "nan",
        "infinity",
        "float",
        "bonus-denominator",
        "rights-currency",
        "rights-exercise",
        "dividend-price",
        "dividend-time",
        "unsupported",
        "lifecycle",
        "post-ex",
        "forward",
        "chain-limit",
        "wrong-security",
        "suspended",
        "naive",
        "unknown-version",
    ],
)
def test_refusal_and_boundaries(case):
    from omegadata.adjustments.factors import factor

    c, x, a, r = system()
    if case in {"zero", "negative", "nan", "infinity", "float"}:
        v = {
            "zero": Decimal(0),
            "negative": Decimal(-1),
            "nan": Decimal("NaN"),
            "infinity": Decimal("Infinity"),
            "float": 2.0,
        }[case]
        assert factor("SPLIT", c.Split(v), c.Policy("PRICE_RETURN")).status == "INVALID_PARAMETERS"
    elif case == "bonus-denominator":
        assert (
            factor("BONUS", c.Bonus(Decimal(1), Decimal(0)), c.Policy("PRICE_RETURN")).status
            == "INVALID_PARAMETERS"
        )
    elif case == "rights-currency":
        p = c.Rights(
            Decimal(4),
            Decimal(1),
            Decimal(50),
            c.Reference(Decimal(100), D, K, "ref", "OTHER"),
            "MATH_UNIT",
            True,
        )
        assert factor("RIGHTS", p, c.Policy("PRICE_RETURN")).status == "INVALID_PARAMETERS"
    elif case == "rights-exercise":
        p = c.Rights(
            Decimal(4),
            Decimal(1),
            Decimal(50),
            c.Reference(Decimal(100), D, K, "ref", "MATH_UNIT"),
            "MATH_UNIT",
            None,
        )
        assert factor("RIGHTS", p, c.Policy("PRICE_RETURN")).status == "INVALID_PARAMETERS"
    elif case == "dividend-price":
        assert (
            factor(
                "DIVIDEND_SPECIAL",
                c.Dividend(Decimal(1), "MATH_UNIT", None, "EX_CLOSE_GROSS"),
                c.Policy("TOTAL_RETURN"),
            ).status
            == "INVALID_PARAMETERS"
        )
    elif case == "dividend-time":
        p = c.Dividend(
            Decimal(1),
            "MATH_UNIT",
            c.Reference(Decimal(10), D, x.known_at + timedelta(seconds=1), "ref", "MATH_UNIT"),
            "EX_CLOSE_GROSS",
        )
        assert (
            chain(
                (replace(a, action_type="DIVIDEND_CASH", parameters=p),), profile="TOTAL_RETURN"
            ).status
            == "BLOCKED_KNOWLEDGE"
        )
    elif case == "unsupported":
        assert (
            chain(
                (
                    replace(
                        a,
                        action_type="MERGER",
                        parameters=c.Merger("other", Decimal(1), Decimal(0)),
                    ),
                )
            ).status
            == "UNSUPPORTED_POLICY"
        )
    elif case == "lifecycle":
        assert (
            factor("SUSPENSION", c.Lifecycle(), c.Policy("PRICE_RETURN")).status == "NOT_APPLICABLE"
        )
    elif case == "post-ex":
        assert chain(raw=replace(r, trade_date=D)).adjusted_price == r.price
    elif case == "forward":
        assert chain(direction="FORWARD").adjusted_price == Decimal(240)
    elif case == "chain-limit":
        many = tuple(replace(a, action_id=str(i)) for i in range(129))
        assert chain(many).status == "CONFLICTING_ACTIONS"
    elif case == "wrong-security":
        assert chain((replace(a, security_id="other"),)).status == "BLOCKED_IDENTITY"
    elif case == "suspended":
        repo = replace(
            x.identity_repository,
            claims=(replace(x.identity_repository.claims[0], lifecycle="SUSPENDED"),),
        )
        assert (
            chain(ctx=replace(x, identity_repository=repo), profile="EXECUTION").status
            == "BLOCKED_IDENTITY"
        )
    elif case == "naive":
        with pytest.raises(ValueError):
            replace(x, known_at=K.replace(tzinfo=None))
    elif case == "unknown-version":
        with pytest.raises(ValueError):
            c.Policy("PRICE_RETURN", version="unknown")


@pytest.mark.parametrize("memory", [True, False])
@pytest.mark.parametrize(
    "case",
    ["restart", "duplicate", "rollback", "append-only", "revisions", "foreign-key", "migration"],
)
def test_persistence(memory, case, tmp_path):
    from sqlalchemy import text

    from omegadata.adjustments.repository import AdjustmentRepository

    c, x, a, r = system()
    url = "sqlite:///:memory:" if memory else "sqlite:///" + str(tmp_path / "math.sqlite")
    repo = AdjustmentRepository(url, disposable_root=tmp_path)
    repo.append_action(a)
    out = chain()
    repo.append_result(out, ("a",))
    if case == "restart":
        if not memory:
            repo.close()
            repo = AdjustmentRepository(url, disposable_root=tmp_path)
        assert repo.get_result(out.output_digest) == out.canonical_json
    elif case == "duplicate":
        repo.append_action(a)
        with pytest.raises(ValueError):
            repo.append_action(replace(a, parameters=c.Split(Decimal(3))))
    elif case == "rollback":
        with pytest.raises(RuntimeError), repo.transaction() as connection:
            connection.execute(
                text(
                    "INSERT INTO od07_action(id,parent,payload,digest) VALUES ('broken',NULL,'bad','bad')"
                )
            )
            raise RuntimeError("controlled interruption")
        assert "broken" not in repo.action_ids()
    elif case == "append-only":
        with pytest.raises(IntegrityError), repo.transaction() as connection:
            connection.execute(text("DELETE FROM od07_action WHERE id='a'"))
        assert repo.action_ids() == ("a",)
    elif case == "revisions":
        b = replace(
            a,
            action_id="b",
            supersedes_action_id="a",
            action_revision=2,
            known_from=K + timedelta(days=1),
        )
        repo.append_action(b)
        assert repo.history("a") == (a, b)
        with pytest.raises(ValueError):
            repo.append_action(replace(b, action_id="c"))
    elif case == "foreign-key":
        with pytest.raises(ValueError):
            repo.append_result(replace(out, reason="different"), ("missing",))
    elif case == "migration":
        with pytest.raises(ValueError):
            repo.rollback_schema()
        empty = AdjustmentRepository("sqlite:///:memory:", disposable_root=tmp_path)
        empty.rollback_schema()
        empty.migrate()
        assert empty.action_ids() == ()
    repo.close()


@pytest.mark.parametrize(
    "case",
    [
        "empty-strict",
        "empty-denied",
        "empty-identity",
        "expired-action",
        "currency-mismatch",
        "nonfinite-action",
        "future-reference-date",
        "missing-reference-evidence",
        "wrong-parameter-version",
        "competing-correction",
        "timezone-reference",
        "suspension-constraint",
        "strict-labels",
        "known-boundary",
        "multistep",
        "rights-volume",
        "dividend-volume",
        "no-partial-ledger",
        "result-payload-binding",
        "quantum-bound",
        "context-precision",
    ],
)
def test_review_refusals(case, tmp_path):
    c, x, a, r = system()
    from omegadata.adjustments.factors import factor
    from omegadata.adjustments.repository import AdjustmentRepository
    from omegadata.adjustments.temporal import select_revisions

    if case == "empty-strict":
        assert chain((), ctx=replace(x, mode="STRICT")).status == "BLOCKED_EVIDENCE"
    elif case == "empty-denied":
        assert (
            chain((), raw=replace(r, evidence=replace(r.evidence, permission="DENIED"))).status
            == "BLOCKED_EVIDENCE"
        )
    elif case == "empty-identity":
        assert (
            chain(
                (), ctx=replace(x, identity_repository=replace(x.identity_repository, claims=()))
            ).status
            == "BLOCKED_IDENTITY"
        )
    elif case == "expired-action":
        assert chain((replace(a, known_to=K + timedelta(days=1)),)).status == "BLOCKED_KNOWLEDGE"
    elif case == "currency-mismatch":
        p = c.Dividend(
            Decimal(1), "OTHER", c.Reference(Decimal(10), D, K, "ref", "OTHER"), "EX_CLOSE_GROSS"
        )
        assert (
            chain(
                (replace(a, action_type="DIVIDEND_CASH", parameters=p),), profile="TOTAL_RETURN"
            ).status
            == "INVALID_PARAMETERS"
        )
    elif case == "nonfinite-action":
        assert (
            chain((replace(a, parameters=c.Split(Decimal("NaN"))),)).status == "INVALID_PARAMETERS"
        )
    elif case == "future-reference-date":
        p = c.Dividend(
            Decimal(1),
            "MATH_UNIT",
            c.Reference(Decimal(10), D + timedelta(days=1), K, "ref", "MATH_UNIT"),
            "EX_CLOSE_GROSS",
        )
        assert (
            chain(
                (replace(a, action_type="DIVIDEND_CASH", parameters=p),), profile="TOTAL_RETURN"
            ).status
            == "BLOCKED_CALENDAR"
        )
    elif case == "missing-reference-evidence":
        ref = c.Reference(Decimal(100), D - timedelta(days=3), K, "ref", "MATH_UNIT")
        p = c.Rights(Decimal(4), Decimal(1), Decimal(50), ref, "MATH_UNIT", True)
        assert (
            chain(
                (replace(a, action_type="RIGHTS", parameters=p),), ctx=replace(x, mode="STRICT")
            ).status
            == "BLOCKED_EVIDENCE"
        )
    elif case == "wrong-parameter-version":
        with pytest.raises(ValueError):
            replace(a, parameter_version="later")
    elif case == "competing-correction":
        b = replace(
            a,
            action_id="b",
            known_from=K + timedelta(days=1),
            action_revision=2,
            supersedes_action_id="a",
        )
        with pytest.raises(ValueError):
            select_revisions((a, b, replace(b, action_id="c")), x.known_at)
    elif case == "timezone-reference":
        p = c.Demerger(
            "other",
            Decimal(1),
            c.Reference(Decimal(10), D, K.replace(tzinfo=None), "ref", "MATH_UNIT"),
        )
        with pytest.raises(ValueError):
            chain((replace(a, action_type="DEMERGER_PARENT", parameters=p),))
    elif case == "suspension-constraint":
        assert (
            chain(
                (replace(a, action_type="SUSPENSION", parameters=c.Lifecycle()),),
                profile="EXECUTION",
            ).status
            == "BLOCKED_IDENTITY"
        )
    elif case == "strict-labels":
        assert not chain(ctx=replace(x, mode="STRICT")).publication_eligibility
    elif case == "known-boundary":
        b = replace(
            a,
            action_id="b",
            known_from=K + timedelta(days=10),
            action_revision=2,
            supersedes_action_id="a",
            parameters=c.Split(Decimal(4)),
        )
        assert select_revisions((a, b), b.known_from) == (b,)
    elif case == "multistep":
        b = replace(
            a,
            action_id="b",
            known_from=K + timedelta(days=1),
            action_revision=2,
            supersedes_action_id="a",
        )
        z = replace(
            b,
            action_id="z",
            known_from=K + timedelta(days=2),
            action_revision=3,
            supersedes_action_id="b",
            parameters=c.Split(Decimal(4)),
        )
        assert chain((z, a, b)).adjusted_price == Decimal(30)
    elif case == "rights-volume":
        p = c.Rights(
            Decimal(4),
            Decimal(1),
            Decimal(50),
            c.Reference(Decimal(100), D, K, "ref", "MATH_UNIT"),
            "MATH_UNIT",
            True,
        )
        assert factor("RIGHTS", p, c.Policy("VOLUME")).volume_factor == 1
    elif case == "dividend-volume":
        assert (
            factor(
                "DIVIDEND_SPECIAL",
                c.Dividend(Decimal(5), "MATH_UNIT", None, None),
                c.Policy("VOLUME"),
            ).volume_factor
            == 1
        )
    elif case == "no-partial-ledger":
        db = AdjustmentRepository("sqlite:///:memory:", disposable_root=tmp_path)
        with pytest.raises(ValueError):
            db.append_result(chain((replace(a, parameters=c.Split(Decimal(0))),)), ())
    elif case == "result-payload-binding":
        db = AdjustmentRepository("sqlite:///:memory:", disposable_root=tmp_path)
        db.append_action(replace(a, parameters=c.Split(Decimal(3))))
        with pytest.raises(ValueError):
            db.append_result(chain(), ("a",))
    elif case == "quantum-bound":
        with pytest.raises(ValueError):
            c.Policy("PRICE_RETURN", price_quantum=Decimal("0.01"))
    elif case == "context-precision":
        with localcontext() as decimal_context:
            decimal_context.prec = 5
            result = chain()
        assert result.adjusted_price == Decimal("60.000000")


def test_legacy_risk_reproduction():
    """Observe frozen legacy behavior; no real symbols/observations or operational DB."""
    from types import SimpleNamespace

    from omegadata.domain import ConfidenceLevel, CorporateActionType, Exchange
    from omegadata.track_b.adjustment_engine import PriceAdjustmentEngine

    action = SimpleNamespace(
        action_type=CorporateActionType.RIGHTS,
        ex_date=D,
        parameters={
            "rights_ratio_denominator": "4",
            "rights_ratio_numerator": "1",
            "issue_price": None,
        },
        confidence=ConfidenceLevel.MEDIUM,
        source_preference=Exchange.NSE,
    )
    old = PriceAdjustmentEngine()._compute_factor(
        action, {D - timedelta(days=1): SimpleNamespace(close_price=Decimal(100))}
    )
    assert (
        old.price_factor == Decimal(".8")
        and old.metadata["subscription_price_fallback_zero"] is True
    )
    assert (
        PriceAdjustmentEngine()._compute_factor(
            action, {D - timedelta(days=3): SimpleNamespace(close_price=Decimal(100))}
        )
        is None
    )


@pytest.mark.parametrize(
    "case",
    [
        "future-ledger-stability",
        "persisted-price-tamper",
        "persisted-factor-tamper",
        "partial-result",
        "duplicate-event-economic-key",
        "reverse-direction-type",
        "reference-identity",
        "profile-volume-rights",
        "large-result-refusal",
        "competing-file-writers",
    ],
)
def test_final_integrity(case, tmp_path):
    from omegadata.adjustments.repository import AdjustmentRepository

    c, x, a, r = system()
    if case == "future-ledger-stability":
        b = replace(
            a,
            action_id="b",
            supersedes_action_id="a",
            action_revision=2,
            known_from=K + timedelta(days=10),
        )
        early = replace(x, known_at=K + timedelta(days=9))
        assert chain((a,), ctx=early).output_digest == chain((a, b), ctx=early).output_digest
    elif case == "persisted-price-tamper":
        db = AdjustmentRepository("sqlite:///:memory:", disposable_root=tmp_path)
        db.append_action(a)
        with pytest.raises(ValueError):
            db.append_result(replace(chain(), adjusted_price=Decimal(999)), ("a",))
    elif case == "persisted-factor-tamper":
        db = AdjustmentRepository("sqlite:///:memory:", disposable_root=tmp_path)
        db.append_action(a)
        out = chain()
        link = replace(
            out.adjustment_factor_chain[0],
            factor=replace(out.adjustment_factor_chain[0].factor, numerator=Decimal(9)),
        )
        with pytest.raises(ValueError):
            db.append_result(replace(out, adjustment_factor_chain=(link,)), ("a",))
    elif case == "partial-result":
        with pytest.raises(ValueError):
            c.Result("CALCULATED", "bad")
    elif case == "duplicate-event-economic-key":
        # Two separate revisions must have explicit ordering; economic uniqueness is not guessed.
        b = replace(a, action_id="b")
        assert chain((a, b)).status == "CONFLICTING_ACTIONS"
    elif case == "reverse-direction-type":
        from omegadata.adjustments.factors import factor

        assert (
            factor("SPLIT_REVERSE", c.Split(Decimal(2)), c.Policy("PRICE_RETURN")).status
            == "INVALID_PARAMETERS"
        )
    elif case == "reference-identity":
        p = c.Rights(
            Decimal(4),
            Decimal(1),
            Decimal(50),
            c.Reference(Decimal(100), D - timedelta(days=3), K, "", "MATH_UNIT"),
            "MATH_UNIT",
            True,
        )
        assert (
            chain((replace(a, action_type="RIGHTS", parameters=p),)).status == "INVALID_PARAMETERS"
        )
    elif case == "profile-volume-rights":
        from omegadata.adjustments.factors import factor

        p = c.Rights(
            Decimal(4),
            Decimal(1),
            Decimal(50),
            c.Reference(Decimal(100), D, K, "ref", "MATH_UNIT"),
            "MATH_UNIT",
            True,
        )
        assert factor("RIGHTS", p, c.Policy("VOLUME")).volume_factor == 1
    elif case == "large-result-refusal":
        many = tuple(
            replace(
                a, action_id=str(i), ex_date=D, sequence=i, parameters=c.Split(Decimal("1e-64"))
            )
            for i in range(100)
        )
        assert chain(many).status == "INVALID_PARAMETERS"
    elif case == "competing-file-writers":
        import concurrent.futures
        import threading

        url = "sqlite:///" + str(tmp_path / "writers.sqlite")
        db = AdjustmentRepository(url, disposable_root=tmp_path)
        db.append_action(a)
        other = AdjustmentRepository(url, disposable_root=tmp_path)
        barrier = threading.Barrier(2)

        def attempt(repo, name):
            barrier.wait()
            try:
                repo.append_action(
                    replace(
                        a,
                        action_id=name,
                        supersedes_action_id="a",
                        action_revision=2,
                        known_from=K + timedelta(days=1),
                    )
                )
                return "COMMITTED"
            except ValueError:
                return "REFUSED"

        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            one = pool.submit(attempt, db, "b")
            two = pool.submit(attempt, other, "c")
            assert sorted((one.result(), two.result())) == ["COMMITTED", "REFUSED"]
        assert len(db.history("a")) == 2


@pytest.mark.parametrize(
    "case",
    ["native-foreign-key", "unrelated-schema", "persisted-order", "source-correction-rollback"],
)
def test_sql_and_chain_integrity(case, tmp_path):
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import IntegrityError

    from omegadata.adjustments.repository import AdjustmentRepository

    c, x, a, r = system()
    if case == "unrelated-schema":
        url = "sqlite:///" + str(tmp_path / "unrelated.sqlite")
        engine = create_engine(url)
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE unrelated(id INTEGER PRIMARY KEY)"))
        engine.dispose()
        with pytest.raises(ValueError):
            AdjustmentRepository(url, disposable_root=tmp_path)
        return
    db = AdjustmentRepository("sqlite:///:memory:", disposable_root=tmp_path)
    db.append_action(a)
    if case == "native-foreign-key":
        with pytest.raises(IntegrityError), db.transaction() as connection:
            connection.execute(
                text(
                    "INSERT INTO od07_action(id,parent,payload,digest) VALUES ('bad','absent','x','x')"
                )
            )
        assert db.action_ids() == ("a",)
    elif case == "persisted-order":
        b = replace(a, action_id="b", ex_date=D + timedelta(days=1), parameters=c.Split(Decimal(3)))
        db.append_action(b)
        out = chain((a, b))
        with pytest.raises(ValueError):
            db.append_result(
                replace(out, adjustment_factor_chain=tuple(reversed(out.adjustment_factor_chain))),
                ("a", "b"),
            )
    elif case == "source-correction-rollback":
        b = replace(
            a,
            action_id="b",
            supersedes_action_id="a",
            action_revision=2,
            known_from=K + timedelta(days=1),
        )
        bad = replace(b, security_id="other")
        with pytest.raises(ValueError):
            db.append_action(bad)
        assert db.history("a") == (a,)


def test_decimal_environment_isolation():
    """Ambient Decimal traps and rounding must not alter version-pinned math."""
    from decimal import ROUND_DOWN, Inexact

    c, x, a, r = system()
    b = replace(a, action_type="BONUS", parameters=c.Bonus(Decimal(1), Decimal(2)))
    ordinary = chain((b,))
    with localcontext() as environment:
        environment.traps[Inexact] = True
        environment.rounding = ROUND_DOWN
        controlled = chain((b,))
    assert controlled.status == "CALCULATED"
    assert controlled.output_digest == ordinary.output_digest
