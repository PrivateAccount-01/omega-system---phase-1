"""Metadata engineering only: real pinned manifests and malformed metadata probes."""

import dataclasses
import hashlib
import importlib
import importlib.util
import json
import os
import socket
import time
import tracemalloc
from pathlib import Path

import pytest
from od05t_metadata_oracle import digest, pins, verify

BASE = Path.cwd() / "od05t_inputs"


def api():
    return importlib.import_module("omegadata.parsers.archive_candidate_inventory")


def cli():
    spec = importlib.util.spec_from_file_location(
        "od05t_cli", Path.cwd() / "scripts/audit_existing_market_archive.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def entries():
    body = json.loads((BASE / "pins.json").read_text())
    return tuple(tuple(row) for row in body["seed"]["entries"])


def copied(tmp_path, count=8):
    root = tmp_path / "manifests"
    root.mkdir()
    for name, sha, length in entries()[:count]:
        raw = (BASE / "seed" / name).read_bytes()
        assert len(raw) == length and hashlib.sha256(raw).hexdigest() == sha
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    return root, pins(root)


def scan(root, expected, **kw):
    a = api()
    return a.scan_metadata(root, approved_root=root, expected=a.ExpectedMetadata(expected), **kw)


def raw():
    return (BASE / "seed" / entries()[0][0]).read_bytes()


def test_m01_real_count_and_independent_pins():
    a = api()
    expected = entries()
    root = BASE / "seed"
    assert verify(root, expected) == digest(expected)
    result = a.scan_metadata(root, approved_root=root, expected=a.ExpectedMetadata(expected))
    assert len(result.rows) == len(expected) > 0


def test_m02_canonical_order_and_frozen_identity(tmp_path):
    a = api()
    root, expected = copied(tmp_path)
    result = scan(root, tuple(reversed(expected)))
    assert result.metadata_sha256 == digest(expected)
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.rows = ()
    assert a.ExpectedMetadata(expected).files == expected


def test_m03_real_source_date_mode_missing_information():
    a = api()
    original = json.loads(raw())
    row = a.parse_metadata(raw(), "entry.manifest.json")
    assert row.source_key == original["source_key"]
    assert row.business_date == original["as_of"]
    assert row.storage_mode == original["storage_mode"]
    assert row.classification == "SEED_IMPORT_UNVERIFIED"
    assert row.permission_evidence == "MISSING"
    assert row.reviewed_values == "MISSING"


@pytest.mark.parametrize(
    "body",
    [b"{", b"[]", b"\xff", b'{"x":1,"x":2}', b"x" * 65537],
    ids=["truncated", "array", "binary", "duplicate", "oversize"],
)
def test_m04_malformed_metadata(body):
    a = api()
    with pytest.raises(a.InventoryError):
        a.parse_metadata(body, "entry.manifest.json")


def test_m04_mixed_namespace_and_budgets(tmp_path):
    a = api()
    original = json.loads(raw())
    original["source_key"] = "NSE_FO_BHAVCOPY"
    with pytest.raises(a.InventoryError, match="SOURCE_SCOPE"):
        a.parse_metadata(json.dumps(original).encode(), "entry.manifest.json")
    root, expected = copied(tmp_path)
    with pytest.raises(a.InventoryError, match="BUDGET"):
        scan(root, expected, limits=a.ScanLimits(max_files=1))
    with pytest.raises(a.InventoryError):
        a.ScanLimits(max_files=0)


def test_m05_distinct_observations_and_revisions(tmp_path):
    api()
    root, _ = copied(tmp_path, 1)
    (root / "same-bytes.manifest.json").write_bytes(raw())
    body = json.loads(raw())
    body["reviewer_evidence_ref"] = "ADVERSARIAL_METADATA_ONLY"
    (root / "revision.manifest.json").write_text(json.dumps(body))
    result = scan(root, pins(root))
    assert len(result.rows) == 3
    assert result.duplicate_metadata_bytes == 1
    assert result.same_date_observations == 2


def test_m06_never_open_manifest_payload_path(tmp_path, monkeypatch):
    api()
    root, _ = copied(tmp_path, 1)
    body = json.loads(raw())
    body["artifact_path"] = str(tmp_path / "DO_NOT_OPEN.zip")
    manifest = next(root.rglob("*.manifest.json"))
    manifest.write_text(json.dumps(body))
    observed = []
    original = os.open

    def check(path, *args, **kw):
        observed.append(str(path))
        assert str(path).endswith(".manifest.json")
        return original(path, *args, **kw)

    monkeypatch.setattr(os, "open", check)
    result = scan(root, pins(root))
    assert observed
    assert result.rows[0].artifact_relative_claim is None
    assert result.payload_bytes_read == 0


@pytest.mark.parametrize("path", ["../escape", "//server/share", "C:\\private", "gnupg", ".venv"])
def test_m07_unsafe_paths(path, tmp_path):
    a = api()
    with pytest.raises(a.InventoryError):
        a.validate_root(Path(path), tmp_path)


@pytest.mark.parametrize("kind", ["file", "directory", "hardlink"])
def test_m07_real_links(tmp_path, kind):
    a = api()
    root, expected = copied(tmp_path, 1)
    target = next(root.rglob("*.manifest.json"))
    link = root / ("escape.manifest.json" if kind != "directory" else "escape")
    try:
        if kind == "hardlink":
            os.link(target, link)
        else:
            link.symlink_to(
                target.parent if kind == "directory" else target,
                target_is_directory=kind == "directory",
            )
    except OSError as error:
        pytest.skip(f"Real link unavailable: {error.__class__.__name__}; paired runtime required")
    with pytest.raises(a.InventoryError, match="PATH_UNSAFE"):
        scan(root, expected)


def test_m07_windows_junction(tmp_path):
    a = api()
    if os.name != "nt":
        pytest.skip("Windows junction; Linux directory-link counterpart required")
    import _winapi

    root, expected = copied(tmp_path, 1)
    _winapi.CreateJunction(str(tmp_path), str(root / "escape"))
    with pytest.raises(a.InventoryError, match="PATH_UNSAFE"):
        scan(root, expected)


def test_m08_redaction():
    a = api()
    body = json.loads(raw())
    body["used_url"] = "https://user:password@example.invalid/x?token=PRIVATE_TOKEN"
    body["artifact_path"] = "C:/PRIVATE_PATH/secret.zip"
    body["source_repo_url"] = "https://PRIVATE_ORIGIN.invalid"
    row = a.parse_metadata(json.dumps(body).encode(), "entry.manifest.json")
    output = json.dumps(dataclasses.asdict(row))
    for token in ("password", "PRIVATE_TOKEN", "PRIVATE_PATH", "PRIVATE_ORIGIN"):
        assert token not in output


@pytest.mark.parametrize("claim", ["PENDING_REVIEW", "REVOKED", "APPROVED", "UNKNOWN"])
def test_m09_no_self_authorizing_rights(claim):
    a = api()
    body = json.loads(raw())
    body["permission"] = claim
    body["permission_evidence_ref"] = "DECLARED_NOT_TRUSTED"
    row = a.parse_metadata(json.dumps(body).encode(), "entry.manifest.json")
    assert row.rights_state == "RIGHTS_PENDING"
    assert row.permission_evidence == "PRESENT_UNVERIFIED"
    assert not row.payload_use_authorized


def test_m10_payload_checksum_is_claim_only():
    a = api()
    row = a.parse_metadata(raw(), "entry.manifest.json")
    assert row.payload_checksum_claim == json.loads(raw())["checksum"]
    assert row.payload_hash_verified is False
    assert row.publisher_origin_verified is False


def test_m11_network_and_original_bytes_unchanged(tmp_path, monkeypatch):
    api()
    root, expected = copied(tmp_path)

    def denied(*args, **kw):
        raise AssertionError("Unexpected network")

    monkeypatch.setattr(socket, "getaddrinfo", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    scan(root, expected)
    assert verify(root, expected) == digest(expected)


@pytest.mark.parametrize("failure", ["empty", "missing", "tamper", "count", "missing_pins"])
def test_m12_nonvacuous_expected_corpus(tmp_path, failure):
    a = api()
    root, expected = copied(tmp_path, 1)
    if failure == "empty":
        next(root.rglob("*.manifest.json")).unlink()
    elif failure == "missing":
        root = root / "missing"
    elif failure == "tamper":
        with next(root.rglob("*.manifest.json")).open("ab") as stream:
            stream.write(b" ")
    elif failure == "count":
        expected = expected + (("absent.manifest.json", expected[0][1], expected[0][2]),)
    else:
        expected = ()
    with pytest.raises(a.InventoryError):
        scan(root, expected)


def test_m13_duplicate_and_mutable_pins_refused():
    a = api()
    entry = entries()[0]
    for values in ((entry, entry), [entry], (("../escape.manifest.json", entry[1], entry[2]),)):
        with pytest.raises(a.InventoryError):
            a.ExpectedMetadata(values)


def test_m14_actual_boundary_matrix_not_session_proof():
    a = api()
    expected = entries()
    result = a.scan_metadata(
        BASE / "seed", approved_root=BASE / "seed", expected=a.ExpectedMetadata(expected)
    )
    output = a.ledger(result)
    for day in (
        "2019-12-31",
        "2020-01-01",
        "2020-01-02",
        "2024-06-21",
        "2024-06-24",
        "2024-06-25",
        "2024-07-04",
        "2024-07-05",
        "2024-07-08",
        "2024-07-09",
    ):
        assert output["boundary_dates"][day]["manifest_count"] > 0
        assert output["boundary_dates"][day]["session_verified"] is False


def test_m15_scorecard_and_cli_modes(tmp_path, capsys):
    api()
    tool = cli()
    root, expected = copied(tmp_path)
    pin_file = tmp_path / "pins.json"
    pin_file.write_text(json.dumps({"schema_version": "od05t.pins/v1", "files": expected}))
    argv = [
        "--manifest-root",
        str(root),
        "--expected-pins",
        str(pin_file),
        "--metadata-only",
        "--dry-run",
    ]
    assert tool.main(argv, allowed_roots=(root,)) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["real_data_scorecard"]["status"] == "BLOCKED_REAL_DATA"
    assert output["real_data_scorecard"]["coverage"] is None
    assert output["market_rows_independently_verified"] == 0
    assert tool.main(argv + ["--require-real-data"], allowed_roots=(root,)) == 3
    capsys.readouterr()
    destination = tmp_path / "report"
    assert tool.main(argv[:-1] + ["--output-dir", str(destination)], allowed_roots=(root,)) == 0
    assert (destination / "inventory.json").is_file()
    capsys.readouterr()
    assert tool.main(argv[:-1] + ["--output-dir", str(destination)], allowed_roots=(root,)) == 2


@pytest.mark.parametrize("size", [1, 8, 32])
def test_m16_real_metadata_resource_measurement(tmp_path, size):
    api()
    root, expected = copied(tmp_path, size)
    tracemalloc.start()
    start = time.perf_counter()
    result = scan(root, expected)
    elapsed = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(json.dumps({"real_metadata_files": size, "seconds": elapsed, "peak_python_bytes": peak}))
    assert len(result.rows) == size
    assert elapsed < 30 and peak < 64_000_000


def test_m17_cli_help_invalid_and_protected(tmp_path, capsys):
    api()
    tool = cli()
    with pytest.raises(SystemExit) as help_result:
        tool.main(["--help"])
    assert help_result.value.code == 0
    capsys.readouterr()
    with pytest.raises(SystemExit) as invalid_result:
        tool.main(["--unknown"])
    assert invalid_result.value.code != 0
    capsys.readouterr()
    root, expected = copied(tmp_path)
    pin_file = tmp_path / "pins.json"
    pin_file.write_text(json.dumps({"schema_version": "od05t.pins/v1", "files": expected}))
    argv = ["--manifest-root", str(root), "--expected-pins", str(pin_file), "--metadata-only"]
    assert tool.main(argv + ["--output-dir", str(root / "report")], allowed_roots=(root,)) == 2
    assert (
        tool.main(argv + ["--dry-run", "--source-key", "NSE_FO_BHAVCOPY"], allowed_roots=(root,))
        == 2
    )
    assert tool.main(argv + ["--dry-run"], allowed_roots=(tmp_path / "not-approved",)) == 2
    assert not (root / "report").exists()


def test_m18_production_interfaces_unchanged():
    a = api()
    from omegadata.parsers.reference_evidence import ReferenceResult
    from omegadata.track_a.source_registry import SOURCE_REGISTRY

    assert ReferenceResult.__dataclass_fields__["official_eligible"].default is False
    assert SOURCE_REGISTRY["NSE_EQUITY_BHAVCOPY"].eras[-1].start_date.isoformat() == "2020-01-01"
    assert a.SOURCE_KEY == "NSE_EQUITY_BHAVCOPY"


@pytest.mark.parametrize("value", [[], {}, 12])
def test_m04_later_wrong_mode_type_is_typed_refusal(value):
    a = api()
    body = json.loads(raw())
    body["storage_mode"] = value
    with pytest.raises(a.InventoryError, match="MALFORMED_METADATA"):
        a.parse_metadata(json.dumps(body).encode(), "entry.manifest.json")


@pytest.mark.parametrize("name", ["CON.manifest.json", "aux.manifest.json", "a/COM1.manifest.json"])
def test_m07_later_portable_device_names(name):
    a = api()
    with pytest.raises(a.InventoryError, match="PATH_UNSAFE"):
        a.ExpectedMetadata(((name, entries()[0][1], entries()[0][2]),))


@pytest.mark.parametrize("name", [".env", "private.key"])
def test_m06_later_pin_filename_refused_before_open(tmp_path, monkeypatch, name):
    a = api()
    target = tmp_path / name
    target.write_bytes(b"NON_MARKET_METADATA_CANARY")
    reads = []

    def forbidden(*args, **kw):
        reads.append(args)
        raise AssertionError("Unexpected protected-file open")

    monkeypatch.setattr(a, "read_file", forbidden)
    with pytest.raises(a.InventoryError, match="EXPECTED_METADATA_INVALID"):
        a.read_expected(target)
    assert reads == []
