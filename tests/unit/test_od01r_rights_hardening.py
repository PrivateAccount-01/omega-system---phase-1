"""OD-01R adversarial boundaries; every approval is SYNTHETIC_TEST_ONLY."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest

from omegadata.track_a import download_manager as dm
from omegadata.track_a.download_manager import DownloadManager, FetchResult
from omegadata.track_a.source_rights import (
    PolicyReason,
    PolicyStatus,
    SourcePolicy,
    SourcePolicyError,
    SourcePolicyRegister,
    SourceTransport,
)

KEY = "NSE_EQUITY_BHAVCOPY"
DAY = date(2024, 1, 2)
NOW = datetime(2026, 11, 15, tzinfo=UTC)
REPO = Path(__file__).resolve().parents[2]


def updated(policy, **changes):
    body = policy.model_dump()
    body.update(changes)
    item = SourcePolicy.model_validate(body)
    return item.model_copy(update={"revision_hash": item.canonical_hash()})


def registry(*policies):
    return SourcePolicyRegister(schema_version="source-policy/v1", policies=policies)


@pytest.fixture()
def manager(synthetic_source_policy_provider, tmp_path):
    item = synthetic_source_policy_provider().policies[0]
    item = updated(item, allowed_hosts=("example.invalid",))
    result = DownloadManager(policy_provider=lambda: registry(item), decision_clock=lambda: NOW)
    result.raw_root = tmp_path / "raw"
    result.seed_raw_root = tmp_path / "seed"
    return result


BAD_URLS = [
    "https://example.invalid:4443/file", "https://example.invalid:80/file",
    "https://example.invalid:8080/file", "http://example.invalid/file",
    "ftp://example.invalid/file", "file://example.invalid/file", "//example.invalid/file",
    "https://user:pass@example.invalid/file", "https://@example.invalid/file",
    "https://example.invalid@other.invalid/file", "https:///example.invalid/file",
    "https://example.invalid:/file", "https://example.invalid:65536/file",
    "https://example.invalid:-1/file", "https://example.invalid:abc/file",
    "https://example.invalid:0443/file", "https://example.invalid../file",
    "https://example.invalid\\@other.invalid/file", "https://example.invalid%2e/file",
    "https://exam\nple.invalid/file", " https://example.invalid/file",
    "https://127.0.0.1/file", "https://10.0.0.1/file", "https://[::1]/file",
    "https://[bad/file", "https://localhost/file", "https://loopback.local/file",
]


@pytest.mark.parametrize("url", BAD_URLS)
def test_r01_r03_url_denied_before_client(manager, monkeypatch, url):
    client = Mock()
    monkeypatch.setattr(dm.httpx, "Client", client)
    monkeypatch.setattr(manager, "_request_with_workarounds", Mock(return_value=FetchResult(
        b"SYNTHETIC_TEST_ONLY", 200, "text/plain", "httpx", 1)))
    monkeypatch.setattr(manager, "_bootstrap_nse_session", Mock())
    with pytest.raises(SourcePolicyError) as exc:
        manager._fetch_candidate(KEY, DAY, url=url, profile={})
    assert exc.value.reason_code == PolicyReason.HOST_NOT_ALLOWED
    client.assert_not_called()
    assert not manager.raw_root.exists()


@pytest.mark.parametrize("url", [
    "https://example.invalid/data", "https://example.invalid:443/data",
    "https://EXAMPLE.INVALID./data?q=http://foreign.invalid:80",
])
def test_r04_https_allowed_mock_transport(manager, monkeypatch, url):
    calls = []

    def handler(request):
        calls.append(request.url)
        return httpx.Response(200, content=b"SYNTHETIC_TEST_ONLY")

    original = httpx.Client
    monkeypatch.setattr(dm.httpx, "Client", lambda **kw: original(
        transport=httpx.MockTransport(handler), **kw))
    result = manager._fetch_candidate(KEY, DAY, url=url, profile={})
    assert result.payload == b"SYNTHETIC_TEST_ONLY" and len(calls) == 1


def cache_fixture(manager, root=None):
    root = manager.raw_root if root is None else root
    folder = root / KEY.lower() / "year=2024" / "month=01"
    folder.mkdir(parents=True)
    artifact = folder / "20240102__safe.bin"
    content = b"SYNTHETIC_TEST_ONLY harmless payload"
    artifact.write_bytes(content)
    pointer = folder / "20240102.latest.json"
    body = {"source_key": KEY, "as_of": DAY.isoformat(), "artifact_path": str(artifact),
            "checksum": hashlib.sha256(content).hexdigest(), "bytes_downloaded": len(content)}
    return folder, artifact, pointer, body


@pytest.mark.parametrize("form", ["absolute", "traversal", "manifest_escape", "pointer_escape"])
@pytest.mark.parametrize("seed", [False, True])
def test_r05_cache_escape_never_opens_external_sentinel(manager, tmp_path, monkeypatch, form, seed):
    root = manager.seed_raw_root if seed else manager.raw_root
    folder, artifact, pointer, body = cache_fixture(manager, root)
    outside = tmp_path / "sentinel.bin"
    outside.write_bytes(b"SYNTHETIC_TEST_ONLY harmless payload")
    if form == "absolute":
        body["artifact_path"] = str(outside)
    elif form == "traversal":
        body["artifact_path"] = str(folder / ".." / ".." / ".." / ".." / outside.name)
    elif form == "manifest_escape":
        body["manifest_path"] = str(outside)
    else:
        try:
            pointer.symlink_to(outside)
        except OSError as exc:
            pytest.skip(f"Real symlink unavailable: {exc}")
    if form != "pointer_escape":
        pointer.write_text(json.dumps(body), encoding="utf-8")
    reads = []
    original = Path.open

    def watch(path, *args, **kw):
        if path.resolve() == outside.resolve():
            reads.append(path)
            raise AssertionError("External sentinel must never be opened")
        return original(path, *args, **kw)

    monkeypatch.setattr(Path, "open", watch)
    assert manager._load_cached_artifact_from_root(root, KEY, DAY) is None
    assert reads == []


def test_r06_real_symlink_payload_escape(manager, tmp_path, monkeypatch):
    folder, artifact, pointer, body = cache_fixture(manager)
    outside = tmp_path / "sentinel.bin"
    outside.write_bytes(b"SYNTHETIC_TEST_ONLY harmless payload")
    link = folder / "linked.bin"
    try:
        link.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"Real symlink unavailable: {exc}")
    body["artifact_path"] = str(link)
    pointer.write_text(json.dumps(body), encoding="utf-8")
    reads = Mock(side_effect=AssertionError("No external bytes may be opened"))
    monkeypatch.setattr(Path, "read_bytes", reads)
    assert manager._load_cached_artifact_from_root(manager.raw_root, KEY, DAY) is None
    reads.assert_not_called()


@pytest.mark.parametrize("entry", ["partition", "payload_directory"])
def test_r06_windows_junction_escape(manager, tmp_path, monkeypatch, entry):
    if sys.platform != "win32":
        pytest.skip("Windows junction test")
    import _winapi

    folder, _, pointer, body = cache_fixture(manager)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "20240102__safe.bin").write_bytes(b"SYNTHETIC_TEST_ONLY harmless payload")
    if entry == "payload_directory":
        junction = folder / "junction"
        _winapi.CreateJunction(str(outside), str(junction))
        body["artifact_path"] = str(junction / "20240102__safe.bin")
        pointer.write_text(json.dumps(body), encoding="utf-8")
    else:
        # Redirect the cache partition itself, without removing any existing path.
        manager.raw_root = tmp_path / "other_raw"
        parent = manager.raw_root / KEY.lower() / "year=2024"
        parent.mkdir(parents=True)
        _winapi.CreateJunction(str(outside), str(parent / "month=01"))
        (outside / "20240102.latest.json").write_text(json.dumps(body), encoding="utf-8")
    reads = []
    original = Path.open

    def watch(path, *args, **kw):
        if path.resolve().is_relative_to(outside):
            reads.append(path)
            raise AssertionError("Junction target must never be opened")
        return original(path, *args, **kw)

    monkeypatch.setattr(Path, "open", watch)
    assert manager._load_cached_artifact_from_root(manager.raw_root, KEY, DAY) is None
    assert reads == []


@pytest.mark.parametrize("change", [
    {"source_key": "MOSPI"}, {"as_of": "2024-01-03"}, {"trade_date": "2024-01-03"},
    {"checksum": "a" * 64}, {"bytes_downloaded": 999}, {"artifact_path": ""},
    {"artifact_path": "../escape.bin"}, {"artifact_path": "C:relative.bin"},
    {"artifact_path": "safe.bin:stream"}, {"bytes_downloaded": "bad"},
])
def test_r07_inconsistent_cache_is_miss(manager, change):
    _, _, pointer, body = cache_fixture(manager)
    body.update(change)
    pointer.write_text(json.dumps(body), encoding="utf-8")
    assert manager._load_cached_artifact_from_root(manager.raw_root, KEY, DAY) is None


@pytest.mark.parametrize("content", ["[]", "null", "{bad", '{"checksum":"a","checksum":"b"}'])
def test_r07_malformed_manifest_is_miss(manager, content):
    _, _, pointer, _ = cache_fixture(manager)
    pointer.write_text(content, encoding="utf-8")
    assert manager._load_cached_artifact_from_root(manager.raw_root, KEY, DAY) is None


@pytest.mark.parametrize("form", ["absolute", "bare", "repo_relative"])
def test_r07_safe_legacy_cache_compatible(manager, monkeypatch, tmp_path, form):
    monkeypatch.chdir(tmp_path)
    _, artifact, pointer, body = cache_fixture(manager)
    body.pop("source_key")
    body.pop("as_of")
    if form == "bare":
        body["artifact_path"] = artifact.name
    elif form == "repo_relative":
        body["artifact_path"] = str(artifact.relative_to(tmp_path))
    pointer.write_text(json.dumps(body), encoding="utf-8")
    cached = manager._load_cached_artifact_from_root(manager.raw_root, KEY, DAY)
    assert cached is not None and cached.path.resolve() == artifact.resolve()


def script(name):
    spec = spec_from_file_location("od01r_" + name, REPO / "scripts" / (name + ".py"))
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("name,entry", [
    ("probe_endpoints", "probe_corporate_actions"), ("probe_endpoints", "probe_bse_bhavcopy"),
    ("probe_bse_urls", "main"), ("generate_source_probe_matrix", "main"),
    ("generate_source_probe_matrix", "_run"),
])
def test_r15_manual_diagnostics_disabled_before_side_effects(name, entry, monkeypatch):
    module = script(name)
    network = Mock(side_effect=AssertionError("Must refuse before side effects"))
    if hasattr(module, "httpx"):
        monkeypatch.setattr(module.httpx, "Client", network)
    if hasattr(module, "subprocess"):
        monkeypatch.setattr(module.subprocess, "run", network)
    with pytest.raises(RuntimeError, match="disabled"):
        getattr(module, entry)(*([] if entry != "_run" else ["deterministic"]))
    network.assert_not_called()


def test_r08_fo_loader_pending_before_db_or_http(monkeypatch):
    module = script("load_nse_fo_into_pipeline_db")
    db, network = Mock(), Mock(side_effect=AssertionError("Must refuse before HTTP"))
    monkeypatch.setattr(module, "init_db", db)
    monkeypatch.setattr(module.httpx, "get", network)
    monkeypatch.setattr(sys, "argv", ["loader", "--trade-date", DAY.isoformat()])
    with pytest.raises(SourcePolicyError, match="POLICY_PENDING"):
        module.main()
    db.assert_not_called()
    network.assert_not_called()


def test_r13_fo_loader_rechecks_after_db_setup(synthetic_source_policy_provider, monkeypatch):
    module = script("load_nse_fo_into_pipeline_db")
    from omegadata.track_a.source_rights import authorize_source

    active = synthetic_source_policy_provider()
    calls = Mock(side_effect=AssertionError("Revoked source must not fetch"))

    def authorize(request):
        return authorize_source(request, lambda: active)

    def init():
        nonlocal active
        item = next(p for p in active.policies if p.source_key == "NSE_FO_BHAVCOPY")
        active = registry(updated(item, status=PolicyStatus.REVOKED,
                                  revoked_at=NOW, revocation_reason="SYNTHETIC_TEST_ONLY"))

    monkeypatch.setattr(module, "authorize_source", authorize)
    monkeypatch.setattr(module, "init_db", init)
    monkeypatch.setattr(module.httpx, "get", calls)
    monkeypatch.setattr(sys, "argv", ["loader", "--trade-date", DAY.isoformat()])
    with pytest.raises(SourcePolicyError, match="POLICY_REVOKED"):
        module.main()
    calls.assert_not_called()


def test_r09_backfill_policy_refusal_terminal(monkeypatch):
    module = script("backfill_nse_equity_history")
    with pytest.raises(SourcePolicyError, match="POLICY_PENDING"):
        module._attempt_live_download(DAY)


@pytest.mark.parametrize("entry", ["orchestrator", "pipeline", "scheduled_ca"])
def test_r08_production_entry_pending_no_output(manager, monkeypatch, entry):
    from omegadata.pipelines.sequential_pipeline import OmegaDataSequentialPipeline
    from omegadata.track_a.orchestration import IngestionOrchestrator

    writes = Mock(side_effect=AssertionError("Pending source must not create output"))
    clients = Mock(side_effect=AssertionError("Pending source must not create client"))
    monkeypatch.setattr(Path, "mkdir", writes)
    monkeypatch.setattr(dm.httpx, "Client", clients)
    with pytest.raises(SourcePolicyError, match="POLICY_PENDING"):
        if entry == "orchestrator":
            IngestionOrchestrator().ingest_raw_source(KEY, DAY)
        elif entry == "pipeline":
            OmegaDataSequentialPipeline().run_track_a(DAY)
        else:
            OmegaDataSequentialPipeline().run_scheduled_corporate_action_collection(
                datetime(2026, 4, 13, 1, 30, tzinfo=UTC))
    writes.assert_not_called()
    clients.assert_not_called()


@pytest.mark.parametrize("url", ["https://example.invalid:4443/x", "http://example.invalid/x"])
def test_r10_probe_authority_before_curl(manager, monkeypatch, url):
    module = script("generate_source_probe_report")
    from omegadata.track_a.source_rights import authorize_source

    def authorize(request):
        return authorize_source(request, manager._policy_provider)

    monkeypatch.setattr(module, "authorize_source", authorize)
    subprocess = Mock(side_effect=AssertionError("Must refuse before curl"))
    temporary = Mock(side_effect=AssertionError("Must refuse before temporary output"))
    monkeypatch.setattr(module.subprocess, "run", subprocess)
    monkeypatch.setattr(module.tempfile, "TemporaryDirectory", temporary)
    with pytest.raises(SourcePolicyError):
        module._curl_probe(source_key=KEY, url=url, timeout_seconds=1)
    subprocess.assert_not_called()
    temporary.assert_not_called()


@pytest.mark.parametrize("revoke_after_bootstrap", [False, True])
def test_r10_probe_bootstrap_scoped_mock_and_refresh(synthetic_source_policy_provider, monkeypatch, revoke_after_bootstrap):
    module = script("generate_source_probe_report")
    from omegadata.track_a.source_rights import authorize_source

    active = synthetic_source_policy_provider()
    calls = []

    def authorize(request):
        return authorize_source(request, lambda: active)

    def fake_run(command, **kwargs):
        nonlocal active
        calls.append(command)
        if "-o" in command:
            Path(command[command.index("-o") + 1]).write_bytes(b"SYNTHETIC_TEST_ONLY")
            Path(command[command.index("-D") + 1]).write_text("HTTP/1.1 200 OK\nContent-Type: text/plain\n")
        if revoke_after_bootstrap and command[-1] == "https://www.nseindia.com/":
            item = updated(active.policies[0], status=PolicyStatus.REVOKED,
                           revoked_at=NOW, revocation_reason="SYNTHETIC_TEST_ONLY")
            active = registry(item)
        return Mock(returncode=0, stderr=b"")

    monkeypatch.setattr(module, "authorize_source", authorize)
    monkeypatch.setattr(module.subprocess, "run", fake_run)
    if revoke_after_bootstrap:
        with pytest.raises(SourcePolicyError, match="POLICY_REVOKED"):
            module._curl_probe(source_key=KEY, url="https://example.invalid/file", timeout_seconds=1, bootstrap_nse=True, offline_runner=fake_run)
        assert len(calls) == 1
    else:
        status, _, payload, _ = module._curl_probe(source_key=KEY, url="https://example.invalid/file", timeout_seconds=1, bootstrap_nse=True, offline_runner=fake_run)
        assert status == 200 and payload == b"SYNTHETIC_TEST_ONLY" and len(calls) == 2


def test_r12_forged_strings_are_only_technical_consistency(manager):
    # This explicitly proves the administrative trust limitation, never legal approval.
    item = manager._policy_provider().policies[0]
    forged = updated(item, approved_by="SYNTHETIC_TEST_ONLY forged principal",
                     approval_evidence_ref="SYNTHETIC_TEST_ONLY forged administrative string")
    from omegadata.track_a.source_rights import PolicyRequest, SourceOperation

    decision = registry(forged).evaluate(PolicyRequest(
        source_key=KEY, operation=SourceOperation.FETCH, decision_at=NOW,
        requested_transport=SourceTransport.HTTPX, requested_host="example.invalid"))
    assert decision.allowed  # Not a signature verifier; operational human gate remains mandatory.


def test_r08_pending_probe_bootstrap_no_temp_or_subprocess(monkeypatch):
    module = script("generate_source_probe_report")
    calls = Mock()
    monkeypatch.setattr(module.subprocess, "run", calls)
    monkeypatch.setattr(module.tempfile, "TemporaryDirectory", calls)
    with pytest.raises(SourcePolicyError, match="POLICY_PENDING"):
        module._curl_probe(source_key=KEY, url="https://example.invalid/file", timeout_seconds=1, bootstrap_nse=True)
    calls.assert_not_called()


def test_r13_bse_discovery_refreshes_before_get(synthetic_source_policy_provider, monkeypatch):
    active = synthetic_source_policy_provider()
    manager = DownloadManager(policy_provider=lambda: active, decision_clock=lambda: NOW)
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)
    client.get.return_value = Mock(text="", raise_for_status=Mock())

    def construct(**kwargs):
        nonlocal active
        item = next(p for p in active.policies if p.source_key == "BSE_EQUITY_BHAVCOPY")
        active = registry(updated(item, status=PolicyStatus.REVOKED,
                                  revoked_at=NOW, revocation_reason="SYNTHETIC_TEST_ONLY"))
        return client

    monkeypatch.setattr(dm.httpx, "Client", construct)
    with pytest.raises(SourcePolicyError, match="POLICY_REVOKED"):
        manager._discover_bse_equity_urls(DAY)
    client.get.assert_not_called()


def test_r13_simultaneous_source_scopes_and_refresh(synthetic_source_policy_provider, monkeypatch):
    original = synthetic_source_policy_provider()
    active = original
    manager = DownloadManager(policy_provider=lambda: active, decision_clock=lambda: NOW)
    barrier = threading.Barrier(2)
    calls = []
    client = Mock()
    client.get.side_effect = lambda *a, **kw: httpx.Response(200, content=b"SYNTHETIC_TEST_ONLY")

    def task(key):
        with manager._source_scope(key):
            barrier.wait(timeout=5)
            decision = manager._authorize_url(manager._policy_source.get(), "https://example.invalid", SourceTransport.HTTPX)
            calls.append(decision.source_key)
            manager._request_once(client, "https://example.invalid")
            return manager._policy_source.get()

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(task, [KEY, "MOSPI"])) == [KEY, "MOSPI"]
    assert sorted(calls) == sorted([KEY, "MOSPI"]) and client.get.call_count == 2
    assert manager._policy_source.get() == ""
    revoked = updated(original.policies[0], status=PolicyStatus.REVOKED,
                      revoked_at=NOW, revocation_reason="SYNTHETIC_TEST_ONLY")
    active = registry(revoked)
    with manager._source_scope(KEY), pytest.raises(SourcePolicyError, match="POLICY_REVOKED"):
        manager._request_once(client, "https://example.invalid")
    assert client.get.call_count == 2


def test_r16_harness_blocks_real_side_effects(tmp_path):
    """Only executed in the separately audited OD-01R runner."""
    if not os.environ.get("OD01R_DISPOSABLE_ROOT"):
        pytest.skip("Requires OD-01R guarded runner")
    import socket
    import sqlite3
    import subprocess

    with pytest.raises(RuntimeError):
        socket.getaddrinfo("example.invalid", 443)
    with pytest.raises(RuntimeError):
        subprocess.run([sys.executable, "-c", "raise SystemExit(99)"])
    with pytest.raises(RuntimeError):
        (REPO / "od01r-must-not-write.txt").write_text("blocked")
    with pytest.raises(RuntimeError):
        sqlite3.connect(str(REPO / "od01r-must-not-create.sqlite"))
    assert not (REPO / "od01r-must-not-write.txt").exists()
    assert not (REPO / "od01r-must-not-create.sqlite").exists()
