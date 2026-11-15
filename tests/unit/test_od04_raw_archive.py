"""OD04 synthetic-only byte identity, transaction and rights contracts."""
from __future__ import annotations

import errno
import hashlib
import importlib
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from omegadata.track_a.download_manager import DownloadManager, FetchResult
from omegadata.track_a.source_rights import SourcePolicyError

KEY = "NSE_EQUITY_BHAVCOPY"
DAY = date(2026, 4, 10)
NOW = datetime(2026, 11, 15, 12, tzinfo=UTC)


@pytest.fixture()
def api():
    # A missing proposed API is NOT evidence of a defect in old application code.
    return importlib.import_module("omegadata.track_a.raw_archive")


@pytest.fixture()
def service(api, tmp_path, synthetic_source_policy_provider):
    return api.RawArchive(tmp_path / "archive", policy_provider=synthetic_source_policy_provider)


def request(api, **updates):
    fields = {"source_key": KEY, "business_date": DAY, "observed_at": NOW,
              "source_era": "2019_present", "source_mode": "SYNTHETIC_TEST_ONLY",
              "parser_schema": "test/v1", "payload_state": "HTTP_RECEIVED",
              "transport": "HTTPX", "original_url": "https://example.invalid/file",
              "final_url": "https://example.invalid/file", "origin_ref": "SYNTHETIC_TEST_ONLY",
              "operation_id": "1" * 32}
    fields.update(updates)
    return api.ObservationRequest(**fields)


def manager_fixture(tmp_path, monkeypatch, provider, body):
    manager = DownloadManager(policy_provider=provider)
    manager.raw_root = tmp_path / "legacy"
    manager.seed_raw_root = tmp_path / "seed"
    monkeypatch.setattr(manager, "_candidate_urls", lambda *_: ["https://example.invalid/data"])
    monkeypatch.setattr(manager, "_fetch_candidate", lambda *a, **kw: FetchResult(body, 200, "application/zip", "httpx", 1))
    return manager


@pytest.mark.parametrize("requirement", ["full_hash", "separate_events", "existing_corruption", "partial_failure"])
def test_a01_a02_a06_a12_negative_first_old_storage(
    tmp_path, monkeypatch, synthetic_source_policy_provider, synthetic_equity_zip, requirement
):
    """Real old-code behavior, not a missing-module/import failure."""
    body = synthetic_equity_zip(DAY)
    manager = manager_fixture(tmp_path, monkeypatch, synthetic_source_policy_provider, body)
    try:
        api = importlib.import_module("omegadata.track_a.raw_archive")
    except ModuleNotFoundError:
        api = None
    if api is not None:
        manager.raw_archive = api.RawArchive(tmp_path / "archive", policy_provider=synthetic_source_policy_provider)
    first = manager.download(KEY, DAY, use_cache=False)
    if requirement == "full_hash":
        assert first.path.name == hashlib.sha256(body).hexdigest()
    elif requirement == "separate_events":
        second = manager.download(KEY, DAY, use_cache=False)
        assert first.manifest_path != second.manifest_path
        assert first.path == second.path
    elif requirement == "existing_corruption":
        first.path.write_bytes(b"SYNTHETIC_CORRUPTION")
        with pytest.raises(RuntimeError, match="INTEGRITY"):
            manager.download(KEY, DAY, use_cache=False)
    else:
        if api is None:
            original = Path.write_text
            def fail_manifest(path, *a, **kw):
                if str(path).endswith(".manifest.json"):
                    raise OSError(errno.ENOSPC, "synthetic disk full")
                return original(path, *a, **kw)
            monkeypatch.setattr(Path, "write_text", fail_manifest)
        else:
            manager.raw_archive.fault = lambda phase: (_ for _ in ()).throw(OSError(errno.ENOSPC, "synthetic")) if phase == "after_stage" else None
        # Fresh storage namespace, not already-committed fixture above.
        manager.raw_root = tmp_path / "fresh-legacy"
        with pytest.raises((OSError, RuntimeError)):
            manager.download(KEY, DAY, use_cache=False)
        assert not list(manager.raw_root.rglob("*"))


def test_a01_a02_a03_a23_exact_bytes_events_and_historical_replay(api, service):
    one = service.put(b"first", request(api))
    two = service.put(b"first", request(api, operation_id="2" * 32))
    three = service.put(b"later", request(api, operation_id="3" * 32))
    assert one.object.sha256 == hashlib.sha256(b"first").hexdigest()
    assert one.object.relative_path.endswith(one.object.sha256)
    assert one.object == two.object and one.observation_id != two.observation_id
    assert three.object.sha256 != one.object.sha256
    for record, expected in [(one, b"first"), (two, b"first"), (three, b"later")]:
        body, obs = service.read_verified(record.observation_id, KEY, DAY)
        assert body == expected and hashlib.sha256(body).hexdigest() == record.object.sha256
        assert obs.published_at is None and obs.source_reference == "SOURCE_REFERENCE_PENDING"
        assert obs.request == request(api, operation_id=record.observation_id)
    assert len(list((service.root / "objects").rglob("[0-9a-f]" * 64))) == 2


def test_a04_a05_idempotence_conflict_and_frozen_models(api, service):
    first = service.put(b"a", request(api))
    assert service.put(b"a", request(api)) == first
    for body, req in [(b"b", request(api)), (b"a", request(api, origin_ref="other"))]:
        with pytest.raises(RuntimeError, match="CONFLICT"):
            service.put(body, req)
    assert service.read_verified(first.observation_id, KEY, DAY)[0] == b"a"
    with pytest.raises(ValueError):
        first.object.size = 99


@pytest.mark.parametrize("phase", ["before_stage", "after_stage", "after_object", "after_observation", "before_commit"])
def test_a06_a07_a08_fault_boundaries_recover_without_promoting(api, service, phase):
    def fault(at):
        if phase == at:
            raise OSError(errno.EIO, "SYNTHETIC_TEST_ONLY")
    service.fault = fault
    with pytest.raises(RuntimeError, match="STORAGE_FAILURE"):
        service.put(b"candidate", request(api))
    with pytest.raises(RuntimeError, match="NOT_COMMITTED"):
        service.read_verified("1" * 32, KEY, DAY)
    before = {p.relative_to(service.root): p.read_bytes() for p in service.root.rglob("*") if p.is_file()}
    inventory = service.recover_staging()
    assert inventory["committed"] == 0
    assert before == {p.relative_to(service.root): p.read_bytes() for p in service.root.rglob("*") if p.is_file()}
    service.fault = None
    committed = service.put(b"candidate", request(api))
    assert service.read_verified(committed.observation_id, KEY, DAY)[0] == b"candidate"


def test_a09_a21_thread_writers_and_reader(api, service):
    def write(n):
        item = service.put(b"same", request(api, operation_id=f"{n:032x}"))
        assert service.read_verified(item.observation_id, KEY, DAY)[0] == b"same"
        return item
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(write, range(12)))
    assert len({r.observation_id for r in rows}) == 12
    assert len({r.object for r in rows}) == 1


@pytest.mark.parametrize("target", ["object", "observation", "commit", "length", "version", "duplicate"])
def test_a12_a14_corruption_refuses(api, service, target):
    item = service.put(b"exact", request(api))
    object_path = service.root / item.object.relative_path
    obs_path = service.observation_path(item.observation_id)
    commit_path = service.commit_path(item.observation_id)
    if target == "object":
        object_path.write_bytes(b"wrong")
    elif target == "observation":
        obs_path.write_text("{}")
    elif target == "commit":
        commit_path.write_text("{")
    else:
        body = json.loads(commit_path.read_text())
        if target == "length":
            body["object"]["size"] += 1
        elif target == "version":
            body["schema_version"] = "raw-commit/v999"
        encoded = json.dumps(body)
        if target == "duplicate":
            encoded = '{"state":"COMMITTED",' + encoded[1:]
        commit_path.write_text(encoded)
    with pytest.raises(RuntimeError, match="INTEGRITY"):
        service.read_verified(item.observation_id, KEY, DAY)


@pytest.mark.parametrize("field,value", [("source_key", "../escape"), ("operation_id", "../escape"), ("operation_id", "C:\\escape"), ("operation_id", "\\\\server\\share"), ("source_mode", "RELEASE_APPROVED"), ("observed_at", "2026-01-01T00:00:00"), ("attempts", -1), ("origin_ref", "../secret"), ("published_at", "2000-01-01T00:00:00Z")])
def test_a13_a15_a24_invalid_identity_before_storage(api, tmp_path, field, value):
    with pytest.raises(ValueError):
        request(api, **{field: value})
    assert not (tmp_path / "archive").exists()


@pytest.mark.parametrize("part", ["objects", "observations", "commits", "staging"])
def test_a13_real_directory_link_escape(api, service, tmp_path, part):
    outside = tmp_path / "outside"
    outside.mkdir()
    service.root.mkdir()
    link = service.root / part
    if os.name == "nt":
        import _winapi
        _winapi.CreateJunction(str(outside), str(link))
    else:
        link.symlink_to(outside, target_is_directory=True)
    with pytest.raises(RuntimeError, match="INTEGRITY"):
        service.put(b"bytes", request(api))
    assert list(outside.iterdir()) == []


def test_a16_pending_before_write_or_read(api, tmp_path):
    service = api.RawArchive(tmp_path / "pending")
    with pytest.raises(SourcePolicyError):
        service.put(b"a", request(api))
    with pytest.raises(SourcePolicyError):
        service.read_verified("1" * 32, KEY, DAY)
    assert not service.root.exists()


def test_a16_revocation_before_replay(api, service):
    item = service.put(b"a", request(api))
    from omegadata.track_a.source_rights import load_policy_register
    service.policy_provider = load_policy_register
    with pytest.raises(SourcePolicyError):
        service.read_verified(item.observation_id, KEY, DAY)


@pytest.mark.parametrize("length", [0, 17])
def test_a19_payload_and_total_budget(api, service, length):
    service.max_payload = 16
    with pytest.raises(RuntimeError, match="BUDGET_EXCEEDED"):
        service.put(b"x" * length, request(api))
    service.max_payload = 1024
    service.max_bytes = 1
    with pytest.raises(RuntimeError, match="BUDGET_EXCEEDED"):
        service.put(b"a", request(api))
    assert not list(service.root.glob("commits/*.json"))


@pytest.mark.parametrize("operation", ["fsync", "link"])
@pytest.mark.parametrize("number", [errno.ENOSPC, errno.EACCES, errno.EIO])
def test_a20_storage_faults_typed_no_success(api, service, monkeypatch, operation, number):
    def fail(*a, **kw):
        raise OSError(number, "synthetic")
    monkeypatch.setattr(os, operation, fail)
    with pytest.raises(RuntimeError, match="STORAGE_FAILURE"):
        service.put(b"a", request(api))
    assert not list(service.root.glob("commits/*.json"))


def test_a22_url_confidentiality_and_a24_policy(api, service):
    req = request(api, original_url="https://u:SYNTHETIC_SECRET@example.invalid/token/SYNTHETIC_SECRET?api_key=SYNTHETIC_SECRET")
    item = service.put(b"safe", req)
    _, obs = service.read_verified(item.observation_id, KEY, DAY)
    assert "SYNTHETIC_SECRET" not in obs.model_dump_json()
    assert obs.request.observed_at == NOW and obs.request.business_date == DAY
    assert obs.policy_decisions[-1].revision_hash and obs.policy_decisions[-1].operation.value == "STORE_RAW"
    with pytest.raises(RuntimeError, match="INTEGRITY"):
        service.read_verified(item.observation_id, KEY, date(2026, 4, 9))


def test_a17_a18_optin_cache_miss_no_effect(api, tmp_path, synthetic_source_policy_provider):
    archive = api.RawArchive(tmp_path / "archive", policy_provider=synthetic_source_policy_provider)
    manager = DownloadManager(policy_provider=synthetic_source_policy_provider, raw_archive=archive)
    manager.raw_root = tmp_path / "legacy"
    manager.seed_raw_root = tmp_path / "seed"
    manager._fetch_candidate = Mock(side_effect=AssertionError("must not fetch"))
    with pytest.raises(RuntimeError, match="CACHE_MISS"):
        manager.download(KEY, DAY, cache_only=True)
    assert not archive.root.exists() and not manager.raw_root.exists()


def test_a17_legacy_facade_is_read_only(api, tmp_path, monkeypatch, synthetic_source_policy_provider, synthetic_equity_zip):
    body = synthetic_equity_zip(DAY)
    manager = manager_fixture(tmp_path, monkeypatch, synthetic_source_policy_provider, body)
    old = manager.download(KEY, DAY, use_cache=False)
    before = {p: p.read_bytes() for p in manager.raw_root.rglob("*") if p.is_file()}
    manager.raw_archive = api.RawArchive(tmp_path / "archive", policy_provider=synthetic_source_policy_provider)
    cached = manager.download(KEY, DAY, cache_only=True)
    assert cached.path == old.path and cached.archive_state == "LEGACY_UNVERIFIED"
    assert cached.observation_id is None and not manager.raw_archive.root.exists()
    assert before == {p: p.read_bytes() for p in manager.raw_root.rglob("*") if p.is_file()}


def test_a15_synthetic_cannot_be_relabelled(api, service):
    candidate = request(api)
    with pytest.raises(ValueError):
        service.put(b"a", candidate.model_copy(update={"source_mode": "PROVIDER_OBSERVED_UNVERIFIED"}))
    assert not service.root.exists()


@pytest.mark.parametrize("field,value", [("sha256", "a" * 12), ("size", True), ("relative_path", "../escape")])
def test_a13_strict_object_contract(api, field, value):
    digest = hashlib.sha256(b"a").hexdigest()
    fields = {"sha256": digest, "size": 1, "relative_path": f"objects/sha256/{digest[:2]}/{digest[2:4]}/{digest}"}
    fields[field] = value
    with pytest.raises(ValueError):
        api.RawObject(**fields)


def test_a21_reader_during_publication(api, service):
    import threading
    ready, release = threading.Event(), threading.Event()
    def pause(phase):
        if phase == "after_observation":
            ready.set()
            assert release.wait(3)
    service.fault = pause
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(service.put, b"exact", request(api))
        assert ready.wait(3)
        try:
            for _ in range(10):
                with pytest.raises(RuntimeError, match="NOT_COMMITTED"):
                    service.read_verified("1" * 32, KEY, DAY)
        finally:
            release.set()
        item = future.result(timeout=4)
    assert service.read_verified(item.observation_id, KEY, DAY)[0] == b"exact"


def test_a16_revocation_at_commit_boundary(api, service):
    from omegadata.track_a.source_rights import load_policy_register
    def revoke(phase):
        if phase == "before_commit":
            service.policy_provider = load_policy_register
    service.fault = revoke
    with pytest.raises(SourcePolicyError):
        service.put(b"exact", request(api))
    assert not list((service.root / "commits").glob("*.json"))


def test_a19_metadata_and_entry_budget(api, service):
    service.max_metadata = 8
    with pytest.raises(RuntimeError, match="BUDGET_EXCEEDED"):
        service.put(b"exact", request(api))
    service.max_metadata = 65536
    service.max_entries = 1
    with pytest.raises(RuntimeError, match="BUDGET_EXCEEDED"):
        service.put(b"exact", request(api))


def test_a16_read_consumer_scope_enforced(api, service, synthetic_source_policy_provider):
    from omegadata.track_a.source_rights import SourceOperation, SourcePolicy, SourcePolicyRegister
    item = service.put(b"exact", request(api))
    policies = []
    for policy in synthetic_source_policy_provider().policies:
        fields = policy.model_dump()
        fields["permitted_operations"] = (SourceOperation.READ_CACHED,)
        revised = SourcePolicy.model_validate(fields)
        policies.append(revised.model_copy(update={"revision_hash": revised.canonical_hash()}))
    register = SourcePolicyRegister(schema_version="source-policy/v1", policies=tuple(policies))
    service.policy_provider = lambda: register
    with pytest.raises(SourcePolicyError):
        service.read_verified(item.observation_id, KEY, DAY, SourceOperation.DERIVE)


def test_a18_dry_run_migration_and_cli_verifier(api, tmp_path, monkeypatch, synthetic_source_policy_provider, synthetic_equity_zip, capsys):
    import runpy
    import sys
    body = synthetic_equity_zip(DAY)
    manager = manager_fixture(tmp_path, monkeypatch, synthetic_source_policy_provider, body)
    manager.download(KEY, DAY, use_cache=False)
    before = {p: p.read_bytes() for p in manager.raw_root.rglob("*") if p.is_file()}
    monkeypatch.setattr("omegadata.track_a.download_manager.load_policy_register", synthetic_source_policy_provider)
    monkeypatch.setattr(sys, "argv", ["plan_legacy_raw_import", str(manager.raw_root), KEY, DAY.isoformat()])
    runpy.run_path(str(Path(__file__).resolve().parents[2] / "scripts/plan_legacy_raw_import.py"), run_name="__main__")
    result = json.loads(capsys.readouterr().out)
    assert result["action"] == "DRY_RUN_ONLY" and result["sha256"] == hashlib.sha256(body).hexdigest()
    assert before == {p: p.read_bytes() for p in manager.raw_root.rglob("*") if p.is_file()}
    monkeypatch.setattr("omegadata.track_a.raw_archive.load_policy_register", synthetic_source_policy_provider)
    service = api.RawArchive(tmp_path / "archive")
    item = service.put(body, request(api))
    monkeypatch.setattr(sys, "argv", ["verify_raw_archive", str(service.root), item.observation_id, KEY, DAY.isoformat()])
    runpy.run_path(str(Path(__file__).resolve().parents[2] / "scripts/verify_raw_archive.py"), run_name="__main__")
    assert json.loads(capsys.readouterr().out)["sha256"] == item.object.sha256


def test_a04_policy_identity_change_is_not_idempotent(api, service, synthetic_source_policy_provider):
    from omegadata.track_a.source_rights import SourcePolicy, SourcePolicyRegister
    service.put(b"exact", request(api))
    policies = []
    for policy in synthetic_source_policy_provider().policies:
        fields = policy.model_dump()
        fields["change_reason"] = "SYNTHETIC_TEST_ONLY changed legal identity"
        revised = SourcePolicy.model_validate(fields)
        policies.append(revised.model_copy(update={"revision_hash": revised.canonical_hash()}))
    register = SourcePolicyRegister(schema_version="source-policy/v1", policies=tuple(policies))
    service.policy_provider = lambda: register
    with pytest.raises(RuntimeError, match="CONFLICT"):
        service.put(b"exact", request(api))


def test_a24_structural_state_requires_actual_validator(api, service):
    with pytest.raises(RuntimeError):
        service.put(b"<html>Access denied</html>", request(api, payload_state="PAYLOAD_STRUCTURALLY_VALID"))
    assert not service.root.exists()


@pytest.mark.parametrize("state", ["REVOKED", "MISSING"])
def test_a16_explicit_revoked_or_missing_before_io(api, tmp_path, synthetic_source_policy_provider, state):
    from omegadata.track_a.source_rights import SourcePolicy, SourcePolicyRegister
    policies = []
    for policy in synthetic_source_policy_provider().policies:
        if state == "MISSING" and policy.source_key == KEY:
            continue
        fields = policy.model_dump()
        if state == "REVOKED":
            fields.update(status="REVOKED", revoked_at=NOW, revocation_reason="SYNTHETIC_TEST_ONLY")
        revised = SourcePolicy.model_validate(fields)
        policies.append(revised.model_copy(update={"revision_hash": revised.canonical_hash()}))
    register = SourcePolicyRegister(schema_version="source-policy/v1", policies=tuple(policies))
    archive = api.RawArchive(tmp_path / "archive", policy_provider=lambda: register)
    for operation in [lambda: archive.put(b"a", request(api)), lambda: archive.read_verified("1" * 32, KEY, DAY)]:
        with pytest.raises(SourcePolicyError, match="POLICY_REVOKED" if state == "REVOKED" else "MISSING_POLICY"):
            operation()
    assert not archive.root.exists()


def test_a12_a23_scan_is_read_only_deterministic_and_refuses_corruption(api, service):
    one = service.put(b"one", request(api))
    service.put(b"two", request(api, operation_id="2" * 32))
    before = {p: p.read_bytes() for p in service.root.rglob("*") if p.is_file()}
    first = service.scan_verified(KEY, DAY)
    assert len(first["observations"]) == 2 and first == service.scan_verified(KEY, DAY)
    assert before == {p: p.read_bytes() for p in service.root.rglob("*") if p.is_file()}
    (service.root / one.object.relative_path).write_bytes(b"tampered")
    with pytest.raises(RuntimeError, match="INTEGRITY"):
        service.scan_verified(KEY, DAY)
