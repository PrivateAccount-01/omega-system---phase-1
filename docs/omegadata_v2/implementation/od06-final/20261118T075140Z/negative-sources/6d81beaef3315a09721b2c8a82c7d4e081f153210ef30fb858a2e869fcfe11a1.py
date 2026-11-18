"""Foundation acceptance: anonymous NON_MARKET_CANARY invariants only."""

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from test_od06_contracts import calendar_system, resolve, system

D = date(2001, 1, 1)
K = datetime(2001, 1, 1, tzinfo=UTC)


def store(tmp_path, mode):
    from omegadata.identity_repository import PersistentRepository

    url = (
        "sqlite+pysqlite:///:memory:"
        if mode == "memory"
        else "sqlite+pysqlite:///" + str(tmp_path / "canary.sqlite")
    )
    return PersistentRepository(url, disposable_root=tmp_path)


def seed(db):
    _, _, r, c = system()
    db.append_entities(r.issuers, r.securities, r.listings)
    db.append_identity_claim(c)
    return r, c


@pytest.mark.parametrize("mode", ["memory", "file"])
@pytest.mark.parametrize(
    "case",
    [
        "insert",
        "duplicate",
        "idempotent",
        "restart",
        "correction-chain",
        "rollback",
        "foreign-key",
        "overlap",
        "immutable",
        "version",
        "competing",
        "migration",
        "history",
        "event",
        "calendar",
    ],
)
def test_persistence(tmp_path, mode, case):
    from omegadata.identity_repository import PersistentRepository

    db = store(tmp_path, mode)
    r, c = seed(db)
    if case == "insert":
        assert (
            db.resolve_listing("CANARY-X", "TOKEN", "SERIES", D, K, "CANARY_ONLY").state
            == "RESOLVED"
        )
        assert len(db.get_identity_history("listing-a")) == 1
    elif case == "duplicate":
        with pytest.raises(ValueError):
            db.append_identity_claim(c)
    elif case == "idempotent":
        db.append_identity_claim(c, idempotent=True)
        with pytest.raises(ValueError):
            db.append_identity_claim(replace(c, symbol="OTHER"), idempotent=True)
        assert len(db.get_identity_history("listing-a")) == 1
    elif case == "restart":
        before = db.serialize_history()
        if mode == "file":
            url = db.url
            db.close()
            db = PersistentRepository(url, disposable_root=tmp_path)
        else:
            db.reconnect()
        assert before == db.serialize_history()
    elif case == "correction-chain":
        b = replace(
            c,
            claim_id="b",
            symbol="TOKEN-B",
            known_from=K + timedelta(days=1),
            supersedes_claim_id="claim-a",
        )
        cc = replace(
            b,
            claim_id="c",
            symbol="TOKEN-C",
            known_from=K + timedelta(days=2),
            supersedes_claim_id="b",
        )
        db.append_identity_correction(b)
        db.append_identity_correction(cc)
        assert len(db.get_claim_revisions("b")) == 3
        assert (
            db.resolve_listing("CANARY-X", "TOKEN", "SERIES", D, K, "CANARY_ONLY").state
            == "RESOLVED"
        )
        assert (
            db.resolve_listing(
                "CANARY-X", "TOKEN-B", "SERIES", D, cc.known_from, "CANARY_ONLY"
            ).state
            == "UNKNOWN"
        )
    elif case == "rollback":
        before = db.serialize_history()
        b = replace(
            c, claim_id="b", known_from=K + timedelta(days=1), supersedes_claim_id="claim-a"
        )
        with pytest.raises(RuntimeError):
            db.append_identity_correction(b, _interrupt_after_insert=True)
        db.reconnect()
        assert db.serialize_history() == before
        assert db.get_claim_revisions("claim-a") == (c,)
    elif case == "foreign-key":
        with pytest.raises(ValueError):
            db.append_identity_claim(replace(c, claim_id="orphan", listing_id="missing"))
        with pytest.raises(IntegrityError):
            db.native_foreign_key_probe()
        assert len(db.get_identity_history("listing-a")) == 1
    elif case == "overlap":
        db.append_identity_claim(replace(c, claim_id="overlap"))
        assert db.validate_identity_consistency()
        assert (
            db.resolve_listing("CANARY-X", "TOKEN", "SERIES", D, K, "CANARY_ONLY").state
            == "AMBIGUOUS"
        )
    elif case == "immutable":
        with pytest.raises(IntegrityError):
            db.native_mutation_probe("update")
        with pytest.raises(IntegrityError):
            db.native_mutation_probe("delete")
    elif case == "version":
        with pytest.raises(ValueError):
            db.get_identity_history("listing-a", version="future")
    elif case == "competing":
        b = replace(
            c, claim_id="b", known_from=K + timedelta(days=1), supersedes_claim_id="claim-a"
        )
        db.append_identity_correction(b)
        with pytest.raises(ValueError):
            db.append_identity_correction(replace(b, claim_id="competing"))
        assert len(db.get_claim_revisions("claim-a")) == 2
    elif case == "migration":
        other = PersistentRepository("sqlite+pysqlite:///:memory:", disposable_root=tmp_path)
        assert other.schema_version == "od06.store/v1"
        other.rollback_empty_schema()
        other.migrate()
        assert other.serialize_history() == "[]"
        with pytest.raises(ValueError):
            db.rollback_empty_schema()
        other.close()
    elif case == "history":
        assert db.get_claim_revisions("claim-a") == (c,)
        assert db.serialize_history() == db.serialize_history()
    elif case == "event":
        m, e, _, _ = system()
        ev = m.LifecycleEvent(
            "event-a", "SUSPENSION", ("listing-a",), e, effective_at=K, known_from=K
        )
        db.append_event(ev)
        assert (
            db.resolve_listing("CANARY-X", "TOKEN", "SERIES", D, K, "CANARY_ONLY").state
            == "QUARANTINED"
        )
    elif case == "calendar":
        _, sc, _ = calendar_system()
        db.append_session(sc)
        before = db.calendar().query("CANARY-X", D, K, "CANARY_ONLY")
        if mode == "file":
            url = db.url
            db.close()
            db = PersistentRepository(url, disposable_root=tmp_path)
        assert db.calendar().query("CANARY-X", D, K, "CANARY_ONLY") == before
    db.close()


@pytest.mark.parametrize(
    "case",
    [
        "plain-labels",
        "resolution-write",
        "session-write",
        "universe-write",
        "forged-review",
        "revoked",
        "missing",
        "source-mismatch",
        "wrong-purpose",
        "unknown-time",
        "future-review",
        "conflicting-review",
        "canary-promotion",
        "unrelated-correction",
        "event-list-mutation",
    ],
)
def test_authority_and_semantics(tmp_path, case):
    m, e, r, c = system()
    if case == "plain-labels":
        forged = replace(e, classification="SOURCE_DOCUMENT", authentication="VERIFIED")
        assert (
            resolve(
                replace(r, claims=(replace(c, evidence=forged),)), evidence_policy="STRICT"
            ).state
            != "RESOLVED"
        )
    elif case == "resolution-write":
        with pytest.raises((ValueError, TypeError)):
            replace(resolve(r), financial_eligible=True)
    elif case == "session-write":
        _, _, cal = calendar_system()
        with pytest.raises((ValueError, TypeError)):
            replace(cal.query("CANARY-X", D, K, "CANARY_ONLY"), financial_eligible=True)
    elif case == "universe-write":
        from omegadata.identity_adapters import strict_universe

        u = strict_universe((), r, "EMPTY", D, K, "CANARY_ONLY")
        with pytest.raises((ValueError, TypeError)):
            replace(u, financial_eligible=True)
    elif case == "unrelated-correction":
        other = replace(r.listings[0], listing_id="other-listing")
        rr = replace(r, listings=(*r.listings, other))
        with pytest.raises(ValueError):
            rr.append_correction(
                replace(
                    c,
                    claim_id="b",
                    listing_id="other-listing",
                    known_from=K + timedelta(days=1),
                    supersedes_claim_id=c.claim_id,
                )
            )
    elif case == "event-list-mutation":
        with pytest.raises(ValueError):
            m.LifecycleEvent("event", "LISTING", ["listing-a"], e)
    else:
        from omegadata.identity_authority import EvidenceAuthority, claim_digest

        authority = EvidenceAuthority.unconfigured()
        kwargs = {
            "evidence_id": e.evidence_id,
            "source_record": {"source_key": "CANARY"},
            "reviewer_attestation": {"review_reference": "forged"},
            "consumer_purpose": "RESEARCH",
            "as_of_knowledge": K,
            "claim_sha256": claim_digest(c),
        }
        if case == "missing":
            kwargs["evidence_id"] = ""
        elif case == "unknown-time":
            kwargs["as_of_knowledge"] = None
        elif case == "future-review":
            kwargs["reviewer_attestation"]["reviewed_at"] = (K + timedelta(days=1)).isoformat()
        elif case == "revoked":
            kwargs["source_record"]["revoked"] = True
        elif case == "source-mismatch":
            kwargs["source_record"]["source_key"] = "OTHER"
        elif case == "wrong-purpose":
            kwargs["consumer_purpose"] = "UNRECOGNIZED"
        elif case == "conflicting-review":
            kwargs["reviewer_attestation"]["conflict"] = True
        elif case == "canary-promotion":
            kwargs["source_record"]["authentication"] = "VERIFIED"
        decision = authority.verify_identity_evidence(**kwargs)
        assert not decision.allowed and not decision.financial_eligible
        with pytest.raises((TypeError, ValueError)):
            replace(decision, financial_eligible=True)


@pytest.mark.parametrize(
    "case",
    [
        "incomplete",
        "no-annual-inference",
        "next",
        "previous",
        "coverage-persistence",
        "later-correction",
        "time-conflict",
        "revoked-session",
    ],
)
def test_calendar_completion(tmp_path, case):
    from omegadata.session_calendar import CoverageClaim

    cm, sc, cal = calendar_system()
    e = sc.evidence
    coverage = CoverageClaim(
        "coverage-a", "CANARY-X", D, D + timedelta(days=3), K, None, e, "canary-v1", "COMPLETE"
    )
    day1 = replace(sc, claim_id="day1", session_date=D + timedelta(days=1), session_type="CLOSED")
    day2 = replace(sc, claim_id="day2", session_date=D + timedelta(days=2), session_type="SPECIAL")
    cal = replace(cal, claims=(sc, day1, day2), coverage=(coverage,))
    if case == "incomplete":
        assert (
            replace(cal, coverage=(replace(coverage, status="INCOMPLETE"),)).coverage_status(
                "CANARY-X", D, K, "CANARY_ONLY"
            )
            == "INCOMPLETE"
        )
    elif case == "no-annual-inference":
        assert cal.coverage_status("CANARY-X", date(2001, 6, 1), K, "CANARY_ONLY") == "UNKNOWN"
        assert (
            replace(cal, coverage=()).coverage_status("CANARY-X", D, K, "CANARY_ONLY") == "UNKNOWN"
        )
    elif case == "next":
        assert (
            cal.next_session("CANARY-X", D, K, "CANARY_ONLY").claims[0].session_date
            == day2.session_date
        )
    elif case == "previous":
        assert (
            cal.previous_session("CANARY-X", day2.session_date, K, "CANARY_ONLY")
            .claims[0]
            .session_date
            == D
        )
    elif case == "coverage-persistence":
        db = store(tmp_path, "file")
        db.append_session(sc)
        db.append_coverage(coverage)
        url = db.url
        db.close()
        from omegadata.identity_repository import PersistentRepository

        db = PersistentRepository(url, disposable_root=tmp_path)
        assert db.calendar().coverage_status("CANARY-X", D, K, "CANARY_ONLY") == "COMPLETE"
        db.close()
    elif case == "later-correction":
        changed = replace(
            sc,
            claim_id="new",
            known_from=K + timedelta(days=1),
            supersedes_claim_id=sc.claim_id,
            session_type="CLOSED",
        )
        new = cal.append_correction(changed)
        assert new.query("CANARY-X", D, K, "CANARY_ONLY").status == "AUTHORITATIVE_SESSION"
        assert new.query("CANARY-X", D, changed.known_from, "CANARY_ONLY").status == "KNOWN_CLOSURE"
    elif case == "time-conflict":
        with pytest.raises(ValueError):
            replace(sc, opens_at=K, closes_at=K - timedelta(seconds=1))
    elif case == "revoked-session":
        bad = replace(sc, evidence=replace(e, permission="DENIED"))
        assert (
            replace(cal, claims=(bad,)).query("CANARY-X", D, K, "CANARY_ONLY").status
            == "SOURCE_BLOCKED"
        )


@pytest.mark.parametrize(
    "case", ["coverage-not-completeness", "membership-revision", "accounting", "removal"]
)
def test_universe_completion(case):
    from omegadata.identity_adapters import MembershipClaim, strict_universe

    _, e, r, _ = system()
    a = MembershipClaim(
        "a",
        "INDEX_CANARY",
        "TOKEN",
        "SERIES",
        "CANARY-X",
        D,
        None,
        K,
        None,
        e,
        status="OFFICIAL_VERIFIED",
    )
    if case == "coverage-not-completeness":
        result = strict_universe((a,), r, "INDEX_CANARY", D, K, "CANARY_ONLY")
        assert result.accounted_count == 1 and not result.financial_eligible
        assert result.authoritative_coverage is False
    elif case == "membership-revision":
        b = replace(
            a,
            membership_id="b",
            symbol="MISSING",
            known_from=K + timedelta(days=1),
            supersedes_membership_id="a",
        )
        before = strict_universe((a, b), r, "INDEX_CANARY", D, K, "CANARY_ONLY")
        after = strict_universe((a, b), r, "INDEX_CANARY", D, b.known_from, "CANARY_ONLY")
        assert before.selected_count == after.selected_count == 1
        assert len(before.resolved_entries) == 1 and len(after.unresolved_memberships) == 1
    elif case == "accounting":
        claims = (
            a,
            replace(a, membership_id="b", symbol="MISSING"),
            replace(a, membership_id="c", evidence=replace(e, permission="PENDING")),
        )
        result = strict_universe(claims, r, "INDEX_CANARY", D, K, "CANARY_ONLY")
        assert result.accounted_count == result.selected_count == 3
    elif case == "removal":
        result = strict_universe(
            (replace(a, valid_to=D + timedelta(days=1)),),
            r,
            "INDEX_CANARY",
            D + timedelta(days=1),
            K,
            "CANARY_ONLY",
        )
        assert result.selected_count == 0


@pytest.mark.parametrize(
    "case",
    [
        "authority-original-claim",
        "event-idempotent",
        "unknown-membership",
        "competing-threads",
        "evidence-id-conflict",
        "session-idempotent",
        "session-competing",
        "query-order",
        "pinned-tamper",
        "unowned-database",
        "three-step-reversal",
    ],
)
def test_persistent_review(tmp_path, monkeypatch, case):
    from omegadata.identity_authority import EvidenceAuthority
    from omegadata.identity_repository import PersistentRepository

    if case == "pinned-tamper":
        p = tmp_path / "canary.json"
        p.write_text("{}")
        with pytest.raises(ValueError):
            EvidenceAuthority.from_pinned_bundle(p, "0" * 64)
        return
    if case == "unowned-database":
        from sqlalchemy import create_engine, text

        p = tmp_path / "legacy.sqlite"
        engine = create_engine("sqlite:///" + str(p))
        with engine.begin() as conn:
            conn.execute(text("CREATE TABLE unrelated_canary (id INTEGER)"))
        engine.dispose()
        with pytest.raises(ValueError):
            PersistentRepository("sqlite:///" + str(p), disposable_root=tmp_path)
        return
    db = store(tmp_path, "file")
    r, c = seed(db)
    if case == "authority-original-claim":
        authority = EvidenceAuthority.unconfigured()
        db.authority = authority
        seen = []
        original = EvidenceAuthority.check_claim

        def spy(self, claim, known_at, purpose="RESEARCH"):
            seen.append(claim)
            return original(self, claim, known_at, purpose)

        monkeypatch.setattr(EvidenceAuthority, "check_claim", spy)
        b = replace(
            c,
            claim_id="b",
            known_from=K + timedelta(days=1),
            supersedes_claim_id="claim-a",
            symbol="TOKEN-B",
        )
        db.append_identity_correction(b)
        db.resolve_listing("CANARY-X", "TOKEN", "SERIES", D, K)
        assert seen == [c]  # Authority digest must bind original stored bytes, not derived closure.
    elif case == "event-idempotent":
        m, e, _, _ = system()
        ev = m.LifecycleEvent("ev", "LISTING", ("listing-a",), e)
        db.append_event(ev)
        db.append_event(ev, idempotent=True)
    elif case == "unknown-membership":
        from omegadata.identity_adapters import MembershipClaim

        member = MembershipClaim(
            "m", "INDEX_CANARY", "TOKEN", "SERIES", "CANARY-X", D, None, None, None, c.evidence
        )
        db.append_membership(member)
        assert (
            db.universe("INDEX_CANARY", D, K, "CANARY_ONLY").unresolved_memberships[0].known_from
            is None
        )
    elif case == "competing-threads":
        from concurrent.futures import ThreadPoolExecutor

        def attempt(tag):
            peer = PersistentRepository(db.url, disposable_root=tmp_path)
            b = replace(
                c, claim_id=tag, known_from=K + timedelta(days=1), supersedes_claim_id="claim-a"
            )
            try:
                peer.append_identity_correction(b)
                return "COMMITTED"
            except ValueError:
                return "REFUSED"
            finally:
                peer.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            out = list(pool.map(attempt, ["one", "two"]))
        assert sorted(out) == ["COMMITTED", "REFUSED"]
        assert len(db.get_claim_revisions("claim-a")) == 2
    elif case == "evidence-id-conflict":
        with pytest.raises(ValueError):
            db.append_identity_claim(
                replace(c, claim_id="b", evidence=replace(c.evidence, review_reference="different"))
            )
        assert len(db.get_identity_history("listing-a")) == 1
    elif case == "session-idempotent":
        _, sc, _ = calendar_system()
        db.append_session(sc)
        db.append_session(sc, idempotent=True)
        assert len(db.calendar().claims) == 1
    elif case == "session-competing":
        _, sc, _ = calendar_system()
        db.append_session(sc)
        b = replace(
            sc, claim_id="b", known_from=K + timedelta(days=1), supersedes_claim_id=sc.claim_id
        )
        db.append_session(b)
        with pytest.raises(ValueError):
            db.append_session(replace(b, claim_id="c"))
    elif case == "query-order":
        before = db.serialize_history()
        for _ in range(5):
            db.resolve_listing("CANARY-X", "TOKEN", "SERIES", D, K, "CANARY_ONLY")
        assert before == db.serialize_history()
    elif case == "three-step-reversal":
        b = replace(
            c,
            claim_id="b",
            known_from=K + timedelta(days=1),
            symbol="WRONG_CANARY",
            supersedes_claim_id="claim-a",
        )
        cc = replace(c, claim_id="c", known_from=K + timedelta(days=2), supersedes_claim_id="b")
        db.append_identity_correction(b)
        db.append_identity_correction(cc)
        assert (
            db.resolve_listing("CANARY-X", "TOKEN", "SERIES", D, cc.known_from, "CANARY_ONLY").state
            == "RESOLVED"
        )
    db.close()


@pytest.mark.parametrize(
    "attack",
    [
        "untrusted",
        "revoked",
        "superseded",
        "missing-id",
        "source-mismatch",
        "wrong-purpose",
        "unknown-time",
        "future-review",
        "duplicate-review",
        "canary",
        "bad-hash",
        "pending-rights",
    ],
)
def test_pinned_authority_refusals(tmp_path, attack):
    """Hostile metadata labels, never an actual publisher approval or market row."""
    import hashlib
    import json

    from omegadata.identity_authority import EvidenceAuthority, claim_digest

    _, _, _, c = system()
    source = {
        "source_key": "NSE_EQUITY_BHAVCOPY",
        "artifact_sha256": "a" * 64,
        "publisher_identity": "FORGED_NON_MARKET_CANARY",
        "document_version": "canary-v1",
        "authentication": "VERIFIED",
        "available_at": K.isoformat(),
    }
    review = {
        "reviewer_id": "FORGED_NON_MARKET_CANARY",
        "attestation_identity": "canary-review",
        "reviewed_at": K.isoformat(),
    }
    record = {
        "evidence_id": "test",
        "classification": "AUTHENTIC_SOURCE",
        "claim_sha256": claim_digest(c),
        "source_record": source,
        "reviewer_attestation": review,
    }
    if attack == "revoked":
        record["revoked"] = True
    if attack == "superseded":
        record["superseded"] = True
    if attack == "unknown-time":
        source["available_at"] = None
    if attack == "future-review":
        review["reviewed_at"] = (K + timedelta(days=1)).isoformat()
    if attack == "canary":
        record["classification"] = "NON_MARKET_CANARY"
    if attack == "bad-hash":
        source["artifact_sha256"] = "not-a-sha"
    rows = [record, record] if attack == "duplicate-review" else [record]
    raw = json.dumps({"schema_version": "od06.authority/v1", "records": rows}).encode()
    p = tmp_path / "hostile-metadata.json"
    p.write_bytes(raw)
    if attack == "duplicate-review":
        with pytest.raises(ValueError):
            EvidenceAuthority.from_pinned_bundle(p, hashlib.sha256(raw).hexdigest())
        return
    authority = EvidenceAuthority.from_pinned_bundle(p, hashlib.sha256(raw).hexdigest())
    supplied = dict(source)
    if attack == "source-mismatch":
        supplied["source_key"] = "OTHER"
    decision = authority.verify_identity_evidence(
        "missing" if attack == "missing-id" else "test",
        supplied,
        review,
        "UNSUPPORTED" if attack == "wrong-purpose" else "RESEARCH",
        K,
        claim_digest(c),
    )
    assert not decision.allowed and not decision.financial_eligible
    if attack == "pending-rights":
        assert decision.reason == "SOURCE_RIGHTS_BLOCKED:POLICY_PENDING"
    if attack == "bad-hash":
        assert decision.reason == "PROVENANCE_INCOMPLETE"


def test_unknown_membership_no_inferred_query(tmp_path, monkeypatch):
    from omegadata import identity_repository as module
    from omegadata.identity_adapters import MembershipClaim

    db = store(tmp_path, "file")
    _, c = seed(db)

    def forbidden(*args, **kwargs):
        raise AssertionError("INFERRED_QUERY_TIME")

    monkeypatch.setattr(module, "strict_universe", forbidden)
    member = MembershipClaim(
        "unknown", "INDEX_CANARY", "TOKEN", "SERIES", "CANARY-X", D, None, None, None, c.evidence
    )
    db.append_membership(member)
    db.close()


def test_shared_database_worker_contract():
    from od06_database_experiments import shared_contract

    assert shared_contract() == {
        "schema_version": "od06.shared-canary/v1",
        "market_data": False,
        "financial_eligible": False,
    }


@pytest.mark.parametrize("case", ["unknown-lifecycle", "calendar-version"])
def test_final_semantic_refusals(tmp_path, case):
    if case == "unknown-lifecycle":
        db = store(tmp_path, "file")
        _, c = seed(db)
        m, e, _, _ = system()
        db.append_event(
            m.LifecycleEvent("unknown-event", "SUSPENSION", ("listing-a",), e, effective_at=K)
        )
        assert (
            db.resolve_listing("CANARY-X", "TOKEN", "SERIES", D, K, "CANARY_ONLY").state
            == "QUARANTINED"
        )
        db.close()
    else:
        cm, sc, cal = calendar_system()
        other = replace(sc, claim_id="v2", calendar_version="canary-v2", session_type="CLOSED")
        cal = replace(cal, claims=(sc, other))
        assert (
            cal.query("CANARY-X", D, K, "CANARY_ONLY", calendar_version="canary-v1").status
            == "AUTHORITATIVE_SESSION"
        )
        assert (
            cal.query("CANARY-X", D, K, "CANARY_ONLY", calendar_version="canary-v2").status
            == "KNOWN_CLOSURE"
        )
