"""Offline evidence identity, never a source-approval authority or downloader."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Annotated, Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

Label = Annotated[
    str, Field(strict=True, min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:/-]+$")
]
Hex = Annotated[str, Field(strict=True, pattern=r"^[0-9a-f]{64}$")]
Size = Annotated[int, Field(strict=True, gt=0, le=1_000_000)]


class ReferenceError(ValueError):
    """Code-only refusal: never echo untrusted metadata, paths or credentials."""

    def __init__(self, code: str) -> None:
        self.reason_code = code
        super().__init__(code)


def filename(value: str) -> str:
    if (
        not re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9_.-]{0,95}", value, re.ASCII)
        or ".." in value
        or value.endswith(".")
        or value.split(".")[0].casefold()
        in {
            "con",
            "prn",
            "aux",
            "nul",
            *(f"com{n}" for n in range(1, 10)),
            *(f"lpt{n}" for n in range(1, 10)),
        }
    ):
        raise ReferenceError("PATH_UNSAFE")
    return value


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class Meaning(Frozen):
    field: Label
    section: Label
    meaning: Label


class Envelope(Frozen):
    schema_version: Literal["od05r.reference/v1"]
    reference_id: Label
    issuer: Literal["NSE"]
    document_id: Label
    version: Label
    source_key: Literal["NSE_EQUITY_BHAVCOPY"]
    exchange: Literal["NSE"]
    segment: Literal["CM"]
    format_id: Label
    canonical_url: Annotated[str, Field(max_length=2048)]
    acquisition_method: Literal[
        "LOCAL_SUPPLIED", "INDEX_ONLY", "SYNTHETIC_TEST_ONLY", "MIRROR", "CACHE", "SEED"
    ]
    acquired_at: str | None
    bytes_kind: Literal["ORIGINAL_UNVERIFIED", "SYNTHETIC", "PARAPHRASE", "INDEX_EXCERPT"]
    document_file: Label | None
    document_sha256: Hex | None
    document_length: Size | None
    mime: Literal["application/pdf", "text/plain", "text/csv", "application/json"]
    permission: Literal["PENDING", "DENIED", "OWNER_SUPPLIED_REFERENCE_USE"]
    permission_ref: Label | None
    reviewer_ref: Label | None
    reviewed_at: str | None
    semantics: Annotated[tuple[Meaning, ...], Field(max_length=64)]
    sample_file: Label | None
    sample_sha256: Hex | None
    sample_length: Size | None
    sample_permission_ref: Label | None
    sample_expected_rows_sha256: Hex | None
    announced_on: str | None
    effective_from: str
    effective_to: str | None
    supersedes: Annotated[tuple[Label, ...], Field(max_length=16)]

    @field_validator("document_file", "sample_file")
    @classmethod
    def name(cls, value: str | None) -> str | None:
        return filename(value) if value is not None else None

    @field_validator("canonical_url")
    @classmethod
    def url(cls, value: str) -> str:
        parts = urlsplit(value)
        if (
            parts.scheme != "https"
            or not parts.hostname
            or parts.username is not None
            or parts.password is not None
            or parts.query
            or parts.fragment
            or any(ord(c) < 33 or ord(c) > 126 for c in value)
            or "%" in value
            or "\\" in value
        ):
            raise ReferenceError("URL_UNSAFE")
        if parts.port not in (None, 443):
            raise ReferenceError("URL_UNSAFE")
        return value

    @field_validator("acquired_at", "reviewed_at")
    @classmethod
    def utc(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if len(value) > 40 or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)", value, re.ASCII
        ):
            raise ReferenceError("UTC_REQUIRED")
        if datetime.fromisoformat(value.replace("Z", "+00:00")).utcoffset() != timedelta(0):
            raise ReferenceError("UTC_REQUIRED")
        return value

    @field_validator("announced_on", "effective_from", "effective_to")
    @classmethod
    def iso_date(cls, value: str | None) -> str | None:
        if value is not None:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value, re.ASCII):
                raise ReferenceError("DATE_INVALID")
            date.fromisoformat(value)
        return value

    @model_validator(mode="after")
    def identities(self) -> Envelope:
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ReferenceError("DATE_INVALID")
        for values in (
            (self.document_file, self.document_sha256, self.document_length),
            (self.sample_file, self.sample_sha256, self.sample_length),
        ):
            if any(v is None for v in values) and any(v is not None for v in values):
                raise ReferenceError("IDENTITY_INCOMPLETE")
        if self.document_file is not None and self.document_file == self.sample_file:
            raise ReferenceError("IDENTITY_AMBIGUOUS")
        return self


def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ReferenceError("JSON_DUPLICATE")
        result[key] = value
    return result


def decode(raw: bytes) -> Any:
    if type(raw) is not bytes or len(raw) > 65_536:
        raise ReferenceError("BUDGET")
    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=unique,
            parse_constant=lambda _: (_ for _ in ()).throw(ReferenceError("JSON_INVALID")),
        )
    except ReferenceError:
        raise
    except (ValueError, UnicodeError, RecursionError):
        raise ReferenceError("JSON_INVALID") from None


@dataclass(frozen=True)
class ReferenceResult:
    evidence: Envelope
    state: str
    semantic_sha256: str
    metadata_sha256: str
    byte_identity_verified: bool
    original_identity_verified: bool
    blockers: tuple[str, ...]
    official_eligible: Literal[False] = False


def verify_reference(raw: bytes, blobs: Mapping[str, bytes]) -> ReferenceResult:
    body = decode(raw)
    try:
        # Duplicate keys are checked before Pydantic's strict JSON validation.
        envelope = Envelope.model_validate_json(json.dumps(body, ensure_ascii=True))
    except ReferenceError:
        raise
    except (ValidationError, ValueError, TypeError, RecursionError):
        raise ReferenceError("REFERENCE_INVALID") from None
    expected_names = {name for name in (envelope.document_file, envelope.sample_file) if name}
    if set(blobs) != expected_names:
        raise ReferenceError("CORPUS_MISMATCH")
    for name, digest, length in (
        (envelope.document_file, envelope.document_sha256, envelope.document_length),
        (envelope.sample_file, envelope.sample_sha256, envelope.sample_length),
    ):
        if name is None:
            continue
        data = blobs[name]
        if type(data) is not bytes or len(data) > 1_000_000:
            raise ReferenceError("BUDGET")
        if len(data) != length:
            raise ReferenceError("LENGTH_MISMATCH")
        if hashlib.sha256(data).hexdigest() != digest:
            raise ReferenceError("RAW_HASH_MISMATCH")
    if (
        envelope.document_file
        and envelope.mime == "application/pdf"
        and (
            not envelope.document_file.endswith(".pdf")
            or not blobs[envelope.document_file].startswith(b"%PDF-")
        )
    ):
        raise ReferenceError("MIME_MISMATCH")
    blockers = ["TRUSTED_REVIEW_REQUIRED", "ROW_REFERENCE_PENDING"]
    original = envelope.document_file is not None and envelope.bytes_kind == "ORIGINAL_UNVERIFIED"
    if not original:
        blockers.append("ORIGINAL_BYTES_REQUIRED")
    state = "DOCUMENT_HASH_VERIFIED" if original else "DOCUMENT_BYTES_UNVERIFIED"
    if envelope.document_file is None:
        state = "DOCUMENT_DISCOVERED"
    if envelope.semantics or envelope.sample_file:
        state = "SCHEMA_REFERENCE_PENDING"
    if envelope.permission != "OWNER_SUPPLIED_REFERENCE_USE" or not envelope.permission_ref:
        state = "BLOCKED_RIGHTS"
        blockers.append("BLOCKED_RIGHTS")
    if envelope.sample_file and not envelope.sample_permission_ref:
        state = "BLOCKED_RIGHTS"
        blockers.append("SAMPLE_RIGHTS_REQUIRED")
    semantic = envelope.model_dump(mode="json", exclude={"acquired_at", "reviewed_at"})
    canonical = json.dumps(
        semantic, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()
    return ReferenceResult(
        envelope,
        state,
        hashlib.sha256(b"od05r.semantic/v1\n" + canonical).hexdigest(),
        hashlib.sha256(raw).hexdigest(),
        envelope.document_file is not None,
        original,
        tuple(blockers),
    )


@dataclass(frozen=True)
class ExpectedCorpus:
    index_sha256: str
    expected_references: int
    files: tuple[tuple[str, str, int], ...]

    def __post_init__(self) -> None:
        if (
            type(self.index_sha256) is not str
            or not re.fullmatch("[0-9a-f]{64}", self.index_sha256)
            or type(self.expected_references) is not int
            or not 1 <= self.expected_references <= 16
            or type(self.files) is not tuple
            or not 1 <= len(self.files) <= 32
        ):
            raise ReferenceError("EXPECTED_CORPUS_INVALID")
        names = []
        for item in self.files:
            if type(item) is not tuple or len(item) != 3:
                raise ReferenceError("EXPECTED_CORPUS_INVALID")
            name, digest, length = item
            if type(name) is not str or type(digest) is not str:
                raise ReferenceError("EXPECTED_CORPUS_INVALID")
            names.append(filename(name))
            if (
                not re.fullmatch("[0-9a-f]{64}", digest)
                or type(length) is not int
                or not 0 < length <= 1_000_000
            ):
                raise ReferenceError("EXPECTED_CORPUS_INVALID")
        if len({n.casefold() for n in names}) != len(names) or "index.json" in names:
            raise ReferenceError("EXPECTED_CORPUS_INVALID")


@dataclass(frozen=True)
class BundleResult:
    references: tuple[ReferenceResult, ...]
    index_sha256: str


def no_links(path: Path) -> os.stat_result:
    try:
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ReferenceError("PATH_UNSAFE")
        return info
    except OSError:
        raise ReferenceError("CORPUS_MISSING") from None


def read_file(path: Path, cap: int) -> bytes:
    initial = no_links(path)
    if not stat.S_ISREG(initial.st_mode) or initial.st_nlink != 1:
        raise ReferenceError("PATH_UNSAFE")
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(descriptor, "rb") as stream:
            opened = os.fstat(stream.fileno())
            if (opened.st_ino, opened.st_dev) != (initial.st_ino, initial.st_dev):
                raise ReferenceError("PATH_UNSAFE")
            data = stream.read(cap + 1)
        if len(data) > cap:
            raise ReferenceError("BUDGET")
        if (no_links(path).st_ino, no_links(path).st_dev) != (initial.st_ino, initial.st_dev):
            raise ReferenceError("PATH_UNSAFE")
        return data
    except OSError:
        raise ReferenceError("CORPUS_MISSING") from None


def read_bundle(root: Path, expected: ExpectedCorpus) -> BundleResult:
    if (
        not root.is_absolute()
        or str(root).startswith(("\\\\", "//"))
        or ".." in root.parts
        or "gnupg" in {p.casefold() for p in root.parts}
    ):
        raise ReferenceError("PATH_UNSAFE")
    for parent in (*reversed(root.parents), root):
        no_links(parent)
    if not stat.S_ISDIR(no_links(root).st_mode):
        raise ReferenceError("CORPUS_MISSING")
    names: set[str] = set()
    try:
        with os.scandir(root) as entries:
            for entry in entries:
                filename(entry.name)
                no_links(Path(entry.path))
                names.add(entry.name)
                if len(names) > 33:
                    raise ReferenceError("BUDGET")
    except OSError:
        raise ReferenceError("CORPUS_MISSING") from None
    if names != {"index.json", *(name for name, _, _ in expected.files)}:
        raise ReferenceError("CORPUS_MISMATCH")
    raw = read_file(root / "index.json", 65_536)
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected.index_sha256:
        raise ReferenceError("INDEX_HASH_MISMATCH")
    body = decode(raw)
    if (
        not isinstance(body, dict)
        or set(body) != {"schema_version", "references"}
        or body["schema_version"] != "od05r.bundle/v1"
        or not isinstance(body["references"], list)
        or len(body["references"]) != expected.expected_references
    ):
        raise ReferenceError("CORPUS_MISMATCH")
    blobs = {}
    for name, pinned, length in expected.files:
        blob = read_file(root / name, 1_000_000)
        if len(blob) != length or hashlib.sha256(blob).hexdigest() != pinned:
            raise ReferenceError("RAW_HASH_MISMATCH")
        blobs[name] = blob
    results = []
    used_files: set[str] = set()
    for item in body["references"]:
        if not isinstance(item, dict):
            raise ReferenceError("REFERENCE_INVALID")
        values = (item.get("document_file"), item.get("sample_file"))
        if any(value is not None and not isinstance(value, str) for value in values):
            raise ReferenceError("REFERENCE_INVALID")
        files = {filename(value) for value in values if isinstance(value, str)}
        if not files.issubset(blobs):
            raise ReferenceError("CORPUS_MISMATCH")
        results.append(
            verify_reference(json.dumps(item).encode(), {name: blobs[name] for name in files})
        )
        used_files.update(files)
    if used_files != set(blobs):
        raise ReferenceError("CORPUS_MISMATCH")
    if len({r.evidence.reference_id for r in results}) != len(results):
        raise ReferenceError("IDENTITY_AMBIGUOUS")
    return BundleResult(tuple(results), digest)
