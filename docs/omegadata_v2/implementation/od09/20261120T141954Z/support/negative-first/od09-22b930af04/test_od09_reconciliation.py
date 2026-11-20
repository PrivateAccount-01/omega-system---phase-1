"""OD09 NON_MARKET_STRUCTURAL_CONTROL / PURE_MATHEMATICAL_TEST only."""

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal, localcontext

import pytest
from test_od08_universe import D, K, observation, setup_case


def controls(**kw):
    from omegadata.reconciliation import contracts as c

    _, x, member, coverage, policy, _ = setup_case()
    a = observation(x, observation_id="left", price_value=Decimal(2))
    b = replace(
        a,
        observation_id="right",
        artifact_identity="right-artifact",
        record_identity="right-row",
        price_value=Decimal(2),
    )
    left = c.Observation(
        a,
        "security-a",
        "CANARY-X",
        "TOKEN",
        "SERIES",
        "publisher-a",
        "parse-v1",
        "schema-v1",
        1,
        "close",
        Decimal(2),
        "CONTROL_ONLY",
        "root-a",
    )
    right = c.Observation(
        b,
        "security-a",
        "CANARY-X",
        "TOKEN",
        "SERIES",
        "publisher-b",
        "parse-v1",
        "schema-v1",
        1,
        "close",
        Decimal(2),
        "CONTROL_ONLY",
        "root-b",
    )
    tolerance = c.TolerancePolicy(
        "policy",
        "v1",
        ("control-source", "control-source"),
        "SAME_VENUE",
        "CONTROL_ONLY",
        "close",
        ("CANARY-X",),
        "ABSOLUTE",
        Decimal("0.1"),
        Decimal("0.2"),
        "CONTROL_UNIT",
        "CONTROL_ONLY",
        K,
        D,
        None,
        "NON_MARKET_MATH_CONTROL",
    )
    context = c.ComparisonContext("comparison", (left,), (right,), tolerance, x, D, K)
    return c, replace(context, **kw), left, right


GROUPS = [
    f"{p}{i:02}"
    for p, n in [("C", 8), ("M", 4), ("T", 3), ("N", 5), ("G", 4), ("R", 6), ("P", 4), ("S", 3)]
    for i in range(1, n + 1)
]


@pytest.mark.parametrize("group", GROUPS)
def test_od09_acceptance(group, tmp_path):
    from omegadata.reconciliation.anomalies import (
        discontinuity,
        persistent_discrepancy,
        structural_anomalies,
    )
    from omegadata.reconciliation.engine import (
        comparability,
        eligibility,
        reconcile_context,
    )
    from omegadata.reconciliation.metrics import difference
    from omegadata.reconciliation.repository import ReconciliationRepository
    from omegadata.reconciliation.reviews import (
        ReprocessCompletion,
        ReprocessRequest,
        ReviewRevision,
        advance_review,
        verify_completion,
    )

    c, x, left, right = controls()
    if group == "C01":
        assert reconcile_context(x)[0].outcome == "PASS"
    elif group == "C02":
        assert (
            reconcile_context(replace(x, right=(replace(right, security_id="other"),)))[0].outcome
            == "UNCOMPARABLE"
        )
    elif group == "C03":
        other = replace(
            right,
            exchange="OTHER",
            availability=replace(right.availability, listing_id="other-listing"),
        )
        assert comparability(left, other, x)[0] == "SAME_SECURITY_DIFFERENT_VENUE"
    elif group == "C04":
        assert (
            reconcile_context(
                replace(
                    x,
                    right=(
                        replace(
                            right, availability=replace(right.availability, price_basis="OTHER")
                        ),
                    ),
                )
            )[0].outcome
            == "UNCOMPARABLE"
        )
    elif group == "C05":
        assert (
            reconcile_context(
                replace(
                    x,
                    right=(
                        replace(
                            right,
                            availability=replace(
                                right.availability, session_date=D + timedelta(days=1)
                            ),
                        ),
                    ),
                )
            )[0].outcome
            == "UNCOMPARABLE"
        )
    elif group == "C06":
        assert reconcile_context(replace(x, right=()))[0].comparability == "MISSING_COUNTERPART"
        assert (
            reconcile_context(
                replace(
                    x,
                    right=(
                        right,
                        replace(
                            right,
                            availability=replace(right.availability, observation_id="duplicate"),
                        ),
                    ),
                )
            )[0].comparability
            == "CONFLICTING_COUNTERPARTS"
        )
    elif group == "C07":
        assert (
            "DEPENDENT_SOURCE_LINEAGE"
            in reconcile_context(replace(x, right=(replace(right, source_lineage_root="root-a"),)))[
                0
            ].reason_codes
        )
    elif group == "C08":
        assert (
            reconcile_context(
                replace(
                    x,
                    right=(
                        replace(
                            right,
                            availability=replace(
                                right.availability, known_from=K + timedelta(seconds=1)
                            ),
                        ),
                    ),
                )
            )[0].outcome
            == "UNCOMPARABLE"
        )
    elif group == "M01":
        assert difference(Decimal(3), Decimal(2), "REFERENCE_RELATIVE").exact_ratio == (1, 2)
    elif group == "M02":
        assert (
            difference(Decimal(1), Decimal(0), "REFERENCE_RELATIVE").status
            == "UNDEFINED_DENOMINATOR"
        )
    elif group == "M03":
        for v, status in [("2.1", "PASS"), ("2.15", "WARN"), ("2.2", "FAIL")]:
            r = replace(
                right,
                value=Decimal(v),
                availability=replace(right.availability, price_value=Decimal(v)),
            )
            assert reconcile_context(replace(x, right=(r,)))[0].outcome == status
    elif group == "M04":
        values = []
        for prec in (5, 28, 90):
            with localcontext() as ctx:
                ctx.prec = prec
                values.append(difference(Decimal(1), Decimal(3), "REFERENCE_RELATIVE"))
        assert values[0] == values[1] == values[2]
    elif group == "T01":
        assert reconcile_context(x)[0].policy_digest == c.fingerprint(x.policy)
    elif group == "T02":
        assert (
            reconcile_context(
                replace(
                    x, policy=replace(x.policy, calibration_knowledge_cutoff=K + timedelta(days=1))
                )
            )[0].outcome
            == "UNCOMPARABLE"
        )
    elif group == "T03":
        assert not reconcile_context(x)[0].financial_eligibility
    elif group == "N01":
        assert structural_anomalies(
            {
                "open": Decimal(2),
                "close": Decimal(2),
                "high": Decimal(1),
                "low": Decimal(0),
                "volume": Decimal(0),
            },
            ohlc_semantics="STANDARD",
        ) == ("STRUCTURAL_INVALIDITY",)
    elif group == "N02":
        # No caller-asserted boolean can stand in for a bound corporate-action reference.
        assert discontinuity(left, right, x, Decimal("0.1"), None) == "NO_DISCONTINUITY"
    elif group == "N03":
        r = replace(
            right,
            value=Decimal(4),
            availability=replace(right.availability, price_value=Decimal(4)),
        )
        assert discontinuity(left, r, x, Decimal("0.1"), None) == "UNEXPLAINED_DISCONTINUITY"
    elif group == "N04":
        assert (
            comparability(left, replace(right, exchange="OTHER"), x)[0]
            == "SAME_SECURITY_DIFFERENT_VENUE"
        )
    elif group == "N05":
        assert (
            persistent_discrepancy(
                (Decimal(1), Decimal(2), Decimal(3)), Decimal("0.5"), minimum_samples=3
            )
            == "PERSISTENT_DIRECTIONAL_DISCREPANCY"
        )
    elif group in {"G01", "G02", "G03", "G04"}:
        block = {
            "G01": "SOURCE_RIGHTS_DENIED",
            "G02": "UNKNOWN_IDENTITY",
            "G03": "UNRESOLVED_CRITICAL_ANOMALY",
            "G04": "UNCOMPARABLE",
        }[group]
        decision = eligibility(Decimal(1), "PASS", (block,), mode="CANARY_ONLY")
        assert (
            not decision.financial_eligibility
            and not decision.publication_eligibility
            and not decision.execution_eligibility
            and block in decision.hard_block_reasons
        )
    elif group.startswith("R"):
        review = ReviewRevision(
            "rev-a",
            "review",
            "discrepancy",
            "OPEN",
            K,
            "data-review",
            ("source-a",),
            "review-v1",
            None,
            ("listing-a",),
            "CRITICAL",
        )
        if group == "R01":
            nxt = advance_review(
                review,
                "UNDER_REVIEW",
                "rev-b",
                K + timedelta(seconds=1),
                "anonymous-reviewer",
                "reason",
                (),
                mode="CANARY_ONLY",
            )
            assert review.state == "OPEN" and nxt.previous_record_digest == c.fingerprint(review)
        elif group == "R02":
            with pytest.raises(ValueError):
                advance_review(
                    review, "CLOSED", "rev-b", K, "anonymous", "reason", (), mode="CANARY_ONLY"
                )
        elif group == "R03":
            review = replace(review, state="UNDER_REVIEW")
            with pytest.raises(ValueError):
                advance_review(
                    review,
                    "CORRECTION_PROPOSED",
                    "rev-b",
                    K,
                    "anonymous",
                    "reason",
                    (),
                    mode="CANARY_ONLY",
                )
        elif group == "R04":
            review = replace(review, state="CORRECTION_PROPOSED")
            with pytest.raises(ValueError, match="AUTHORITY"):
                advance_review(
                    review,
                    "APPROVED",
                    "rev-b",
                    K,
                    "forged-reviewer",
                    "reason",
                    ("new-evidence",),
                    mode="STRICT",
                )
        else:
            req = ReprocessRequest(
                "request",
                "correction",
                ("listing-a",),
                (D,),
                ("raw-v2",),
                ("adjusted-v2",),
                ("universe-v2",),
                ("result-v2",),
                (("policy", "v1"),),
            )
            actual = ReprocessCompletion(
                "completion",
                "request",
                c.fingerprint(req),
                "correction",
                ("raw-v2",),
                ("adjusted-v2",),
                ("universe-v2",),
                ("result-v2",),
                (("policy", "v1"),),
                "COMPLETED_UNVERIFIED",
                ("completion-evidence",),
            )
            if group == "R05":
                assert req.request_digest == c.fingerprint(req)
            else:
                assert verify_completion(req, actual, mode="CANARY_ONLY") == "COMPLETED_UNVERIFIED"
                assert (
                    verify_completion(
                        req, replace(actual, affected_reconciliation_results=()), mode="CANARY_ONLY"
                    )
                    == "BLOCKED_DEPENDENCY"
                )
    elif group.startswith("P"):
        url = (
            "sqlite:///:memory:"
            if group != "P03"
            else "sqlite:///" + str(tmp_path / "reconciliation.sqlite")
        )
        db = ReconciliationRepository(url, disposable_root=tmp_path)
        db.pin_comparison(x)
        results = reconcile_context(x)
        if group == "P01":
            db.admit_results(x.context_id, results)
            db.admit_results(x.context_id, results)
            with pytest.raises(ValueError):
                db.admit_results(x.context_id, (replace(results[0], outcome="FAIL"),))
        elif group == "P02":
            later = replace(x, context_id="later", known_at=K + timedelta(days=1))
            db.pin_comparison(later)
            assert db.replay(x.context_id) == results
        elif group == "P03":
            db.admit_results(x.context_id, results)
            db.close()
            db = ReconciliationRepository(url, disposable_root=tmp_path)
            assert db.replay(x.context_id) == results
            with pytest.raises(ValueError):
                db.rollback_empty()
        else:
            with pytest.raises(ValueError):
                db.pin_comparison(replace(x, known_at=K + timedelta(days=1)))
        db.close()
    elif group == "S01":
        assert not reconcile_context(x)[0].financial_eligibility
    elif group == "S02":
        import od05x_isolated_runner

        assert od05x_isolated_runner.assert_boundary()["verified"]
    elif group == "S03":
        from omegadata.track_b.confidence import ConfidenceScorer

        assert ConfidenceScorer.THRESHOLDS


@pytest.mark.parametrize(
    "metric,left,right,expected",
    [
        ("ABSOLUTE", "3", "2", (1, 1)),
        ("SIGNED", "2", "3", (-1, 1)),
        ("REFERENCE_RELATIVE", "1", "3", (2, 3)),
        ("SYMMETRIC_RELATIVE", "3", "1", (1, 1)),
        ("RATIO_DIFFERENCE", "3", "2", (1, 2)),
        ("TICK", "3", "2", (4, 1)),
    ],
)
def test_literal_metric_oracle(metric, left, right, expected):
    from omegadata.reconciliation.metrics import difference

    assert (
        difference(Decimal(left), Decimal(right), metric, tick=Decimal("0.25")).exact_ratio
        == expected
    )


@pytest.mark.parametrize("mode", ["memory", "file"])
def test_review_persistence_and_competing_children(mode, tmp_path):
    from sqlalchemy.exc import IntegrityError

    from omegadata.reconciliation.engine import reconcile_context
    from omegadata.reconciliation.repository import ReconciliationRepository
    from omegadata.reconciliation.reviews import ReviewRevision, advance_review

    c, x, left, right = controls()
    url = (
        "sqlite:///:memory:"
        if mode == "memory"
        else "sqlite:///" + str(tmp_path / "reviews.sqlite")
    )
    db = ReconciliationRepository(url, disposable_root=tmp_path)
    db.pin_comparison(x)
    result = reconcile_context(x)[0]
    db.admit_results(x.context_id, (result,))
    root = ReviewRevision(
        "r0",
        "review",
        result.reconciliation_id,
        "OPEN",
        K,
        "data-review",
        ("original",),
        "review-v1",
        None,
        ("listing-a",),
        "CRITICAL",
    )
    db.append_review(root)
    child = advance_review(
        root,
        "UNDER_REVIEW",
        "r1",
        K + timedelta(seconds=1),
        "anonymous",
        "structural review",
        (),
        mode="CANARY_ONLY",
    )
    db.append_review(child)
    db.append_review(child)
    other = replace(child, revision_id="competing")
    with pytest.raises((ValueError, IntegrityError)):
        db.append_review(other)
    assert len(db.get_review_history("review")) == 2
    if mode == "file":
        db.close()
        db = ReconciliationRepository(url, disposable_root=tmp_path)
        assert db.get_review_history("review") == (root, child)
    db.close()


def test_review_scope_cannot_target_unrelated_listing(tmp_path):
    from omegadata.reconciliation.engine import reconcile_context
    from omegadata.reconciliation.repository import ReconciliationRepository
    from omegadata.reconciliation.reviews import ReviewRevision

    c, x, left, right = controls()
    db = ReconciliationRepository("sqlite:///:memory:", disposable_root=tmp_path)
    db.pin_comparison(x)
    result = reconcile_context(x)[0]
    db.admit_results(x.context_id, (result,))
    root = ReviewRevision(
        "r0",
        "review",
        result.reconciliation_id,
        "OPEN",
        K,
        "data-review",
        ("original",),
        "v",
        None,
        ("unrelated-listing",),
        "CRITICAL",
    )
    with pytest.raises(ValueError, match="SCOPE"):
        db.append_review(root)


def test_anomaly_admission_cannot_accept_arbitrary_claim(tmp_path):
    from omegadata.reconciliation.repository import ReconciliationRepository

    c, x, left, right = controls()
    db = ReconciliationRepository("sqlite:///:memory:", disposable_root=tmp_path)
    db.pin_comparison(x)
    with pytest.raises(ValueError):
        db.append_anomaly("made-up", x.context_id, {"status": "APPROVED"})


@pytest.mark.parametrize(
    "case",
    [
        "missing",
        "wrong_scope",
        "wrong_policy",
        "wrong_cutoff",
        "wrong_source",
        "different_context",
        "omitted_result",
    ],
)
def test_independent_persisted_admission(case, tmp_path):
    from omegadata.reconciliation.engine import reconcile_context
    from omegadata.reconciliation.repository import ReconciliationRepository

    c, x, left, right = controls()
    db = ReconciliationRepository("sqlite:///:memory:", disposable_root=tmp_path)
    db.pin_comparison(x)
    out = reconcile_context(x)
    if case == "missing":
        out = ()
    elif case == "wrong_scope":
        out = (replace(out[0], left_observation_ids=("other",)),)
    elif case == "wrong_policy":
        out = (replace(out[0], policy_digest="forged"),)
    elif case == "wrong_cutoff":
        out = (replace(out[0], known_at=K + timedelta(seconds=1)),)
    elif case == "wrong_source":
        out = (replace(out[0], left_observation_digests=("forged",)),)
    elif case == "different_context":
        out = (replace(out[0], context_id="other"),)
    else:
        out = (replace(out[0], right_observation_ids=()),)
    with pytest.raises(ValueError):
        db.admit_results(x.context_id, out)
    assert db.replay(x.context_id) == reconcile_context(x)


@pytest.mark.parametrize(
    "reason",
    [
        "SOURCE_RIGHTS_DENIED",
        "UNKNOWN_IDENTITY",
        "WRONG_PRICE_BASIS",
        "FUTURE_INFORMATION",
        "UNRESOLVED_CRITICAL_ANOMALY",
        "INCOMPLETE_REQUIRED_HISTORY",
        "UNVERIFIED_CORRECTION",
        "REPROCESS_NOT_COMPLETED",
    ],
)
def test_confidence_never_overrides_hard_requirement(reason):
    from omegadata.reconciliation.engine import eligibility

    out = eligibility(Decimal(1), "PASS", (reason,))
    assert reason in out.hard_block_reasons and not out.financial_eligibility


def test_candidate_accounting_no_cartesian_overwrite():
    from omegadata.reconciliation.engine import reconcile_context

    c, x, left, right = controls()
    duplicate = replace(
        right, availability=replace(right.availability, observation_id="right-duplicate")
    )
    outputs = reconcile_context(replace(x, right=(right, duplicate)))
    assert len(outputs) == 1 and outputs[0].right_observation_ids == ("right", "right-duplicate")
    assert outputs[0].outcome == "UNCOMPARABLE"


def test_pure_calibration_independent_literal_answers():
    from omegadata.reconciliation.tolerances import CalibrationSample, calibrate

    rows = (
        CalibrationSample("a", ("a", "b"), Decimal(1), K, "TRAIN", "control", independent=True),
        CalibrationSample("b", ("c", "d"), Decimal(2), K, "TRAIN", "control", independent=True),
        CalibrationSample("c", ("e", "f"), Decimal(3), K, "VALIDATION", "control", False, True),
    )
    result = calibrate(rows, K, minimum_samples=2, liquidity_bucket="control")
    assert result.warning_threshold == Decimal(2) and result.failure_threshold == Decimal(2)
    assert (
        result.false_positive_count == 1
        and result.false_negative_count == 0
        and result.authenticity == "BLOCKED_CALIBRATION"
    )
    with pytest.raises(ValueError):
        calibrate(rows + (rows[0],), K, minimum_samples=2, liquidity_bucket="control")
    assert (
        calibrate(
            tuple(replace(v, known_from=K + timedelta(days=1)) for v in rows),
            K,
            minimum_samples=2,
            liquidity_bucket="control",
        ).status
        == "BLOCKED_SAMPLE_ADEQUACY"
    )


def test_sql_atomic_rollback_and_foreign_key(tmp_path):
    from sqlalchemy import func, select
    from sqlalchemy.exc import IntegrityError

    from omegadata.reconciliation import repository as r

    c, x, left, right = controls()
    db = r.ReconciliationRepository("sqlite:///:memory:", disposable_root=tmp_path)
    with pytest.raises(ValueError), db.transaction() as con:
        db._put(con, r.policies, "rolled-back", x.policy)
        raise ValueError("interruption")
    with db.transaction() as con:
        assert con.scalar(select(func.count()).select_from(r.policies)) == 0
    with pytest.raises(IntegrityError), db.transaction() as con:
        db._put(con, r.results, "orphan", {}, context="absent")
    db.rollback_empty()
    assert not r.inspect(db.engine).get_table_names()


def correction_case(tmp_path):
    from omegadata.reconciliation.engine import reconcile_context
    from omegadata.reconciliation.repository import ReconciliationRepository
    from omegadata.reconciliation.reviews import CorrectionRevision, ReviewRevision, advance_review

    c, x, left, right = controls()
    db = ReconciliationRepository("sqlite:///:memory:", disposable_root=tmp_path)
    db.pin_comparison(x)
    result = reconcile_context(x)[0]
    db.admit_results(x.context_id, (result,))
    changed = replace(
        left,
        value=Decimal(3),
        availability=replace(
            left.availability,
            observation_id="corrected-left",
            record_identity="corrected-record",
            price_value=Decimal(3),
            known_from=K + timedelta(seconds=2),
        ),
    )
    root = ReviewRevision(
        "r0",
        "review",
        result.reconciliation_id,
        "OPEN",
        K,
        "data-review",
        ("original",),
        "v",
        None,
        ("listing-a",),
        "CRITICAL",
    )
    db.append_review(root)
    current = root
    for i, state in enumerate(("UNDER_REVIEW", "CORRECTION_PROPOSED", "APPROVED"), 1):
        current = advance_review(
            current,
            state,
            "r" + str(i),
            K + timedelta(seconds=i),
            "anonymous-reviewer",
            "NON_MARKET_STATE_CONTROL",
            ("canary-evidence-" + str(i),),
            mode="CANARY_ONLY",
            proposed_revision_digest=c.fingerprint(changed),
        )
        db.append_review(current)
    correction = CorrectionRevision(
        "correction",
        current.revision_id,
        c.fingerprint(left),
        c.fingerprint(changed),
        ("listing-a",),
        ("canary-evidence-3",),
        K + timedelta(seconds=4),
    )
    db.append_correction(correction)
    newcontext = replace(
        x, context_id="corrected-context", left=(changed,), known_at=K + timedelta(seconds=5)
    )
    return c, db, x, newcontext, correction


def test_reprocess_refuses_unchanged_old_output_identity(tmp_path):
    c, db, x, newcontext, correction = correction_case(tmp_path)
    with pytest.raises(ValueError, match="REPLACEMENT"):
        db.derive_reprocess_request("request", correction.correction_id)


def test_reprocess_exact_replacement_and_false_verified_refusal(tmp_path):
    from omegadata.reconciliation.engine import reconcile_context
    from omegadata.reconciliation.reviews import ReprocessCompletion

    c, db, x, newcontext, correction = correction_case(tmp_path)
    db.pin_comparison(newcontext)
    db.admit_results(newcontext.context_id, reconcile_context(newcontext))
    db.pin_replacement_context(correction.correction_id, x.context_id, newcontext.context_id)
    req = db.derive_reprocess_request("request", correction.correction_id)
    db.append_reprocess_request(req)
    assert (
        req.expected_output_identities
        and req.expected_output_identities[0][0] != reconcile_context(x)[0].reconciliation_id
    )
    completion = ReprocessCompletion(
        "completion",
        "request",
        req.request_digest,
        req.approved_correction_id,
        req.source_record_revisions,
        req.affected_adjustment_outputs,
        req.affected_universe_snapshots,
        req.affected_reconciliation_results,
        req.required_dependency_versions,
        "COMPLETED_UNVERIFIED",
        ("canary-completion",),
        output_identities=req.expected_output_identities,
    )
    assert db.append_completion(completion) == "COMPLETED_UNVERIFIED"
    with pytest.raises(ValueError):
        db.append_completion(replace(completion, completion_id="forged", state="VERIFIED"))
    with pytest.raises(ValueError):
        db.append_completion(replace(completion, completion_id="wrong", output_identities=()))


def test_context_identity_computed_once_per_reconciliation(monkeypatch):
    from omegadata.reconciliation.engine import reconcile_context

    c, x, left, right = controls()
    rows = tuple(
        replace(
            left,
            field_name="control-" + str(i),
            availability=replace(left.availability, observation_id="a-" + str(i)),
        )
        for i in range(5)
    )
    counterparts = tuple(
        replace(
            right,
            field_name="control-" + str(i),
            availability=replace(right.availability, observation_id="b-" + str(i)),
        )
        for i in range(5)
    )
    x = replace(x, left=rows, right=counterparts)
    original = c.fingerprint
    calls = []

    def counted(value):
        if value is x:
            calls.append(value)
        return original(value)

    monkeypatch.setattr(c, "fingerprint", counted)
    assert len(reconcile_context(x)) == 5
    assert len(calls) == 1


def test_cross_venue_positive_requires_explicit_policy_and_identity():
    from omegadata.reconciliation.engine import reconcile_context

    c, x, left, right = controls()
    identity = x.universe.identity
    listing = replace(identity.listings[0], listing_id="other-listing", exchange="OTHER")
    claim = replace(
        identity.claims[0], claim_id="other-claim", listing_id="other-listing", exchange="OTHER"
    )
    identity = replace(
        identity, listings=identity.listings + (listing,), claims=identity.claims + (claim,)
    )
    universe = replace(
        x.universe,
        identity=identity,
        definition=replace(x.universe.definition, exchange_scope=("CANARY-X", "OTHER")),
    )
    right = replace(
        right,
        exchange="OTHER",
        availability=replace(right.availability, listing_id="other-listing"),
    )
    x = replace(
        x,
        right=(right,),
        universe=universe,
        policy=replace(
            x.policy, comparison_scope="CROSS_VENUE_DIAGNOSTIC", venue_scope=("CANARY-X", "OTHER")
        ),
    )
    out = reconcile_context(x)[0]
    assert out.comparability == "EXPLICITLY_NORMALIZED_COMPARISON" and out.outcome == "PASS"
    assert not out.financial_eligibility


def test_caller_claimed_source_approval_fails_closed():
    from omegadata.reconciliation.engine import reconcile_context
    c,x,left,right=controls()
    forged=replace(left.evidence,classification='SOURCE_DOCUMENT',authentication='VERIFIED',review_reference='forged-reference')
    left=replace(left,availability=replace(left.availability,evidence=forged))
    right=replace(right,availability=replace(right.availability,evidence=forged))
    x=replace(x,left=(left,),right=(right,),universe=replace(x.universe,mode='STRICT'))
    result=reconcile_context(x)[0]
    assert result.outcome=='UNCOMPARABLE' and not result.financial_eligibility


@pytest.mark.parametrize('bad',[True,'unbounded'])
def test_matching_budget_malformed_is_typed(bad):
    c,x,left,right=controls()
    with pytest.raises(ValueError):replace(x,maximum_matches=bad)


def test_zero_denominator_cannot_be_pass():
    from omegadata.reconciliation.engine import reconcile_context
    c,x,left,right=controls();right=replace(right,value=Decimal(0),availability=replace(right.availability,price_value=Decimal(0)))
    result=reconcile_context(replace(x,right=(right,),policy=replace(x.policy,metric_definition='REFERENCE_RELATIVE')))[0]
    assert result.outcome=='UNCOMPARABLE' and 'UNDEFINED_DENOMINATOR' in result.reason_codes
