"""P01-P18: real manifest/stat evidence and non-market filesystem canaries only."""

import builtins
import hashlib
import importlib
import importlib.util
import io
import json
import os
from pathlib import Path

import pytest
from od05v_presence_oracle import observe

BASE = Path.cwd() / "od05v_inputs"
# OD05W contract: these tests consume an explicitly labelled native disposable
# metadata/sparse-file corpus. Original-host inventory is a separate fresh run.
# Reuse one frozen observation for unmodified inputs; mutation tests never cache.
_OBSERVATIONS = {}


def api():
    return importlib.import_module("omegadata.parsers.local_archive_presence")


def original():
    return Path(os.environ["OD05V_ORIGINAL"])


def groups():
    return json.loads((BASE / "groups.json").read_text())


def scan(repo, label, expected=None, **kw):
    a = api()
    from omegadata.parsers.archive_candidate_inventory import ExpectedMetadata

    pins = expected if expected is not None else groups()[label]["entries"]
    if expected is None and not kw and os.environ.get("OD05W_CORPUS_CLASS") == "NON_MARKET_CANARY":
        key = (str(repo), label)
        if key not in _OBSERVATIONS:
            _OBSERVATIONS[key] = a.PresenceObservation(
                repo, label, ExpectedMetadata(tuple(tuple(r) for r in pins)), version=1
            )
        return _OBSERVATIONS[key].get()
    return a.scan_presence(
        repo, label, expected=ExpectedMetadata(tuple(tuple(r) for r in pins)), **kw
    )


def fixture(tmp_path, label="seed"):
    a = api()
    group = groups()[label]
    name, sha, length = group["entries"][0]
    raw = (original() / group["repository_root"] / name).read_bytes()
    assert len(raw) == length and hashlib.sha256(raw).hexdigest() == sha
    body = json.loads(raw)
    repo = tmp_path / "repo"
    path = repo / a.ROOTS[label] / name
    path.parent.mkdir(parents=True)
    path.write_bytes(raw)
    payload = repo / body["artifact_path"].replace("\\", "/")
    payload.touch()
    with payload.open("r+b") as f:
        f.truncate(body["bytes_downloaded"])
    return repo, path, payload, [(name, sha, length)]


def repin(path, repo, label="seed"):
    raw = path.read_bytes()
    return [
        (
            path.relative_to(repo / api().ROOTS[label]).as_posix(),
            hashlib.sha256(raw).hexdigest(),
            len(raw),
        )
    ]


@pytest.mark.parametrize(
    "label,day,size",
    [("seed", "2011-06-22", 53301), ("seed", "2020-01-02", 69955), ("cache", "2024-07-23", 165041)],
    ids=["P01", "P02", "P03"],
)
def test_p01_p03_real_candidates(label, day, size):
    report = scan(original(), label)
    row = next(r for r in report["rows"] if r["date"] == day)
    # First execution discovered an existing two-link 2011 archive. Preserve
    # refusal: existence is not eligibility for reading. This is a recorded
    # post-code harness correction, not retroactive negative-first evidence.
    actual = (original() / row["payload_relative"]).lstat()
    assert row["state"] == ("HARDLINK_REFUSED" if actual.st_nlink != 1 else "PRESENT_SIZE_MATCHED")
    assert row["filesystem_bytes"] == row["claimed_bytes"] == size
    assert row["payload_hash_verified"] is False


def test_p04_full_independent_count_oracle():
    api()
    frozen = json.loads((BASE / "presence.json").read_text())
    assert observe(original(), groups()) == frozen
    for label in ("seed", "cache"):
        report = scan(original(), label)
        assert report["manifest_count"] == len(frozen[label]) > 0
        assert report["counts"]["present"] == sum(r["present"] for r in frozen[label])
        assert report["counts"]["size_matches_manifest"] == sum(
            r["size_match"] for r in frozen[label]
        )


def test_p05_missing_payload(tmp_path):
    repo, path, payload, pins = fixture(tmp_path)
    payload.unlink()
    report = scan(repo, "seed", pins)
    assert report["counts"]["missing_payload"] == 1
    assert report["rows"][0]["state"] == "MISSING_PAYLOAD"


def test_p06_wrong_claimed_size(tmp_path):
    repo, path, payload, pins = fixture(tmp_path)
    body = json.loads(path.read_text())
    body["bytes_downloaded"] += 1
    path.write_text(json.dumps(body))
    report = scan(repo, "seed", repin(path, repo))
    assert report["rows"][0]["state"] == "SIZE_MISMATCH"


@pytest.mark.parametrize("kind", ["directory", "extension"])
def test_p07_wrong_type_or_extension(tmp_path, kind):
    repo, path, payload, pins = fixture(tmp_path)
    if kind == "directory":
        payload.unlink()
        payload.mkdir()
    else:
        body = json.loads(path.read_text())
        body["artifact_path"] = body["artifact_path"].replace(".zip", ".csv")
        path.write_text(json.dumps(body))
        pins = repin(path, repo)
    assert scan(repo, "seed", pins)["rows"][0]["state"] in {"WRONG_TYPE", "PATH_UNSAFE"}


@pytest.mark.parametrize(
    "claim",
    [
        "../escape.zip",
        "/escape.zip",
        "C:/secret.zip",
        "//host/share/x.zip",
        "data/raw/nse_equity_bhavcopy/x.zip:secret",
        "data/raw/nse_equity_bhavcopy/../x.zip",
        "DATA/seed_raw/omega_phase2_repo/nse_equity_bhavcopy/x.zip",
        "data/seed_raw/omega_phase2_repo/nse_equity_bhavcopy/con.zip",
    ],
)
def test_p08_unsafe_claim(tmp_path, claim):
    repo, path, payload, pins = fixture(tmp_path)
    body = json.loads(path.read_text())
    body["artifact_path"] = claim
    path.write_text(json.dumps(body))
    assert scan(repo, "seed", repin(path, repo))["rows"][0]["state"] == "PATH_UNSAFE"


@pytest.mark.parametrize("kind", ["symlink", "hardlink", "junction"])
def test_p09_link_traps(tmp_path, kind):
    repo, path, payload, pins = fixture(tmp_path)
    outside = tmp_path / "canary"
    outside.write_bytes(b"NON_MARKET_FILESYSTEM_CANARY")
    if kind == "junction":
        if os.name != "nt":
            pytest.skip("Windows junction counterpart exercised on Windows")
        import _winapi

        # Refuse a linked ancestor of a payload without opening the target.
        payload.unlink()
        target = tmp_path / "target"
        target.mkdir()
        link = payload.parent / "linked"
        _winapi.CreateJunction(str(target), str(link))
        body = json.loads(path.read_text())
        body["artifact_path"] = (
            str(Path(body["artifact_path"]).parent).replace("\\", "/") + "/linked/test.zip"
        )
        path.write_text(json.dumps(body))
        pins = repin(path, repo)
    else:
        payload.unlink()
        try:
            if kind == "symlink":
                payload.symlink_to(outside)
            else:
                os.link(outside, payload)
        except OSError as e:
            pytest.skip("OS link privilege unavailable: " + str(e.errno))
    report = scan(repo, "seed", pins)
    assert (
        report["counts"]["symlink_or_reparse_refused"] + report["counts"]["hardlink_refused"] >= 1
    )


@pytest.mark.parametrize("kind", ["root", "feed", "source"])
def test_p10_scope(tmp_path, kind):
    repo, path, payload, pins = fixture(tmp_path)
    if kind == "root":
        with pytest.raises(api().InventoryError):
            scan(repo, "elsewhere", pins)
    elif kind == "source":
        with pytest.raises(api().InventoryError):
            scan(repo, "seed", pins, source_key="NSE_FO_BHAVCOPY")
    else:
        body = json.loads(path.read_text())
        body["source_key"] = "NSE_FO_BHAVCOPY"
        path.write_text(json.dumps(body))
        assert scan(repo, "seed", repin(path, repo))["rows"][0]["state"] == "SOURCE_SCOPE"


def test_p11_no_payload_open(tmp_path, monkeypatch):
    repo, path, payload, pins = fixture(tmp_path)
    reads = []

    def wrap(old):
        def check(name, *args, **kw):
            if not isinstance(name, int):
                assert not str(name).lower().endswith((".zip", ".csv", ".gz"))
                reads.append(str(name))
            return old(name, *args, **kw)

        return check

    for obj, name in ((builtins, "open"), (io, "open"), (os, "open")):
        monkeypatch.setattr(obj, name, wrap(getattr(obj, name)))
    assert scan(repo, "seed", pins)["payload_bytes_read"] == 0
    assert reads and all(p.endswith(".manifest.json") for p in reads)


@pytest.mark.parametrize(
    "state", ["PENDING_REVIEW", "DENIED", "REVOKED", "EXPIRED", "missing", "unknown"]
)
def test_p12_payload_integrity_refusal(tmp_path, monkeypatch, state):
    a = api()
    from datetime import UTC, datetime

    from omegadata.track_a.source_rights import SourcePolicyRegister, load_policy_register

    repo, path, payload, pins = fixture(tmp_path)
    reg = load_policy_register()
    rows = [p.model_dump(mode="json") for p in reg.policies]
    if state == "missing":
        rows = []
    elif state != "unknown":
        for p in rows:
            p["status"] = state
            if state == "REVOKED":
                p["revocation_reason"], p["revoked_at"] = (
                    "OS_METADATA_TEST",
                    datetime.now(UTC).isoformat(),
                )
            from omegadata.track_a.source_rights import SourcePolicy

            p["revision_hash"] = SourcePolicy.model_validate(p).canonical_hash()
    register = SourcePolicyRegister.model_validate(
        {"schema_version": "source-policy/v1", "policies": rows}
    )
    monkeypatch.setattr(Path, "open", lambda *a, **k: pytest.fail("Unexpected file open"))
    with pytest.raises(a.InventoryError):
        a.request_payload_integrity(
            "unknown" if state == "unknown" else "seed", policy_provider=lambda: register
        )


def test_p13_redaction(tmp_path):
    repo, path, payload, pins = fixture(tmp_path)
    body = json.loads(path.read_text())
    body.update(
        used_url="https://user:SECRET@example.invalid/file?token=SECRET",
        approved_by="SECRET",
        permission_evidence_ref="SECRET",
        original_filename="SECRET/password=SECRET.zip",
    )
    path.write_text(json.dumps(body))
    text = json.dumps(scan(repo, "seed", repin(path, repo)))
    assert "SECRET" not in text and str(tmp_path) not in text


def test_p14_duplicate_observations_and_nonvacuity(tmp_path):
    repo, path, payload, pins = fixture(tmp_path)
    second = path.with_name("revision.manifest.json")
    second.write_bytes(path.read_bytes())
    pins += repin(second, repo)
    report = scan(repo, "seed", pins)
    assert report["same_date_observations"] == 1
    assert report["duplicate_candidate"] == 1
    from omegadata.parsers.archive_candidate_inventory import ExpectedMetadata

    with pytest.raises(api().InventoryError):
        ExpectedMetadata(())


def test_p15_2020_conflict_no_route_change():
    from datetime import date

    from omegadata.track_a.source_registry import resolve_era

    report = scan(original(), "seed")
    row = next(r for r in report["rows"] if r["date"] == "2020-01-02")
    assert row["era_state"] == "ERA_CONFLICT_2020_REFERENCE_PENDING"
    assert row["claim_format"] == "LEGACY_FILENAME_CLAIM"
    assert resolve_era("NSE_EQUITY_BHAVCOPY", date(2020, 1, 2)).name == "2019_present"


def test_p16_lineage_claims_not_authentication():
    row = next(r for r in scan(original(), "seed")["rows"] if r["date"] == "2011-06-22")
    assert row["lineage"] == "PHASE2_REPOSITORY_CLAIM"
    assert row["original_filename_claim"] == "cm22JUN2011bhav.csv.zip"
    assert row["publisher_origin"] == "PUBLISHER_ORIGIN_UNVERIFIED"


def test_p17_determinism_and_bounds(tmp_path):
    repo, path, payload, pins = fixture(tmp_path)
    assert scan(repo, "seed", pins) == scan(repo, "seed", list(reversed(pins)))
    with pytest.raises(api().InventoryError):
        api().ScanLimits(max_depth=13)
    assert payload.stat().st_size > 0


def cli():
    spec = importlib.util.spec_from_file_location(
        "presence_cli", Path.cwd() / "scripts/audit_local_archive_presence.py"
    )
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def test_p18_cli_dryrun_fresh_output_and_preservation(tmp_path, capsys):
    repo, path, payload, pins = fixture(tmp_path)
    pinfile = tmp_path / "pins.json"
    pinfile.write_text(json.dumps({"schema_version": "od05t.pins/v1", "files": pins}))
    before = payload.lstat()
    args = ["--root", "seed", "--expected-pins", str(pinfile)]
    assert cli().main(args, repo=repo) == 0
    assert json.loads(capsys.readouterr().out)["payload_bytes_read"] == 0
    dest = tmp_path / "output"
    assert cli().main(args + ["--output-dir", str(dest)], repo=repo) == 0
    assert (dest / "presence.json").is_file()
    assert cli().main(args + ["--output-dir", str(dest)], repo=repo) == 2
    assert cli().main(args + ["--output-dir", str(repo / "bad")], repo=repo) == 2
    assert cli().main(args + ["--payload-integrity"], repo=repo) == 2
    assert payload.lstat().st_mtime_ns == before.st_mtime_ns


def test_p18_pin_mismatch_and_corpus(tmp_path):
    repo, path, payload, pins = fixture(tmp_path)
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(api().InventoryError, match="PIN"):
        scan(repo, "seed", pins)


@pytest.mark.parametrize("value", [[], {}, 7, True])
def test_p13_late_nonstring_original_claim(tmp_path, value):
    repo, path, payload, pins = fixture(tmp_path)
    body = json.loads(path.read_text())
    body["original_filename"] = value
    path.write_text(json.dumps(body))
    row = scan(repo, "seed", repin(path, repo))["rows"][0]
    assert row["lineage"] == "UNVERIFIED"
    assert row["original_filename_claim"] is None


def test_p08_late_non_directory_parent_not_counted_as_payload(tmp_path):
    repo, path, payload, pins = fixture(tmp_path)
    blocker = payload.parent / "blocker"
    blocker.touch()
    body = json.loads(path.read_text())
    body["artifact_path"] = blocker.relative_to(repo).as_posix() + "/unreachable.zip"
    path.write_text(json.dumps(body))
    report = scan(repo, "seed", repin(path, repo))
    assert report["rows"][0]["state"] == "PATH_UNSAFE"
    assert report["counts"]["payload_path_exists"] == 0
