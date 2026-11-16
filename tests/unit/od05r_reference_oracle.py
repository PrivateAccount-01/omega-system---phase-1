"""Independent literal evidence oracle: stdlib only, no verifier imports."""

import hashlib
import json

DOCUMENT = b"%PDF-1.4\nSYNTHETIC_TEST_ONLY original-byte identity exercise\n%%EOF\n"
SAMPLE = b"SYNTHETIC_TEST_ONLY,10.10,0\n"
META = {
    "schema_version": "od05r.reference/v1",
    "reference_id": "syn-doc-1",
    "issuer": "NSE",
    "document_id": "SYN-CM-1",
    "version": "v1",
    "source_key": "NSE_EQUITY_BHAVCOPY",
    "exchange": "NSE",
    "segment": "CM",
    "format_id": "legacy-illustrative",
    "canonical_url": "https://example.invalid/reference.pdf",
    "acquisition_method": "SYNTHETIC_TEST_ONLY",
    "acquired_at": "2026-11-16T00:00:00Z",
    "bytes_kind": "SYNTHETIC",
    "document_file": "document.pdf",
    "document_sha256": hashlib.sha256(DOCUMENT).hexdigest(),
    "document_length": len(DOCUMENT),
    "mime": "application/pdf",
    "permission": "OWNER_SUPPLIED_REFERENCE_USE",
    "permission_ref": "SYNTHETIC_TEST_ONLY",
    "reviewer_ref": None,
    "reviewed_at": None,
    "semantics": [],
    "sample_file": None,
    "sample_sha256": None,
    "sample_length": None,
    "sample_permission_ref": None,
    "sample_expected_rows_sha256": None,
    "announced_on": None,
    "effective_from": "2019-01-01",
    "effective_to": "2024-07-05",
    "supersedes": [],
}


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def expected_digest(meta):
    # Operational acquisition/review times remain in raw metadata SHA, not semantics.
    value = {k: v for k, v in meta.items() if k not in ("acquired_at", "reviewed_at")}
    return hashlib.sha256(b"od05r.semantic/v1\n" + encode(value)).hexdigest()


def corpus(root, meta=None):
    body = dict(META if meta is None else meta)
    root.mkdir()
    (root / "document.pdf").write_bytes(DOCUMENT)
    index = encode({"schema_version": "od05r.bundle/v1", "references": [body]})
    (root / "index.json").write_bytes(index)
    return hashlib.sha256(index).hexdigest()
