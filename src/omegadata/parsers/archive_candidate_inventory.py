"""Read-only metadata triage. No market payload, source permission or approval API."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import time
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any

from omegadata.parsers.reference_evidence import ReferenceError, no_links, read_file, unique

SOURCE_KEY = "NSE_EQUITY_BHAVCOPY"
BOUNDARIES = (
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
)


class InventoryError(ValueError):
    """Bounded reason codes only, with no user metadata or host paths."""

    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        super().__init__(reason_code)


def relative_name(value: str) -> str:
    if (
        type(value) is not str
        or len(value) > 512
        or "\\" in value
        or ":" in value
        or value.startswith("/")
        or "//" in value
        or any(
            not re.fullmatch(r"[A-Za-z0-9_=-][A-Za-z0-9_.=-]{0,127}", p)
            or ".." in p
            or p.endswith(".")
            or p.split(".")[0].casefold()
            in {
                "con",
                "prn",
                "aux",
                "nul",
                *(f"com{n}" for n in range(1, 10)),
                *(f"lpt{n}" for n in range(1, 10)),
            }
            for p in value.split("/")
        )
    ):
        raise InventoryError("PATH_UNSAFE")
    return value


def json_object(raw: bytes, cap: int) -> dict[str, Any]:
    if type(raw) is not bytes or not 0 < len(raw) <= cap:
        raise InventoryError("BUDGET_OR_EMPTY")
    try:
        body = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=unique,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
        )
        if not isinstance(body, dict):
            raise ValueError
        return body
    except (ValueError, UnicodeError, RecursionError):
        raise InventoryError("MALFORMED_METADATA") from None


@dataclass(frozen=True)
class ScanLimits:
    max_files: int = 5000
    max_entries: int = 20000
    max_depth: int = 12
    max_file_bytes: int = 65536
    max_total_bytes: int = 64_000_000
    max_seconds: int = 30

    def __post_init__(self) -> None:
        ceilings = (5000, 20000, 12, 65536, 64_000_000, 30)
        if any(
            type(v) is not int or not 0 < v <= cap
            for v, cap in zip(asdict(self).values(), ceilings, strict=True)
        ):
            raise InventoryError("BUDGET_INVALID")


@dataclass(frozen=True)
class ExpectedMetadata:
    files: tuple[tuple[str, str, int], ...]

    def __post_init__(self) -> None:
        if type(self.files) is not tuple or not 1 <= len(self.files) <= 5000:
            raise InventoryError("EXPECTED_METADATA_INVALID")
        names = []
        for item in self.files:
            if type(item) is not tuple or len(item) != 3:
                raise InventoryError("EXPECTED_METADATA_INVALID")
            name, sha, length = item
            relative_name(name)
            if (
                not name.endswith(".manifest.json")
                or type(sha) is not str
                or not re.fullmatch(r"[0-9a-f]{64}", sha)
                or type(length) is not int
                or not 0 < length <= 65536
            ):
                raise InventoryError("EXPECTED_METADATA_INVALID")
            names.append(name.casefold())
        if len(set(names)) != len(names):
            raise InventoryError("EXPECTED_METADATA_INVALID")


def read_expected(path: Path) -> ExpectedMetadata:
    if path.suffix != ".json" or path.name.startswith("."):
        raise InventoryError("EXPECTED_METADATA_INVALID")
    validate_root(path.parent, path.parent)
    try:
        body = json_object(read_file(path, 2_000_000), 2_000_000)
        if set(body) != {"schema_version", "files"} or body["schema_version"] != "od05t.pins/v1":
            raise InventoryError("EXPECTED_METADATA_INVALID")
        files = body["files"]
        if not isinstance(files, list) or any(not isinstance(row, list) for row in files):
            raise InventoryError("EXPECTED_METADATA_INVALID")
        return ExpectedMetadata(tuple(tuple(row) for row in files))
    except ReferenceError as error:
        raise InventoryError(error.reason_code) from None
    except (TypeError, KeyError):
        raise InventoryError("EXPECTED_METADATA_INVALID") from None


def validate_root(root: Path, approved_root: Path) -> Path:
    for path in (root, approved_root):
        if (
            not path.is_absolute()
            or str(path).startswith(("//", "\\\\"))
            or ".." in path.parts
            or path == Path(path.anchor)
            or any(
                p.casefold() == "gnupg" or p.casefold().startswith((".venv", ".env"))
                for p in path.parts
            )
        ):
            raise InventoryError("PATH_UNSAFE")
        try:
            for parent in (*reversed(path.parents), path):
                no_links(parent)
            if not stat.S_ISDIR(no_links(path).st_mode):
                raise InventoryError("PATH_UNSAFE")
        except ReferenceError as error:
            raise InventoryError(error.reason_code) from None
    if not root.resolve().is_relative_to(approved_root.resolve()):
        raise InventoryError("PATH_UNSAFE")
    return root


@dataclass(frozen=True)
class Candidate:
    manifest_name: str
    metadata_sha256: str
    source_key: str
    business_date: str
    storage_mode: str
    classification: str
    origin_classification: str
    payload_checksum_claim: str | None
    artifact_relative_claim: str | None
    permission_evidence: str
    reference_evidence: str
    reviewed_values: str
    rights_state: str = "RIGHTS_PENDING"
    payload_use_authorized: bool = False
    payload_hash_verified: bool = False
    publisher_origin_verified: bool = False


def parse_metadata(raw: bytes, name: str, source_key: str = SOURCE_KEY) -> Candidate:
    relative_name(name)
    if source_key != SOURCE_KEY:
        raise InventoryError("SOURCE_SCOPE")
    body = json_object(raw, 65536)
    if body.get("source_key") != source_key:
        raise InventoryError("SOURCE_SCOPE")
    day = body.get("as_of")
    try:
        if not isinstance(day, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", day):
            raise ValueError
        date.fromisoformat(day)
    except ValueError:
        raise InventoryError("DATE_METADATA_INVALID") from None
    declared_mode = body.get("storage_mode")
    if declared_mode is not None and type(declared_mode) is not str:
        raise InventoryError("MALFORMED_METADATA")
    modes = {
        "immutable_seed_cache": "SEED_IMPORT_UNVERIFIED",
        "immutable_versioned": "VERSIONED_CACHE_UNVERIFIED",
    }
    mode = declared_mode if declared_mode in modes else "MISSING_INFORMATION"
    checksum = body.get("checksum")
    checksum = (
        checksum if isinstance(checksum, str) and re.fullmatch("[0-9a-f]{64}", checksum) else None
    )
    artifact = body.get("artifact_path")
    try:
        artifact = relative_name(artifact) if isinstance(artifact, str) else None
    except InventoryError:
        artifact = None
    url = body.get("used_url")
    # Only a scheme category is emitted. Never host, userinfo, query or URL path.
    origin = "MISSING_INFORMATION"
    if isinstance(url, str):
        for scheme in ("https", "http", "seed"):
            if url.startswith(scheme + "://"):
                origin = scheme.upper() + "_CLAIM_UNVERIFIED"
                break

    def presence(*fields: str) -> str:
        return "PRESENT_UNVERIFIED" if any(body.get(field) for field in fields) else "MISSING"

    return Candidate(
        name,
        hashlib.sha256(raw).hexdigest(),
        source_key,
        day,
        mode,
        modes.get(mode, "TRANSPORT_CLAIM_UNVERIFIED"),
        origin,
        checksum,
        artifact,
        presence("permission_evidence_ref", "approval_evidence_ref"),
        presence("reference_id", "reference_evidence_ref"),
        presence("reviewer_evidence_ref", "expected_values_ref"),
    )


@dataclass(frozen=True)
class Inventory:
    rows: tuple[Candidate, ...]
    errors: tuple[tuple[str, str], ...]
    metadata_sha256: str
    metadata_bytes_read: int
    duplicate_metadata_bytes: int
    same_date_observations: int
    payload_bytes_read: int = 0


def scan_metadata(
    root: Path,
    *,
    approved_root: Path,
    expected: ExpectedMetadata,
    source_key: str = SOURCE_KEY,
    business_date_start: str | None = None,
    business_date_end: str | None = None,
    limits: ScanLimits | None = None,
) -> Inventory:
    if source_key != SOURCE_KEY:
        raise InventoryError("SOURCE_SCOPE")
    limits = limits or ScanLimits()
    for value in (business_date_start, business_date_end):
        if value is not None:
            try:
                if date.fromisoformat(value).isoformat() != value:
                    raise ValueError
            except ValueError:
                raise InventoryError("DATE_METADATA_INVALID") from None
    if business_date_start and business_date_end and business_date_end < business_date_start:
        raise InventoryError("DATE_METADATA_INVALID")
    validate_root(root, approved_root)
    start = time.monotonic()
    found: list[str] = []
    count = 0
    stack = [(root, 0)]
    device = root.stat().st_dev
    try:
        while stack:
            directory, depth = stack.pop()
            if depth > limits.max_depth:
                raise InventoryError("BUDGET")
            with os.scandir(directory) as iterator:
                for entry in iterator:
                    count += 1
                    if count > limits.max_entries or time.monotonic() - start > limits.max_seconds:
                        raise InventoryError("BUDGET")
                    path = Path(entry.path)
                    info = no_links(path)
                    if info.st_dev != device:
                        raise InventoryError("PATH_UNSAFE")
                    if stat.S_ISDIR(info.st_mode):
                        relative_name(path.relative_to(root).as_posix())
                        stack.append((path, depth + 1))
                    elif path.name.endswith(".manifest.json"):
                        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                            raise InventoryError("PATH_UNSAFE")
                        found.append(relative_name(path.relative_to(root).as_posix()))
                        if len(found) > limits.max_files:
                            raise InventoryError("BUDGET")
        if set(found) != {row[0] for row in expected.files}:
            raise InventoryError("EXPECTED_CORPUS_MISMATCH")
        rows = []
        errors = []
        total = 0
        for name, pinned, length in sorted(expected.files):
            if time.monotonic() - start > limits.max_seconds:
                raise InventoryError("BUDGET")
            raw = read_file(root / PurePosixPath(name), limits.max_file_bytes)
            total += len(raw)
            if total > limits.max_total_bytes:
                raise InventoryError("BUDGET")
            if len(raw) != length or hashlib.sha256(raw).hexdigest() != pinned:
                raise InventoryError("METADATA_PIN_MISMATCH")
            try:
                row = parse_metadata(raw, name, source_key)
                if (business_date_start is None or row.business_date >= business_date_start) and (
                    business_date_end is None or row.business_date <= business_date_end
                ):
                    rows.append(row)
            except InventoryError as error:
                errors.append((name, error.reason_code))
        canonical = json.dumps(
            sorted(expected.files), separators=(",", ":"), ensure_ascii=True
        ).encode()
        return Inventory(
            tuple(rows),
            tuple(errors),
            hashlib.sha256(b"od05t.metadata/v1\n" + canonical).hexdigest(),
            total,
            len(rows) - len({r.metadata_sha256 for r in rows}),
            len(rows) - len({(r.source_key, r.business_date) for r in rows}),
        )
    except ReferenceError as error:
        raise InventoryError(error.reason_code) from None
    except OSError:
        raise InventoryError("METADATA_IO_REFUSED") from None


def ledger(result: Inventory) -> dict[str, Any]:
    ordered = sorted(
        result.rows,
        key=lambda r: (
            -(r.permission_evidence != "MISSING"),
            -(r.reference_evidence != "MISSING"),
            -(r.reviewed_values != "MISSING"),
            r.business_date,
            r.manifest_name,
        ),
    )
    counts = Counter(r.business_date for r in result.rows)
    return {
        "schema_version": "od05t.inventory/v1",
        "classification": "METADATA_ONLY_INVENTORY",
        "metadata_sha256": result.metadata_sha256,
        "metadata_bytes_read": result.metadata_bytes_read,
        "manifest_count": len(result.rows),
        "malformed_count": len(result.errors),
        "errors": result.errors,
        "duplicate_metadata_bytes": result.duplicate_metadata_bytes,
        "same_date_observations": result.same_date_observations,
        "declared_modes": dict(sorted(Counter(r.storage_mode for r in result.rows).items())),
        "months": dict(sorted(Counter(r.business_date[:7] for r in result.rows).items())),
        "dates": dict(sorted(counts.items())),
        "boundary_dates": {
            d: {"manifest_count": counts[d], "session_verified": False} for d in BOUNDARIES
        },
        "candidates": [asdict(row) for row in ordered],
        "payload_bytes_read": 0,
        "market_rows_parsed": 0,
        "market_rows_independently_verified": 0,
        "official_reference_verified": 0,
        "real_data_scorecard": {
            "status": "BLOCKED_REAL_DATA",
            "authentic_market_files_verified": 0,
            "market_rows_independently_verified": 0,
            "mismatches": None,
            "missing_sessions": None,
            "coverage": None,
            "coverage_denominator": None,
            "rejected_market_records": 0,
            "synthetic_acceptance_contribution": 0,
        },
    }
