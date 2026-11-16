"""W01-W24. Filesystem canaries contain no market observations."""

import hashlib
import importlib
import json
import os
import socket
import subprocess
import sys
from pathlib import Path

import pytest
from test_od05v_local_presence import fixture, repin


def harness():
    return importlib.import_module("od05w_safe_harness")


def presence():
    return importlib.import_module("omegadata.parsers.local_archive_presence")


def scan(repo, pins, **kw):
    from omegadata.parsers.archive_candidate_inventory import ExpectedMetadata

    return presence().scan_presence(
        repo, "seed", expected=ExpectedMetadata(tuple(pins)), version=2, **kw
    )


def test_w01_old_helper_and_glob_rejected_before_open(tmp_path, monkeypatch):
    h = harness()
    monkeypatch.setattr(Path, "open", lambda *a, **k: pytest.fail("opened before preflight"))
    for name in ("data/**/*.zip", "docs/od05r/control.py", "src/*.py"):
        with pytest.raises(ValueError):
            h.preflight(tmp_path, [name], {name: "CODE"})


def test_w02_exact_allowlist(tmp_path):
    h = harness()
    (tmp_path / "ok.py").write_text("# non-market code\n")
    assert len(h.preflight(tmp_path, ["ok.py"], {"ok.py": "CODE"})) == 1
    for name in ("unknown.py", "unknown.xyz"):
        with pytest.raises(ValueError):
            h.preflight(tmp_path, [name], {"ok.py": "CODE"})


@pytest.mark.parametrize(
    "name", ["x.zip", "x.csv", "x.parquet", "x.db", ".env", "x.key", "x.zip.py"]
)
def test_w03_denied_inside_allowed_tree(tmp_path, name):
    h = harness()
    (tmp_path / name).touch()
    with pytest.raises(ValueError):
        h.preflight(tmp_path, [name], {name: "CODE"})


def test_w04_actual_guard_denials():
    assert os.environ.get("OD05W_GUARD_ACTIVE") == "1"
    with pytest.raises((RuntimeError, PermissionError)):
        subprocess.run([sys.executable, "-c", "pass"], check=True)
    with pytest.raises((RuntimeError, PermissionError)):
        socket.create_connection(("example.invalid", 443))
    with pytest.raises((RuntimeError, PermissionError)):
        Path(os.environ["OD05W_FORBIDDEN_CANARY"]).read_bytes()
    with pytest.raises((RuntimeError, PermissionError)):
        Path(os.environ["OD05W_FORBIDDEN_WRITE"]).write_text("NON_MARKET_CANARY")


def test_w04_original_boundary_covered():
    # A benign instruction file proves the boundary without opening a payload.
    # No actual market file is used to reproduce a guard defect.
    target = Path(os.environ["OD05W_ORIGINAL_BOUNDARY"]) / "AGENTS.md"
    with pytest.raises((RuntimeError, PermissionError)):
        target.read_bytes()


def test_w04_external_retained_copy_boundary():
    # Newly created harmless sentinel, never an actual retained incident file.
    with pytest.raises((RuntimeError, PermissionError)):
        Path(os.environ["OD05W_EXTERNAL_CANARY"]).read_bytes()


def test_w05_hardlinked_copy_source_refused(tmp_path):
    h = harness()
    (tmp_path / "a.py").touch()
    os.link(tmp_path / "a.py", tmp_path / "b.py")
    with pytest.raises(ValueError):
        h.preflight(tmp_path, ["a.py"], {"a.py": "CODE"})


@pytest.mark.parametrize("kind", ["private", "linked_root"])
def test_w05_copy_root_ancestors_refused(tmp_path, kind):
    h = harness()
    source = tmp_path / (".env-private" if kind == "private" else "source")
    source.mkdir()
    (source / "a.py").write_text("# NON_MARKET_CANARY\n")
    root = source
    if kind == "linked_root":
        root = tmp_path / "linked"
        if os.name == "nt":
            import _winapi

            _winapi.CreateJunction(str(source), str(root))
        else:
            root.symlink_to(source, target_is_directory=True)
    with pytest.raises(ValueError, match="COPY_PATH_UNSAFE"):
        h.preflight(root, ["a.py"], {"a.py": "CODE"})


def test_w06_historical_incident_immutable():
    record = json.loads((Path.cwd() / "od05w_inputs/incident.json").read_text())
    assert record["status"] == "NOT_SELF_APPROVED"
    assert len(record["raw_files"]) == 39
    assert sum(r["bytes"] for r in record["raw_files"]) == 6135515


def test_w07_hardlink_physically_present(tmp_path):
    repo, _, payload, pins = fixture(tmp_path)
    os.link(payload, tmp_path / "second-link")
    # Existing v1 defect is executable independently of the absent v2 API.
    old = presence().scan_presence(repo, "seed", expected=presence().ExpectedMetadata(tuple(pins)))
    assert old["counts"]["regular_file"] == 1
    row = scan(repo, pins)["rows"][0]
    assert row["metadata_discovery_state"] == "PRESENT_HARDLINK_SIZE_MATCHED"
    assert row["path_exists"] and row["regular_file"]
    assert row["filesystem_size_matches_manifest"] is True
    assert row["content_inspection_eligibility"] is False


def test_w07_existing_physical_count_defect(tmp_path):
    repo, _, payload, pins = fixture(tmp_path)
    os.link(payload, tmp_path / "second-link")
    kwargs = {"version": 2} if hasattr(presence(), "PresenceObservation") else {}
    result = presence().scan_presence(
        repo, "seed", expected=presence().ExpectedMetadata(tuple(pins)), **kwargs
    )
    assert result["counts"]["present"] == result["counts"]["size_matches_manifest"] == 1


def test_w08_hardlink_mismatch(tmp_path):
    repo, _, payload, pins = fixture(tmp_path)
    os.link(payload, tmp_path / "link")
    with payload.open("r+b") as stream:
        stream.truncate(1)
    row = scan(repo, pins)["rows"][0]
    assert row["state"] == "SIZE_MISMATCH" and row["link_class"] == "HARDLINKED"


def test_w09_presence_not_permission(tmp_path):
    repo, _, _, pins = fixture(tmp_path)
    result = scan(repo, pins)
    assert result["counts"]["present"] == 1
    assert result["counts"]["content_eligible"] == 0
    assert result["payload_bytes_read"] == result["market_rows_independently_verified"] == 0


def test_w10_fresh_original_ledger():
    body = json.loads((Path.cwd() / "od05w_inputs/original-stat.json").read_text())
    assert body["evidence_class"] == "LOCAL_META"
    assert body["phase"] == "OD05W" and body["counts"] == {
        "seed": 3596,
        "cache": 30,
        "present": 3626,
        "size_matched": 3626,
        "hardlinked": 2760,
        "single_link": 866,
        "missing": 0,
    }


def test_w11_historical_claims_unchanged():
    samples = json.loads((Path.cwd() / "od05w_inputs/original-stat.json").read_text())["samples"]
    assert samples["2020-01-02"]["era_state"] == "ERA_CONFLICT_2020_REFERENCE_PENDING"
    assert samples["2011-06-22"]["lineage"] == "PHASE2_REPOSITORY_CLAIM"
    assert samples["2024-07-23"]["claim_format"] == "UDIFF_URL_CLAIM"


@pytest.mark.parametrize(
    "claim", ["../x.zip", "//host/share/x.zip", "C:/x.zip", "data/raw/x.zip:ads", "DATA/x.zip"]
)
def test_w12_unsafe_paths(tmp_path, claim):
    repo, meta, _, _ = fixture(tmp_path)
    body = json.loads(meta.read_text())
    body["artifact_path"] = claim
    meta.write_text(json.dumps(body))
    assert scan(repo, repin(meta, repo))["rows"][0]["path_exists"] is False


def test_w13_canonical_digest_and_redaction(tmp_path):
    repo, _, _, pins = fixture(tmp_path)
    a, b = scan(repo, pins), scan(repo, list(reversed(pins)))
    assert a["semantic_sha256"] == b["semantic_sha256"]
    assert str(tmp_path) not in json.dumps(a)


def test_w14_budgets(tmp_path):
    repo, _, _, pins = fixture(tmp_path)
    with pytest.raises(presence().InventoryError, match="BUDGET"):
        scan(repo, pins, limits=presence().ScanLimits(max_entries=1))
    with pytest.raises(presence().InventoryError, match="BUDGET"):
        presence().ScanLimits(max_seconds=31)


def test_w15_profile_without_limit_relaxation(tmp_path):
    repo, _, _, pins = fixture(tmp_path)
    profile = {}
    scan(repo, pins, profile=profile)
    assert profile["max_seconds"] == 30
    assert profile["metadata_reads"] == 1 and profile["entries"] > 0
    assert all(
        profile[k] >= 0 for k in ("enumeration_seconds", "read_seconds", "correlation_seconds")
    )


def test_w16_immutable_observation_invalidated(tmp_path):
    repo, meta, _, pins = fixture(tmp_path)
    observation = presence().PresenceObservation(
        repo, "seed", presence().ExpectedMetadata(tuple(pins))
    )
    a = observation.get()
    a["rows"].clear()
    assert len(observation.get()["rows"]) == 1 and observation.scan_count == 1
    meta.write_bytes(meta.read_bytes() + b" ")
    with pytest.raises(presence().InventoryError, match="CHANGED"):
        observation.get()


def test_w17_native_link_refusal(tmp_path):
    repo, meta, payload, pins = fixture(tmp_path)
    target = tmp_path / "NON_MARKET_CANARY"
    target.touch()
    if os.name == "nt":
        import _winapi

        link = payload.parent / "junction"
        _winapi.CreateJunction(str(tmp_path), str(link))
        body = json.loads(meta.read_text())
        body["artifact_path"] = link.relative_to(repo).as_posix() + "/NON_MARKET_CANARY.zip"
        meta.write_text(json.dumps(body))
        pins = repin(meta, repo)
    else:
        payload.unlink()
        payload.symlink_to(target)
    assert scan(repo, pins)["rows"][0]["path_exists"] is False


def test_w18_canary_not_financial_evidence():
    assert os.environ["OD05W_CORPUS_CLASS"] == "NON_MARKET_CANARY"
    assert (
        json.loads((Path.cwd() / "od05w_inputs/original-stat.json").read_text())["evidence_class"]
        == "LOCAL_META"
    )


def test_w19_inventory_closed_world():
    h = harness()
    assert h.classify_tests(["known"], {"known": "A"}) == {"known": "A"}
    with pytest.raises(ValueError):
        h.classify_tests(["unknown"], {"known": "A"})


def test_w20_blocked_input_not_passed():
    assert harness().blocked_inputs({"b": "B", "a": "A", "c": "C"}) == {
        "b": "BLOCKED_INPUT",
        "c": "BLOCKED_REAL_DATA",
    }


def test_w21_diagnostic_failures_preserved():
    result = harness().gate_summary({"passed": 1, "failed": 4}, engineering_exit=0)
    assert result["diagnostic"] == "FAIL" and result["engineering"] == "PASS"


def test_w22_integrity_refuses():
    with pytest.raises(presence().InventoryError):
        presence().request_payload_integrity("seed")


def test_w23_fresh_copy_no_overwrite(tmp_path):
    h = harness()
    source = tmp_path / "source"
    source.mkdir()
    (source / "a.py").write_text("# NON_MARKET_CANARY\n")
    dest = tmp_path / "dest"
    with pytest.raises(ValueError, match="GUARD"):
        h.copy_exact(source, dest, ["a.py"], {"a.py": "CODE"}, guard=None)
    dest.mkdir()
    with pytest.raises(ValueError):
        h.copy_exact(source, dest, ["a.py"], {"a.py": "CODE"}, guard=h.active_guard())


def test_w24_test_fixture_preserved():
    pins = json.loads((Path.cwd() / "od05w_inputs/preservation.json").read_text())
    assert pins
    for name, sha in pins.items():
        assert hashlib.sha256((Path.cwd() / name).read_bytes()).hexdigest() == sha
