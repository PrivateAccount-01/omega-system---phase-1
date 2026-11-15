"""OD04R independent adversarial contracts; all payloads are synthetic."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from omegadata.track_a.raw_archive import ArchiveError, ObservationRequest, RawArchive

KEY = "NSE_EQUITY_BHAVCOPY"
DAY = date(2026, 4, 10)


def request(**changes):
    fields = dict(source_key=KEY, business_date=DAY,
                  observed_at=datetime(2026, 11, 15, 12, tzinfo=UTC),
                  source_era="2019_present", source_mode="SYNTHETIC_TEST_ONLY",
                  parser_schema="test/v1", payload_state="HTTP_RECEIVED",
                  transport="HTTPX", original_url="https://example.invalid/file",
                  final_url="https://example.invalid/file", origin_ref="SYNTHETIC_TEST_ONLY",
                  operation_id="a" * 32)
    return ObservationRequest(**(fields | changes))


@pytest.fixture()
def archive(tmp_path, synthetic_source_policy_provider):
    return RawArchive(tmp_path / "archive", policy_provider=synthetic_source_policy_provider)


@pytest.mark.parametrize("layout,reason", [
    ("missing", "NOT_FOUND"), ("empty", "EMPTY_ARCHIVE"),
    ("staging", "EMPTY_ARCHIVE"), ("orphan", "EMPTY_ARCHIVE"),
    ("root_file", "INTEGRITY"), ("commits_file", "INTEGRITY"),
])
def test_r01_absence_is_never_verified(archive, layout, reason):
    if layout == "root_file":
        archive.root.write_bytes(b"SYNTHETIC_TEST_ONLY")
    elif layout != "missing":
        archive.root.mkdir()
        if layout == "staging":
            (archive.root / "staging").mkdir()
            (archive.root / "staging" / "pending").write_bytes(b"SYNTHETIC_TEST_ONLY")
        elif layout == "orphan":
            (archive.root / "observations").mkdir()
            (archive.root / "observations" / ("a" * 32 + ".json")).write_text("{}")
        elif layout == "commits_file":
            (archive.root / "commits").write_bytes(b"SYNTHETIC_TEST_ONLY")
    with pytest.raises(ArchiveError, match=reason):
        archive.scan_verified(KEY, DAY)


def test_r01_disappears_after_inventory(archive, monkeypatch):
    archive.root.mkdir()
    original = archive._inventory

    def move_after_inventory():
        result = original()
        archive.root.rename(archive.root.with_name("moved-disposable-archive"))
        return result

    monkeypatch.setattr(archive, "_inventory", move_after_inventory)
    with pytest.raises(ArchiveError, match="NOT_FOUND"):
        archive.scan_verified(KEY, DAY)


def test_r01_walk_error_cannot_hide_existing_evidence(archive, monkeypatch):
    archive.put(b"SYNTHETIC_TEST_ONLY", request())

    def denied_walk(*args, **kwargs):
        callback = kwargs.get("onerror")
        if callback:
            callback(PermissionError("SYNTHETIC_TEST_ONLY"))
        return iter(())

    monkeypatch.setattr("omegadata.track_a.raw_archive.os.walk", denied_walk)
    with pytest.raises(ArchiveError, match="INTEGRITY"):
        archive.scan_verified(KEY, DAY)


def test_r01_expected_count_is_external_contract(archive):
    archive.root.mkdir()
    result = archive.scan_verified(KEY, DAY, expected_count=0)
    assert result["schema_version"] == "raw-verification/v2"
    assert result["verification"] == "EXPECTED_COUNT_MATCHED"
    assert result["observations"] == []
    with pytest.raises(ArchiveError, match="COUNT_MISMATCH"):
        archive.scan_verified(KEY, DAY, expected_count=1)
    archive.put(b"SYNTHETIC_TEST_ONLY", request())
    with pytest.raises(ArchiveError, match="COUNT_MISMATCH"):
        archive.scan_verified(KEY, DAY, expected_count=0)
    assert len(archive.scan_verified(KEY, DAY, expected_count=1)["observations"]) == 1


@pytest.mark.parametrize("value", [-1, True, "1"])
def test_r01_invalid_expectation(archive, value):
    with pytest.raises(ArchiveError, match="INPUT_INVALID"):
        archive.scan_verified(KEY, DAY, expected_count=value)
    assert not archive.root.exists()


@pytest.mark.parametrize("layout", ["missing", "staging", "orphan"])
def test_r01_expected_empty_does_not_hide_incomplete_storage(archive, layout):
    if layout != "missing":
        (archive.root / layout).mkdir(parents=True)
        (archive.root / layout / "pending").write_bytes(b"SYNTHETIC_TEST_ONLY")
    with pytest.raises(ArchiveError, match="NOT_FOUND|EMPTY_ARCHIVE"):
        archive.scan_verified(KEY, DAY, expected_count=0)


def test_r09_existing_wrong_size_object_refuses_without_overwrite(archive):
    payload = b"SYNTHETIC_TEST_ONLY-candidate"
    digest = hashlib.sha256(payload).hexdigest()
    path = archive.root / f"objects/sha256/{digest[:2]}/{digest[2:4]}/{digest}"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"wrong")
    with pytest.raises(ArchiveError, match="INTEGRITY"):
        archive.put(payload, request())
    assert path.read_bytes() == b"wrong"
    assert not list(archive.root.glob("commits/*.json"))


def test_r18_independent_link_oracle_and_missing_object(archive):
    payload = b"SYNTHETIC_TEST_ONLY-byte-oracle"
    digest = hashlib.sha256(payload).hexdigest()
    first = archive.put(payload, request())
    second = archive.put(payload, request(operation_id="b" * 32))
    assert first.object == second.object
    markers = list(archive.root.glob("commits/*.json"))
    assert len(markers) == 2
    objects = [p for p in archive.root.glob("objects/sha256/*/*/*") if p.is_file()]
    assert len(objects) == 1 and objects[0].read_bytes() == payload
    for marker in markers:
        commit = json.loads(marker.read_bytes())
        raw = (archive.root / "observations" / marker.name).read_bytes()
        obs = json.loads(raw)
        assert commit["observation_id"] == obs["observation_id"] == marker.stem
        assert commit["observation_sha256"] == hashlib.sha256(raw).hexdigest()
        assert commit["object"] == obs["object"]
        assert commit["object"]["sha256"] == digest
        assert commit["object"]["size"] == len(payload)
    objects[0].rename(objects[0].with_name("moved-disposable-object"))
    with pytest.raises(ArchiveError, match="INTEGRITY"):
        archive.scan_verified(KEY, DAY)


def test_r18_namespace_mixing_refuses(archive):
    archive.put(b"SYNTHETIC_TEST_ONLY-one", request())
    archive.put(b"SYNTHETIC_TEST_ONLY-two", request(operation_id="b" * 32, business_date=date(2026, 4, 9)))
    with pytest.raises(ArchiveError, match="INTEGRITY"):
        archive.scan_verified(KEY, DAY)
