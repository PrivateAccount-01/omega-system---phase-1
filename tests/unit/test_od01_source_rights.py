from __future__ import annotations

# All approvals below are SYNTHETIC_TEST_ONLY and reach fake transports only.
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest
from pydantic import ValidationError

from omegadata.config import settings
from omegadata.track_a import download_manager as downloader
from omegadata.track_a.download_manager import DownloadManager
from omegadata.track_a.source_registry import SOURCE_REGISTRY
from omegadata.track_a.source_rights import (
    DEFAULT_POLICY_PATH,
    PolicyReason,
    PolicyRegisterError,
    PolicyRequest,
    PolicyStatus,
    SourcePolicy,
    SourcePolicyError,
    SourcePolicyRegister,
    authorize_source,
    load_policy_register,
)
from omegadata.track_a.source_rights import (
    SourceOperation as Op,
)
from omegadata.track_a.source_rights import (
    SourceTransport as Transport,
)


def test_pending_default_stops_before_cache_disclosure(tmp_path: Path, monkeypatch) -> None:
    """Negative-first proof: unchanged after production implementation."""
    raw = tmp_path / "must-not-be-created"
    monkeypatch.setattr(settings, "raw_root", str(raw))
    monkeypatch.setattr(settings, "seed_raw_root", str(tmp_path / "seed"))
    manager = DownloadManager()
    cached = Mock(return_value=Mock(path=Path("SYNTHETIC_TEST_ONLY")))
    fetch = Mock()
    monkeypatch.setattr(manager, "_load_cached_artifact", cached)
    monkeypatch.setattr(manager, "_fetch_candidate", fetch)
    with pytest.raises(RuntimeError, match="POLICY_PENDING"):
        manager.download("NSE_EQUITY_BHAVCOPY", date(2024, 1, 2))
    cached.assert_not_called()
    fetch.assert_not_called()
    assert not raw.exists()


NOW = datetime(2026, 11, 14, 15, 0, tzinfo=UTC)
KEY = "NSE_EQUITY_BHAVCOPY"
AS_OF = date(2024, 1, 2)


def changed(policy: SourcePolicy, **updates) -> SourcePolicy:
    body = policy.model_dump()
    body.update(updates)
    item = SourcePolicy.model_validate(body)
    return item.model_copy(update={"revision_hash": item.canonical_hash()})


def register(*policies: SourcePolicy) -> SourcePolicyRegister:
    return SourcePolicyRegister(schema_version="source-policy/v1", policies=policies)


def request(
    source_key=KEY, operation=Op.FETCH, transport=Transport.HTTPX, host="example.invalid", **updates
) -> PolicyRequest:
    return PolicyRequest(
        source_key=source_key,
        operation=operation,
        decision_at=NOW,
        requested_transport=transport,
        requested_host=host,
        **updates,
    )


@pytest.fixture()
def approved(synthetic_source_policy_provider) -> SourcePolicy:
    return synthetic_source_policy_provider().policies[0]


@pytest.mark.parametrize(
    ("case", "reason"),
    [
        ("unknown", PolicyReason.UNKNOWN_SOURCE),  # T01
        ("missing", PolicyReason.MISSING_POLICY),  # T02
        ("pending", PolicyReason.POLICY_PENDING),  # T03
        ("denied", PolicyReason.POLICY_DENIED),  # T04
        ("revoked", PolicyReason.POLICY_REVOKED),  # T05
        ("expired", PolicyReason.POLICY_EXPIRED),  # T06
        ("expiry_state", PolicyReason.POLICY_EXPIRED),
        ("evidence", PolicyReason.EVIDENCE_INCOMPLETE),  # T07
        ("host", PolicyReason.HOST_NOT_ALLOWED),  # T10
        ("transport", PolicyReason.TRANSPORT_NOT_ALLOWED),  # T11
        ("store", PolicyReason.SCOPE_NOT_ALLOWED),
        ("future", PolicyReason.SCOPE_NOT_ALLOWED),
    ],
)
def test_t01_t11_download_refusals_have_zero_side_effects(
    case,
    reason,
    approved,
    tmp_path,
    monkeypatch,
) -> None:
    body = {
        "pending": {"status": PolicyStatus.PENDING_REVIEW},
        "denied": {"status": PolicyStatus.DENIED},
        "revoked": {
            "status": PolicyStatus.REVOKED,
            "revocation_reason": "SYNTHETIC_TEST_ONLY",
            "revoked_at": NOW,
        },
        "expired": {"valid_until": NOW},
        "expiry_state": {"status": PolicyStatus.EXPIRED},
        "evidence": {"approval_evidence_ref": None},
        "host": {"allowed_hosts": ("foreign.invalid",)},
        "transport": {"permitted_transports": (Transport.CURL,)},
        "store": {"permitted_operations": (Op.FETCH,)},
        "future": {"approved_at": NOW + timedelta(seconds=1)},
    }.get(case, {})
    policy = changed(approved, **body)

    def provider():
        return register() if case == "missing" else register(policy)

    raw = tmp_path / "no-raw"
    monkeypatch.setattr(settings, "raw_root", str(raw))
    monkeypatch.setattr(settings, "seed_raw_root", str(tmp_path / "no-seed"))
    manager = DownloadManager(policy_provider=provider, decision_clock=lambda: NOW)
    network = Mock(side_effect=AssertionError("fake network must not be reached"))
    cached = Mock(side_effect=AssertionError("cache must not be consulted"))
    candidates = Mock(side_effect=AssertionError("fallback must not be selected"))
    reads = Mock(side_effect=AssertionError("payload must not be read"))
    writes = Mock(side_effect=AssertionError("raw must not be written"))
    text_writes = Mock(side_effect=AssertionError("manifest must not be written"))
    directories = Mock(side_effect=AssertionError("raw directory must not be created"))
    monkeypatch.setattr(manager, "_fetch_candidate", network)
    monkeypatch.setattr(manager, "_candidate_urls", candidates)
    monkeypatch.setattr(manager, "_load_cached_artifact", cached)
    monkeypatch.setattr(Path, "read_bytes", reads)
    monkeypatch.setattr(Path, "write_bytes", writes)
    monkeypatch.setattr(Path, "write_text", text_writes)
    monkeypatch.setattr(Path, "mkdir", directories)
    monkeypatch.setattr(downloader.httpx, "Client", network)
    with pytest.raises(SourcePolicyError) as exc:
        manager.download("UNREGISTERED_TEST" if case == "unknown" else KEY, AS_OF, use_cache=False)
    assert exc.value.reason_code == reason
    for spy in (network, cached, candidates, reads, writes, text_writes, directories):
        spy.assert_not_called()
    assert not raw.exists()


def test_t08_fetch_does_not_grant_redistribution(approved) -> None:
    def provider():
        return register(changed(approved, permitted_operations=(Op.FETCH,)))

    assert authorize_source(request(), provider).allowed
    with pytest.raises(SourcePolicyError) as exc:
        authorize_source(request(operation=Op.REDISTRIBUTE), provider)
    assert exc.value.reason_code == PolicyReason.SCOPE_NOT_ALLOWED


def test_t09_research_does_not_grant_trade_use(approved) -> None:
    def provider():
        return register(changed(approved, permitted_operations=(Op.FETCH, Op.RESEARCH)))

    assert authorize_source(request(consumer_purpose=Op.RESEARCH), provider).allowed
    with pytest.raises(SourcePolicyError) as exc:
        authorize_source(request(consumer_purpose=Op.TRADE_DECISION_USE), provider)
    assert exc.value.reason_code == PolicyReason.SCOPE_NOT_ALLOWED


def test_t12_fake_http_acquisition_preserves_envelope(
    synthetic_source_policy_provider,
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "raw_root", str(tmp_path / "raw"))
    monkeypatch.setattr(settings, "seed_raw_root", str(tmp_path / "seed"))
    manager = DownloadManager(
        policy_provider=synthetic_source_policy_provider, decision_clock=lambda: NOW
    )
    payload = b"SYNTHETIC_TEST_ONLY payload; no licensed market data"
    calls = []

    def handler(req):
        calls.append(str(req.url))
        return httpx.Response(200, content=payload, headers={"content-type": "text/plain"})

    original = httpx.Client
    monkeypatch.setattr(
        downloader.httpx,
        "Client",
        lambda **kw: original(transport=httpx.MockTransport(handler), **kw),
    )
    artifact = manager.download("MOSPI", AS_OF, use_cache=False)
    assert len(calls) == 1
    assert artifact.path.read_bytes() == payload
    assert artifact.checksum == hashlib.sha256(payload).hexdigest()
    assert artifact.bytes_downloaded == len(payload)
    manifest = json.loads(artifact.manifest_path.read_text())
    assert manifest["checksum"] == artifact.checksum
    assert manifest["storage_mode"] == "immutable_versioned"
    assert len(manifest["policy_decisions"]) == 2
    assert all(d.policy_id.startswith("SYNTHETIC_TEST_ONLY") for d in artifact.policy_decisions)
    assert {d.operation for d in artifact.policy_decisions} == {Op.FETCH, Op.STORE_RAW}
    assert all(len(d.revision_hash) == 64 for d in artifact.policy_decisions)
    before = artifact.manifest_path.read_bytes()
    cached = manager.download("MOSPI", AS_OF)
    assert cached.checksum == artifact.checksum and len(calls) == 1
    assert all(d.operation == Op.READ_CACHED for d in cached.policy_decisions)
    assert artifact.manifest_path.read_bytes() == before


def test_t13_latest_revocation_keeps_old_decision_attributable(approved) -> None:
    old = register(approved).evaluate(request())
    revoked = changed(
        approved,
        policy_revision=2,
        previous_revision_hash=approved.revision_hash,
        status=PolicyStatus.REVOKED,
        revocation_reason="SYNTHETIC_TEST_ONLY",
        revoked_at=NOW,
        created_at=NOW,
    )
    current = register(approved, revoked).evaluate(request())
    assert old.allowed and old.policy_revision == 1
    assert not current.allowed and current.reason_code == PolicyReason.POLICY_REVOKED
    assert current.policy_revision == 2 and current.revision_hash != old.revision_hash
    assert old.revision_hash == approved.revision_hash


@pytest.mark.parametrize(
    "field",
    [
        "source_entity",
        "source_terms_url",
        "terms_sha256",
        "terms_retrieved_at",
        "approval_evidence_ref",
        "approved_by",
        "approved_at",
        "valid_from",
        "valid_until",
    ],
)
def test_t07_each_missing_approval_evidence_field_is_denied(approved, field) -> None:
    decision = register(changed(approved, **{field: None})).evaluate(request())
    assert decision.reason_code == PolicyReason.EVIDENCE_INCOMPLETE


@pytest.mark.parametrize(
    "field",
    ["created_at", "terms_retrieved_at", "approved_at", "valid_from", "valid_until", "revoked_at"],
)
def test_t14_naive_policy_dates_reject(approved, field) -> None:
    with pytest.raises(ValidationError):
        changed(approved, **{field: datetime(2026, 1, 1)})


@pytest.mark.parametrize("timestamp", ["2026-01-01", "2026-01-01T12:00:00+05:30", 1760000000])
def test_t14_request_timestamp_ambiguity_rejects(timestamp) -> None:
    with pytest.raises(ValidationError):
        PolicyRequest(
            source_key=KEY,
            operation=Op.FETCH,
            decision_at=timestamp,
            requested_transport=Transport.HTTPX,
            requested_host="example.invalid",
        )


@pytest.mark.parametrize(
    "mutation",
    [
        {"status": "approved"},
        {"policy_revision": True},
        {"extra_field": "invalid"},
        {"terms_sha256": "wrong"},
        {"schema_version": "source-policy/v2"},
        {"source_key": "UNKNOWN"},
        {"source_key": []},
        {"allowed_hosts": ("*.example.invalid",)},
        {"allowed_hosts": ("https://example.invalid",)},
        {"allowed_hosts": ("example.invalid:443",)},
        {"permitted_operations": ("VIEW",)},
        {"permitted_transports": ("STEALTH",)},
    ],
)
def test_t14_malformed_fields_reject(approved, mutation) -> None:
    with pytest.raises(ValidationError):
        changed(approved, **mutation)


def test_t14_duplicate_entries_and_unlinked_revisions_reject(approved) -> None:
    with pytest.raises(ValidationError):
        register(approved, approved)
    with pytest.raises(ValidationError):
        register(approved, changed(approved, policy_revision=2))
    with pytest.raises(ValidationError):
        register(
            changed(approved, change_reason="tampered").model_copy(
                update={"revision_hash": approved.revision_hash}
            )
        )


@pytest.mark.parametrize(
    "contents",
    [
        b"not json",
        b'{"schema_version":"source-policy/v1","schema_version":"source-policy/v1","policies":[]}',
        b'{"schema_version":"source-policy/v1","policies":[],"extra":true}',
        b"\xff\xfeinvalid encoding",
    ],
)
def test_t14_malformed_file_denies_before_transport(tmp_path, contents, monkeypatch) -> None:
    path = tmp_path / "policy.json"
    path.write_bytes(contents)

    def provider():
        return load_policy_register(path)

    manager = DownloadManager(policy_provider=provider, decision_clock=lambda: NOW)
    spy = Mock()
    monkeypatch.setattr(manager, "_load_cached_artifact", spy)
    with pytest.raises(SourcePolicyError) as exc:
        manager.download(KEY, AS_OF)
    assert exc.value.reason_code == PolicyReason.MALFORMED_POLICY
    spy.assert_not_called()


@pytest.mark.parametrize("key", tuple(SOURCE_REGISTRY))
def test_default_pending_blocks_every_source_before_cache(key, monkeypatch) -> None:
    manager = DownloadManager()
    spy = Mock()
    monkeypatch.setattr(manager, "_load_cached_artifact", spy)
    with pytest.raises(SourcePolicyError) as exc:
        manager.download(key, AS_OF)
    assert exc.value.reason_code == PolicyReason.POLICY_PENDING
    spy.assert_not_called()


@pytest.mark.parametrize(
    "host",
    [
        "foreign.invalid",
        "*.example.invalid",
        "example.invalid:443",
        "https://example.invalid",
        None,
    ],
)
def test_t10_evaluator_exact_host_scope(approved, host) -> None:
    assert (
        register(approved).evaluate(request(host=host)).reason_code == PolicyReason.HOST_NOT_ALLOWED
    )


def test_normalized_dns_and_local_cache_policy(approved) -> None:
    policy = changed(approved, allowed_hosts=("EXAMPLE.INVALID.",))
    assert register(policy).evaluate(request(host="Example.Invalid.")).allowed
    assert (
        register(policy)
        .evaluate(request(operation=Op.READ_CACHED, transport=Transport.CACHE, host=None))
        .allowed
    )
    assert not register(policy).evaluate(request(transport=Transport.BROWSER)).allowed


@pytest.mark.parametrize(
    "changes",
    [
        {"valid_until": datetime(2019, 1, 1, tzinfo=UTC)},
        {"permitted_operations": (Op.FETCH, Op.FETCH)},
        {"permitted_transports": (Transport.HTTPX, Transport.HTTPX)},
        {"allowed_hosts": ("example.invalid", "EXAMPLE.INVALID")},
        {"source_terms_url": "https://user:credential@example.invalid/terms"},
        {"status": PolicyStatus.REVOKED, "revoked_at": NOW},
        {"source_key": " NSE_EQUITY_BHAVCOPY "},
    ],
)
def test_structural_policy_inconsistencies_are_malformed(approved, changes) -> None:
    with pytest.raises(ValidationError):
        changed(approved, **changes)


def test_invalid_register_history_identity_rejects(
    approved, synthetic_source_policy_provider
) -> None:
    other = synthetic_source_policy_provider().policies[1]
    with pytest.raises(ValidationError):
        register(approved, changed(other, policy_id=approved.policy_id))
    with pytest.raises(ValidationError):
        register(
            changed(approved, policy_revision=2, previous_revision_hash=approved.revision_hash)
        )
    with pytest.raises(ValidationError):
        PolicyRequest(
            source_key=" NSE_EQUITY_BHAVCOPY ",
            operation=Op.FETCH,
            decision_at=NOW,
            requested_transport=Transport.HTTPX,
        )


def test_t17_optional_pipeline_refusal_does_not_try_later_source(approved, monkeypatch) -> None:
    from omegadata.pipelines.sequential_pipeline import OmegaDataSequentialPipeline

    pipeline = OmegaDataSequentialPipeline()
    seen = []
    denied = register(changed(approved, status=PolicyStatus.DENIED)).evaluate(request())

    def ingest(key, as_of):
        seen.append(key)
        if key == "NSE_FO_BHAVCOPY":
            raise SourcePolicyError(denied)
        return "SYNTHETIC_TEST_ONLY-unused"

    monkeypatch.setattr(pipeline.ingestor, "ingest_raw_source", ingest)
    with pytest.raises(SourcePolicyError):
        pipeline.run_track_a(AS_OF)
    assert seen == ["NSE_EQUITY_BHAVCOPY", "BSE_EQUITY_BHAVCOPY", "NSE_FO_BHAVCOPY"]


def test_allowed_fake_probe_preserves_policy_attribution(
    synthetic_source_policy_provider, monkeypatch
) -> None:
    manager = DownloadManager(
        policy_provider=synthetic_source_policy_provider, decision_clock=lambda: NOW
    )
    fake = Mock(
        return_value=downloader.FetchResult(b"SYNTHETIC_TEST_ONLY", 200, "text/plain", "httpx", 1)
    )
    monkeypatch.setattr(manager, "_fetch_candidate", fake)
    results = manager.probe_source_candidates("MOSPI", AS_OF, limit=1)
    assert len(results) == 1 and results[0].validated
    assert results[0].policy_decisions[0].policy_id.startswith("SYNTHETIC_TEST_ONLY")
    assert fake.call_count == 1


def test_t17_denied_fallback_transport_is_terminal(approved, monkeypatch) -> None:
    policy = changed(approved, permitted_transports=(Transport.HTTPX,))
    manager = DownloadManager(policy_provider=lambda: register(policy), decision_clock=lambda: NOW)
    first = Mock(side_effect=downloader.DownloadError("TLS issue"))
    fallback = Mock()
    monkeypatch.setattr(manager, "_request", first)
    monkeypatch.setattr(manager, "_request_via_urllib", fallback)
    monkeypatch.setattr(manager, "_request_via_curl", fallback)
    with manager._source_scope(KEY), pytest.raises(SourcePolicyError) as exc:
        manager._request_with_workarounds(Mock(cookies={}), "https://www.nseindia.com/api/mock", {})
    assert exc.value.reason_code == PolicyReason.TRANSPORT_NOT_ALLOWED
    assert first.call_count == 1
    fallback.assert_not_called()


def test_missing_policy_file_is_typed_refusal(tmp_path) -> None:
    with pytest.raises(PolicyRegisterError) as exc:
        load_policy_register(tmp_path / "absent.json")
    assert exc.value.reason_code == PolicyReason.MISSING_POLICY


def test_t15_every_registered_default_is_pending() -> None:
    default = load_policy_register()
    assert {p.source_key for p in default.policies} == set(SOURCE_REGISTRY)
    assert len(default.policies) == len(SOURCE_REGISTRY) == 13
    assert all(p.status == PolicyStatus.PENDING_REVIEW for p in default.policies)
    assert all(
        not p.permitted_operations and not p.permitted_transports and not p.allowed_hosts
        for p in default.policies
    )
    assert all(p.approved_by is None and p.terms_sha256 is None for p in default.policies)
    assert DEFAULT_POLICY_PATH.is_file()


@pytest.mark.parametrize("seed", [False, True])
def test_t16_revoked_cache_and_seed_do_not_read_payload(
    seed,
    approved,
    tmp_path,
    monkeypatch,
) -> None:
    manager = DownloadManager(
        policy_provider=lambda: register(
            changed(
                approved,
                status=PolicyStatus.REVOKED,
                revocation_reason="SYNTHETIC_TEST_ONLY",
                revoked_at=NOW,
            )
        ),
        decision_clock=lambda: NOW,
    )
    root = tmp_path / "seed" if seed else tmp_path / "raw"
    manager.raw_root = tmp_path / "raw"
    manager.seed_raw_root = tmp_path / "seed"
    reads = Mock(side_effect=AssertionError("No cache payload may be read"))
    writes = Mock()
    network = Mock()
    monkeypatch.setattr(Path, "read_bytes", reads)
    monkeypatch.setattr(Path, "write_bytes", writes)
    monkeypatch.setattr(manager, "_fetch_candidate", network)
    with pytest.raises(SourcePolicyError) as exc:
        manager._load_cached_artifact_from_root(root, KEY, AS_OF)
    assert exc.value.reason_code == PolicyReason.POLICY_REVOKED
    for spy in (reads, writes, network):
        spy.assert_not_called()


def test_cache_only_permission_does_not_escalate_on_miss(approved, tmp_path, monkeypatch) -> None:
    policy = changed(approved, permitted_operations=(Op.READ_CACHED,))
    manager = DownloadManager(policy_provider=lambda: register(policy), decision_clock=lambda: NOW)
    manager.raw_root = tmp_path / "raw"
    manager.seed_raw_root = tmp_path / "seed"
    spy = Mock()
    monkeypatch.setattr(manager, "_fetch_candidate", spy)
    with pytest.raises(SourcePolicyError) as exc:
        manager.download(KEY, AS_OF)
    assert exc.value.reason_code == PolicyReason.SCOPE_NOT_ALLOWED
    spy.assert_not_called()


def test_t17_policy_refusal_in_fetch_is_not_swallowed(approved, tmp_path, monkeypatch) -> None:
    manager = DownloadManager(
        policy_provider=lambda: register(approved), decision_clock=lambda: NOW
    )
    manager.raw_root = tmp_path / "no-output"
    denied = register(changed(approved, status=PolicyStatus.DENIED)).evaluate(request())
    fetch = Mock(side_effect=SourcePolicyError(denied))
    monkeypatch.setattr(
        manager,
        "_candidate_urls",
        lambda *_: ["https://example.invalid/one", "https://example.invalid/two"],
    )
    monkeypatch.setattr(manager, "_fetch_candidate", fetch)
    with pytest.raises(SourcePolicyError) as exc:
        manager.download(KEY, AS_OF, use_cache=False)
    assert exc.value.reason_code == PolicyReason.POLICY_DENIED
    assert fetch.call_count == 1
    assert not manager.raw_root.exists()


def test_t18_concurrent_decisions_are_immutable_and_deterministic(approved) -> None:
    policy = register(approved)
    with ThreadPoolExecutor(max_workers=4) as pool:
        decisions = list(pool.map(lambda _: policy.evaluate(request()), range(32)))
    assert all(d == decisions[0] for d in decisions)
    with pytest.raises(ValidationError):
        policy.policies[0].status = PolicyStatus.APPROVED
    with pytest.raises(ValidationError):
        decisions[0].allowed = False


def test_t18_transport_source_context_is_thread_local(synthetic_source_policy_provider) -> None:
    manager = DownloadManager(
        policy_provider=synthetic_source_policy_provider, decision_clock=lambda: NOW
    )

    def scoped(key):
        with manager._source_scope(key):
            return manager._policy_source.get()

    with ThreadPoolExecutor(max_workers=4) as pool:
        keys = list(SOURCE_REGISTRY)
        assert list(pool.map(scoped, keys)) == keys
    assert manager._policy_source.get() == ""


@pytest.mark.parametrize(
    "entry",
    [
        "probe",
        "discover_bse",
        "discover_fo",
        "stockreach",
        "unscoped_request",
        "unscoped_urllib",
        "unscoped_curl",
    ],
)
def test_all_manager_acquisition_entry_points_fail_closed(entry, tmp_path, monkeypatch) -> None:
    manager = DownloadManager()
    calls = Mock(side_effect=AssertionError("network forbidden"))
    monkeypatch.setattr(downloader.httpx, "Client", calls)
    monkeypatch.setattr(downloader, "urlopen", calls)
    monkeypatch.setattr(downloader.subprocess, "run", calls)
    with pytest.raises(SourcePolicyError):
        if entry == "probe":
            manager.probe_source_candidates(KEY, AS_OF)
        elif entry == "discover_bse":
            manager._discover_bse_equity_urls(AS_OF)
        elif entry == "discover_fo":
            manager._discover_nse_fo_urls(AS_OF)
        elif entry == "stockreach":
            manager.fetch_bse_stockreach_graph("123", AS_OF, AS_OF)
        elif entry == "unscoped_request":
            manager._request(Mock(), "https://example.invalid")
        elif entry == "unscoped_urllib":
            manager._request_via_urllib("https://example.invalid", {})
        else:
            manager._request_via_curl("https://example.invalid", {})
    calls.assert_not_called()


def test_foreign_discovered_host_is_denied_before_client(approved, monkeypatch) -> None:
    manager = DownloadManager(
        policy_provider=lambda: register(approved), decision_clock=lambda: NOW
    )
    spy = Mock()
    monkeypatch.setattr(downloader.httpx, "Client", spy)
    with pytest.raises(SourcePolicyError) as exc:
        manager._fetch_candidate(KEY, AS_OF, url="https://foreign.invalid/file", profile={})
    assert exc.value.reason_code == PolicyReason.HOST_NOT_ALLOWED
    spy.assert_not_called()


def test_policy_change_is_rechecked_before_operation(approved, tmp_path, monkeypatch) -> None:
    active = register(approved)
    manager = DownloadManager(policy_provider=lambda: active, decision_clock=lambda: NOW)
    assert manager._authorize(KEY, Op.READ_CACHED, Transport.CACHE).allowed
    active = register(
        changed(
            approved,
            status=PolicyStatus.REVOKED,
            revocation_reason="SYNTHETIC_TEST_ONLY",
            revoked_at=NOW,
        )
    )
    spy = Mock()
    monkeypatch.setattr(manager, "_load_cached_artifact", spy)
    with pytest.raises(SourcePolicyError):
        manager.download(KEY, AS_OF)
    spy.assert_not_called()


def test_source_probe_script_checks_policy_before_curl(monkeypatch) -> None:
    path = Path(__file__).resolve().parents[2] / "scripts/generate_source_probe_report.py"
    spec = spec_from_file_location("od01_probe_under_test", path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    spy = Mock()
    monkeypatch.setattr(module.subprocess, "run", spy)
    with pytest.raises(SourcePolicyError) as exc:
        module._probe_entry(
            source_key=KEY,
            as_of=AS_OF,
            url="https://example.invalid/data",
            role="primary",
            timeout_seconds=1.0,
            kind="zip",
        )
    assert exc.value.reason_code == PolicyReason.POLICY_PENDING
    spy.assert_not_called()
