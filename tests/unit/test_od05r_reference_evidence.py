"""R01–R24 complete pre-code reference-verifier matrix. Synthetic only."""

from __future__ import annotations

import hashlib
from datetime import date

import pytest
from od05r_reference_oracle import DOCUMENT, META, SAMPLE, corpus, encode, expected_digest


@pytest.fixture()
def api():
    from omegadata.parsers import era_matrix, reference_evidence

    return reference_evidence, era_matrix


def verify(api, meta=None, blobs=None):
    return api[0].verify_reference(
        encode(META if meta is None else meta),
        {"document.pdf": DOCUMENT} if blobs is None else blobs,
    )


def pins(api, sha, **changes):
    values = {
        "index_sha256": sha,
        "expected_references": 1,
        "files": (("document.pdf", hashlib.sha256(DOCUMENT).hexdigest(), len(DOCUMENT)),),
    }
    return api[0].ExpectedCorpus(**(values | changes))


def test_r01_absent_empty(api, tmp_path):
    for root in (tmp_path / "missing", tmp_path):
        with pytest.raises(api[0].ReferenceError):
            api[0].read_bundle(root, pins(api, "0" * 64))


@pytest.mark.parametrize(
    "raw", [b"{}", b'{"reference_id":"a","reference_id":"b"}', b"[]", b"{", b'{"x":NaN}']
)
def test_r02_json(api, raw):
    with pytest.raises(api[0].ReferenceError):
        api[0].verify_reference(raw, {})


@pytest.mark.parametrize("changes", [{"document_sha256": "0" * 64}, {"document_length": 1}])
def test_r03_identity(api, changes):
    with pytest.raises(api[0].ReferenceError):
        verify(api, META | changes)


def test_r04_paraphrase(api):
    result = verify(api, META | {"bytes_kind": "PARAPHRASE"})
    assert not result.original_identity_verified and not result.official_eligible
    assert "ORIGINAL_BYTES_REQUIRED" in result.blockers


@pytest.mark.parametrize(
    "changes",
    [{"issuer": "FAKE"}, {"official": True}, {"approved": True}, {"reviewer_ref": "LLM-citation"}],
)
def test_r05_no_caller_authority(api, changes):
    if "reviewer_ref" in changes:
        assert not verify(api, META | changes).official_eligible
    else:
        with pytest.raises(api[0].ReferenceError):
            verify(api, META | changes)


@pytest.mark.parametrize("permission", ["PENDING", "DENIED"])
def test_r06_rights(api, permission):
    result = verify(api, META | {"permission": permission, "permission_ref": None})
    assert result.state == "BLOCKED_RIGHTS" and not result.official_eligible


def test_r07_document_not_row(api):
    result = verify(
        api, META | {"bytes_kind": "ORIGINAL_UNVERIFIED", "acquisition_method": "LOCAL_SUPPLIED"}
    )
    assert result.byte_identity_verified and result.original_identity_verified
    assert result.state == "DOCUMENT_HASH_VERIFIED" and not result.official_eligible


def test_r08_sample_not_schema(api):
    meta = META | {
        "document_file": None,
        "document_sha256": None,
        "document_length": None,
        "sample_file": "sample.csv",
        "sample_sha256": hashlib.sha256(SAMPLE).hexdigest(),
        "sample_length": len(SAMPLE),
        "sample_permission_ref": "SYNTHETIC_TEST_ONLY",
        "sample_expected_rows_sha256": "a" * 64,
    }
    result = verify(api, meta, {"sample.csv": SAMPLE})
    assert result.state == "SCHEMA_REFERENCE_PENDING" and not result.official_eligible


def test_r09_conflict(api):
    a = verify(api)
    b = verify(api, META | {"reference_id": "syn-doc-2", "format_id": "udiff-illustrative"})
    cell = api[1].build_matrix((a, b), (date(2020, 1, 1),))[0]
    assert cell.state == "CONFLICT" and not cell.supported


def test_r10_dates_overlap(api):
    a = verify(api)
    b = verify(api, META | {"reference_id": "syn-doc-2", "document_id": "SYN-CM-2"})
    cells = api[1].build_matrix((a, b), (date(2018, 1, 1), date(2024, 7, 5), date(2024, 7, 8)))
    assert [c.state for c in cells] == ["UNKNOWN", "OVERLAP", "UNKNOWN"]


def test_r11_versions(api):
    a = verify(api)
    b = verify(
        api, META | {"reference_id": "syn-doc-2", "version": "v2", "supersedes": ["syn-doc-1"]}
    )
    assert a.semantic_sha256 != b.semantic_sha256
    assert len(api[1].build_matrix((a, b), (date(2020, 1, 1),))[0].reference_ids) == 2


@pytest.mark.parametrize(
    "changes", [{"segment": "FO"}, {"source_key": "NSE_FO_BHAVCOPY"}, {"exchange": "BSE"}]
)
def test_r12_scope(api, changes):
    with pytest.raises(api[0].ReferenceError):
        verify(api, META | changes)


def test_r13_bse_no_inheritance(api):
    with pytest.raises(api[0].ReferenceError):
        verify(
            api, META | {"issuer": "BSE", "exchange": "BSE", "source_key": "BSE_EQUITY_BHAVCOPY"}
        )


@pytest.mark.parametrize("method", ["SYNTHETIC_TEST_ONLY", "CACHE", "SEED", "MIRROR", "INDEX_ONLY"])
def test_r14_origin(api, method):
    assert not verify(api, META | {"acquisition_method": method}).official_eligible


@pytest.mark.parametrize(
    "url",
    [
        "https://user:secret@example.invalid/doc",
        "https://example.invalid/doc?token=secret",
        "file:///secret",
        "http://example.invalid/doc",
        "https://example.invalid/doc#secret",
    ],
)
def test_r15_secret_redaction(api, url):
    with pytest.raises(api[0].ReferenceError) as caught:
        verify(api, META | {"canonical_url": url})
    assert "secret" not in str(caught.value) and "example.invalid" not in str(caught.value)


@pytest.mark.parametrize(
    "changes",
    [
        {"acquired_at": "2026-11-16T00:00:00"},
        {"acquired_at": "2026-11-16T01:00:00+01:00"},
        {"effective_from": "2020-1-1"},
        {"version": "v" * 300},
        {"version": "v\u0301"},
        {"effective_from": "2025-01-01", "effective_to": "2024-01-01"},
    ],
)
def test_r16_bounds(api, changes):
    with pytest.raises(api[0].ReferenceError):
        verify(api, META | changes)


@pytest.mark.parametrize(
    "name",
    [
        "../document.pdf",
        "/document.pdf",
        "C:/document.pdf",
        "\\\\host\\share",
        "a\\b.pdf",
        "con.pdf",
    ],
)
def test_r17_names(api, name):
    with pytest.raises(api[0].ReferenceError):
        verify(api, META | {"document_file": name})


def test_r17_real_link(api, tmp_path):
    root = tmp_path / "bundle"
    sha = corpus(root)
    outside = tmp_path / "external.pdf"
    outside.write_bytes(DOCUMENT)
    (root / "document.pdf").unlink()
    try:
        (root / "document.pdf").symlink_to(outside)
    except OSError:
        # Windows junction analogue and real Linux file-link proof are paired externally.
        pytest.skip("File symlink privilege unavailable; paired Linux node required")
    with pytest.raises(api[0].ReferenceError, match="PATH_UNSAFE"):
        api[0].read_bundle(root, pins(api, sha))


def test_r18_budgets(api, tmp_path):
    with pytest.raises(api[0].ReferenceError, match="BUDGET"):
        api[0].verify_reference(b" " * 65537, {})
    root = tmp_path / "bundle"
    sha = corpus(root)
    for n in range(34):
        (root / f"x{n}.txt").write_bytes(b"x")
    with pytest.raises(api[0].ReferenceError):
        api[0].read_bundle(root, pins(api, sha))
    with pytest.raises(api[0].ReferenceError):
        verify(api, blobs={"document.pdf": DOCUMENT + b"x" * 1_000_001})


def test_r19_pinned_corpus(api, tmp_path):
    root = tmp_path / "bundle"
    sha = corpus(root)
    result = api[0].read_bundle(root, pins(api, sha))
    assert len(result.references) == 1
    for changed in (pins(api, "0" * 64), pins(api, sha, expected_references=2)):
        with pytest.raises(api[0].ReferenceError):
            api[0].read_bundle(root, changed)
    root.rename(tmp_path / "moved")
    with pytest.raises(api[0].ReferenceError):
        api[0].read_bundle(root, pins(api, sha))


def test_r20_deterministic(api):
    first = verify(api)
    second = verify(api, META | {"acquired_at": "2026-11-16T02:00:00Z"})
    assert first.semantic_sha256 == second.semantic_sha256 == expected_digest(META)
    assert first.metadata_sha256 != second.metadata_sha256


def test_r21_pure(api, monkeypatch):
    import builtins
    import socket

    def deny(*args, **kwargs):
        raise AssertionError("PURE_VERIFIER_IO")

    monkeypatch.setattr(builtins, "open", deny)
    monkeypatch.setattr(socket, "create_connection", deny)
    assert verify(api).official_eligible is False


def test_r22_compatibility(api):
    from od05_oracle import LEGACY
    from od05_oracle import expected_digest as old_digest

    from omegadata.parsers.contracts import ParseRequest
    from omegadata.parsers.dispatch import parse

    before = parse(
        LEGACY,
        ParseRequest(
            "NSE_EQUITY_BHAVCOPY",
            date(2019, 12, 31),
            hashlib.sha256(LEGACY).hexdigest(),
            "SYNTHETIC_TEST_ONLY",
            "legacy-illustrative",
            "syn-v1",
            "synthetic-v1",
        ),
    )
    verify(api)
    assert before.semantic_sha256 == old_digest("2019-12-31", "legacy-illustrative")


def test_r23_oracle_and_tamper(api):
    assert verify(api).semantic_sha256 == expected_digest(META)
    changed = verify(api, META | {"version": "v2"})
    assert changed.semantic_sha256 != expected_digest(META)
    for body in (DOCUMENT + b"x", b"", DOCUMENT[:-1]):
        with pytest.raises(api[0].ReferenceError):
            verify(api, blobs={"document.pdf": body})


def test_r24_runtime_vector(api):
    # Full platform/quality/security evidence is required outside this unit vector.
    result = verify(api)
    assert result.semantic_sha256 == expected_digest(META)
    assert not result.official_eligible and "TRUSTED_REVIEW_REQUIRED" in result.blockers


# Review additions after the first green implementation; never pre-code claims.
def test_r17_later_root_traversal(api, tmp_path):
    parent = tmp_path / "holder"
    parent.mkdir()
    target = tmp_path / "bundle"
    sha = corpus(target)
    with pytest.raises(api[0].ReferenceError, match="PATH_UNSAFE"):
        api[0].read_bundle(parent / ".." / "bundle", pins(api, sha))


def test_r02_later_unhashable_file(api, tmp_path):
    root = tmp_path / "bundle"
    sha = corpus(root, META | {"document_file": ["document.pdf"]})
    with pytest.raises(api[0].ReferenceError):
        api[0].read_bundle(root, pins(api, sha))


def test_r19_later_orphan_pin(api, tmp_path):
    root = tmp_path / "bundle"
    sha = corpus(root)
    (root / "orphan.pdf").write_bytes(DOCUMENT)
    expected = pins(
        api,
        sha,
        files=(
            ("document.pdf", hashlib.sha256(DOCUMENT).hexdigest(), len(DOCUMENT)),
            ("orphan.pdf", hashlib.sha256(DOCUMENT).hexdigest(), len(DOCUMENT)),
        ),
    )
    with pytest.raises(api[0].ReferenceError):
        api[0].read_bundle(root, expected)


def test_r17_later_windows_junction(api, tmp_path):
    import sys

    if sys.platform != "win32":
        pytest.skip("Windows junction; Linux file-link counterpart required")
    import _winapi

    target = tmp_path / "bundle"
    sha = corpus(target)
    link = tmp_path / "junction"
    _winapi.CreateJunction(str(target), str(link))
    with pytest.raises(api[0].ReferenceError, match="PATH_UNSAFE"):
        api[0].read_bundle(link, pins(api, sha))


def test_r23_later_sample_tamper(api):
    meta = META | {
        "sample_file": "sample.csv",
        "sample_sha256": hashlib.sha256(SAMPLE).hexdigest(),
        "sample_length": len(SAMPLE),
        "sample_permission_ref": "SYNTHETIC_TEST_ONLY",
        "sample_expected_rows_sha256": "a" * 64,
    }
    with pytest.raises(api[0].ReferenceError):
        verify(
            api, meta, {"document.pdf": DOCUMENT, "sample.csv": SAMPLE.replace(b"10.10", b"10.11")}
        )


def test_r09_later_conflicting_field_semantics(api):
    first = verify(api)
    changed = verify(
        api,
        META
        | {
            "reference_id": "syn-doc-2",
            "semantics": [{"field": "TradDt", "section": "p1", "meaning": "business-date"}],
        },
    )
    assert api[1].build_matrix((first, changed), (date(2020, 1, 1),))[0].state == "CONFLICT"


def test_r19_later_expected_pins_are_frozen(api):
    with pytest.raises(api[0].ReferenceError):
        pins(
            api,
            "0" * 64,
            files=[("document.pdf", hashlib.sha256(DOCUMENT).hexdigest(), len(DOCUMENT))],
        )
