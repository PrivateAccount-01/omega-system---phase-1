"""Final OD05: non-market failures and existing fixture regression only."""
import hashlib
import importlib
import io
import json
import os
import zipfile
from datetime import date
from pathlib import Path

import pytest

from omegadata.parsers.contracts import ParseRequest
from omegadata.parsers.dispatch import parse


def request(raw):
    return ParseRequest("NSE_EQUITY_BHAVCOPY", date(2019, 12, 31),
                        hashlib.sha256(raw).hexdigest(), "SYNTHETIC_TEST_ONLY",
                        "legacy-illustrative", "syn-v1", "synthetic-v1")


@pytest.mark.parametrize("raw,code", [(b"<html>denied</html>", "PARSER_HTML_CHALLENGE"),
                                     (b"\xff", "PARSER_INVALID_ENCODING"),
                                     (b"PKbroken", "PARSER_ARCHIVE_CORRUPT"),
                                     (b"missing,header\n", "PARSER_REQUIRED_COLUMN_MISSING")])
def test_final_public_failure_codes(raw, code):
    result = parse(raw, request(raw))
    assert result.state == "QUARANTINED" and result.rows == ()
    assert result.failure_code == code


def test_final_existing_fixture_output_retains_versions_and_digest():
    # Reuse the already frozen regression fixture; generate no new observations.
    from od05_oracle import LEGACY

    result = parse(LEGACY, request(LEGACY))
    assert result.failure_code is None
    assert result.parser_version == "syn-v1" and result.format_id == "legacy-illustrative"
    assert result.raw_sha256 == hashlib.sha256(LEGACY).hexdigest()


def test_final_catalog_has_explicit_authority_and_no_inferred_dates():
    h = importlib.import_module("omegadata.parsers.schema_catalog")
    profiles = h.supported_formats()
    assert {p["format_id"] for p in profiles} == {"legacy-illustrative", "udiff-illustrative"}
    for p in profiles:
        assert p["effective_start"] is p["effective_end"] is None
        assert p["source_authentication_state"] == "UNVERIFIED"
        assert p["content_permission_state"] == "REGRESSION_ONLY_NO_SOURCE_GRANT"
        assert p["unknown_column_policy"] == "PRESERVE_NOT_INTERPRETED"
        assert p["encoding_rules"] == "UTF8_STRICT_CRLF_OR_LF"
        assert p["schema_version"] and p["required_columns"]


def reporting():
    return importlib.import_module("od05_final_report")


def bundle(tmp_path):
    root = tmp_path / "report-inputs"
    root.mkdir()
    body = json.dumps({"artifacts": {"report.md": "# NON_MARKET_CANARY\n"}}).encode()
    (root / "summary.json").write_bytes(body)
    spec = {"schema_version": "od05.final-report/v1", "files": {
        "summary.json": {"sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}}}
    raw = json.dumps(spec).encode()
    (root / "manifest.json").write_bytes(raw)
    return root, hashlib.sha256(raw).hexdigest()


def test_final_report_requires_actual_boundary_before_input(tmp_path):
    with pytest.raises(ValueError, match="BOUNDARY"):
        reporting().render(tmp_path / "not-read", "0" * 64, tmp_path / "out", capability=None)


def test_final_report_no_git_or_discovery(tmp_path, monkeypatch):
    import subprocess

    def forbidden(*args, **kwargs):
        raise AssertionError("UNSAFE_GIT_REACHED")

    monkeypatch.setattr(subprocess, "check_output", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    # A harmless fake repository is not initialized or queried by Git.
    (tmp_path / ".git").mkdir()
    root, pin = bundle(tmp_path)
    h = reporting()
    result = h.render(root, pin, tmp_path / "out", capability=h.boundary())
    assert result["files"] == ["report.md"]
    assert (tmp_path / "out/report.md").read_text() == "# NON_MARKET_CANARY\n"
    with pytest.raises(ValueError, match="FRESH"):
        h.render(root, pin, tmp_path / "out", capability=h.boundary())


@pytest.mark.parametrize("attack", ["extra", "symlink", "hardlink", "pin", "path", "command"])
def test_final_report_fail_closed(tmp_path, attack):
    root, pin = bundle(tmp_path)
    if attack == "extra":
        (root / "unknown.json").write_text("{}")
    elif attack == "symlink":
        (root / "summary.json").rename(root / "other.json")
        (root / "summary.json").symlink_to(root / "other.json")
    elif attack == "hardlink":
        os.link(root / "summary.json", tmp_path / "alias.json")
    elif attack == "pin":
        (root / "summary.json").write_text("{}")
    else:
        name = "../escape.md" if attack == "path" else "report.md"
        body = {"artifacts": {name: "NON_MARKET_CANARY"}}
        if attack == "command":
            body["command"] = ["git", "diff", "--name-only"]
        raw = json.dumps(body).encode()
        (root / "summary.json").write_bytes(raw)
        spec = {"schema_version": "od05.final-report/v1", "files": {"summary.json": {
            "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}}}
        raw = json.dumps(spec).encode()
        (root / "manifest.json").write_bytes(raw)
        pin = hashlib.sha256(raw).hexdigest()
    h = reporting()
    with pytest.raises((ValueError, OSError)):
        h.render(root, pin, tmp_path / "out", capability=h.boundary())
    assert not (tmp_path / "out").exists()


def test_final_report_native_boundary():
    import od05x_isolated_runner as h

    assert all(h.native_probe(n)["denied"] for n in ("read", "write", "execve", "tcp", "dns"))
    assert not Path("/mnt/e").exists()


def test_final_nonmarket_archive_failure_has_no_rows():
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as z:
        z.writestr("../NON_MARKET_CANARY.txt", "NON_MARKET_CANARY")
    raw = stream.getvalue()
    result = parse(raw, request(raw))
    assert result.rows == () and result.failure_code == "PARSER_ARCHIVE_UNSAFE"
