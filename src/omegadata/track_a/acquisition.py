"""Bounded offline acquisition contracts. No legal approval or live egress authority."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
import stat
import time
import zipfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from email.utils import parsedate_to_datetime
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit, urlunsplit

from omegadata.track_a.source_registry import resolve_era


class DownloadError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        stage: str = "request",
        reason_code: str = "INTERNAL_ERROR",
        terminal: bool = False,
        retry_after: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.stage = stage
        self.reason_code = reason_code
        self.terminal = terminal
        self.retry_after = retry_after
        self.context: dict[str, object] = {}


def failure(
    reason: str,
    *,
    status: int | None = None,
    terminal: bool = True,
    stage: str = "request",
    retry_after: str | None = None,
) -> DownloadError:
    return DownloadError(
        reason,
        reason_code=reason,
        status_code=status,
        terminal=terminal,
        stage=stage,
        retry_after=retry_after,
    )


@dataclass(frozen=True)
class AcquisitionLimits:
    schema_version: str
    max_attempts: int
    total_seconds: float
    request_seconds: float
    body_bytes: int
    archive_bytes: int
    zip_entries: int
    compression_ratio: float
    max_rows: int
    max_redirects: int
    backoff_seconds: tuple[float, ...]

    def __post_init__(self) -> None:
        if (
            self.schema_version != "acquisition-limits/v1"
            or type(self.max_redirects) is not int
            or self.max_redirects != 0
        ):
            raise ValueError("Only explicit no-redirect acquisition-limits/v1 is supported")
        for key in ("max_attempts", "body_bytes", "archive_bytes", "zip_entries", "max_rows"):
            value = getattr(self, key)
            if type(value) is not int or value <= 0:
                raise ValueError("Positive integer acquisition limit required")
        for value in (self.total_seconds, self.request_seconds, self.compression_ratio):
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise ValueError("Finite positive acquisition limit required")
        if not self.backoff_seconds or any(
            type(v) not in (int, float) or not math.isfinite(v) or v < 0
            for v in self.backoff_seconds
        ):
            raise ValueError("Explicit finite backoff schedule required")


def load_limits(path: Path | None = None) -> AcquisitionLimits:
    path = path or Path(__file__).resolve().parents[3] / "config/acquisition_limits.v1.json"
    try:
        body = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
        body["backoff_seconds"] = tuple(body["backoff_seconds"])
        return AcquisitionLimits(**body)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise failure("INVALID_ACQUISITION_LIMITS") from exc


def validate_request_options(timeout_seconds: float | None, max_attempts: int | None) -> None:
    if timeout_seconds is not None and (
        type(timeout_seconds) not in (int, float)
        or not math.isfinite(timeout_seconds)
        or timeout_seconds <= 0
    ):
        raise failure("INVALID_ACQUISITION_LIMITS")
    if max_attempts is not None and (type(max_attempts) is not int or max_attempts <= 0):
        raise failure("INVALID_ACQUISITION_LIMITS")


@dataclass
class RequestBudget:
    limits: AcquisitionLimits
    clock: Callable[[], float] = time.monotonic
    sleep: Callable[[float], None] = time.sleep
    attempts: int = 0
    started: float | None = None
    context: dict[str, object] = field(default_factory=dict)

    def remaining(self) -> float:
        now = self.clock()
        if self.started is None:
            self.started = now
        remaining = self.limits.total_seconds - (now - self.started)
        if remaining <= 0:
            raise failure("TOTAL_DEADLINE_EXCEEDED")
        return remaining

    def consume(self) -> float:
        remaining = self.remaining()
        if self.attempts >= self.limits.max_attempts:
            raise failure("ATTEMPT_BUDGET_EXCEEDED")
        self.attempts += 1
        return min(remaining, self.limits.request_seconds)

    def backoff(self) -> None:
        delay = self.limits.backoff_seconds[
            min(max(0, self.attempts - 1), len(self.limits.backoff_seconds) - 1)
        ]
        if delay >= self.remaining():
            raise failure("TOTAL_DEADLINE_EXCEEDED")
        if self.attempts >= self.limits.max_attempts:
            raise failure("ATTEMPT_BUDGET_EXCEEDED")
        self.sleep(delay)
        self.remaining()


def safe_url(url: str) -> str:
    parsed = urlsplit(url)
    # Evidence must never retain userinfo or query tokens, even on rejected URLs.
    authority = parsed.netloc.rsplit("@", 1)[-1]
    return urlunsplit((parsed.scheme, authority, parsed.path, "", ""))


def check_status(status: int, headers: Mapping[str, str]) -> None:
    if 300 <= status < 400:
        raise failure("REDIRECT_NOT_ALLOWED", status=status)
    if status in {401, 403, 451}:
        raise failure("HTTP_ACCESS_DENIED", status=status)
    if status == 429:
        raw = headers.get("retry-after", "")
        retry_after = None
        if raw.isascii() and raw.isdigit() and len(raw) <= 8:
            retry_after = str(int(raw))
        else:
            try:
                parsed = parsedate_to_datetime(raw)
                if parsed.tzinfo is not None:
                    retry_after = parsed.isoformat()
            except (ValueError, TypeError, OverflowError):
                pass
        raise failure("HTTP_RATE_LIMITED", status=status, retry_after=retry_after)
    if status == 404:
        raise failure("HTTP_NOT_FOUND", status=status)
    if status in {500, 502, 503, 504}:
        raise failure("HTTP_TRANSIENT", status=status, terminal=False)
    if status < 200 or status >= 300:
        raise failure("HTTP_REJECTED", status=status)


def check_body(payload: bytes, content_type: str, limits: AcquisitionLimits) -> None:
    if len(payload) > limits.body_bytes:
        raise failure("BODY_LIMIT_EXCEEDED", stage="validation")
    if not payload:
        raise failure("PAYLOAD_EMPTY", stage="validation")
    beginning = payload[:1024].lstrip().lower()
    if (
        "html" in content_type.lower()
        or beginning.startswith((b"<html", b"<!doctype", b"<head", b"<body"))
        or beginning.startswith((b"access denied", b"login required"))
    ):
        raise failure("PAYLOAD_HTML_DENIAL", stage="validation")


def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON field")
        result[key] = value
    return result


@dataclass(frozen=True)
class PayloadValidation:
    schema: str
    era: str
    rows: int
    state: str
    sha256: str


def _date(value: str) -> date:
    for pattern in ("%Y-%m-%d", "%d-%b-%Y", "%d-%b-%y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value.strip(), pattern).date()
        except ValueError:
            pass
    raise failure("TRADE_DATE_MISMATCH", stage="validation")


def _csv(
    payload: bytes,
    key: str,
    requested: date,
    legacy: bool,
    filename_date: bool,
    limits: AcquisitionLimits,
) -> tuple[str, int]:
    try:
        text = payload.decode("utf-8-sig", errors="strict")
    except UnicodeError as exc:
        raise failure("ENCODING_UNSUPPORTED", stage="validation") from exc
    reader = csv.reader(io.StringIO(text), strict=True)
    try:
        header = [v.strip().upper() for v in next(reader, [])]
        if len(set(header)) != len(header) or not header or any(not v for v in header):
            raise failure("SCHEMA_UNKNOWN", stage="validation")
        modern = {
            "TRADDT",
            "BIZDT",
            "ISIN",
            "TCKRSYMB",
            "OPNPRIC",
            "HGHPRIC",
            "LWPRIC",
            "CLSPRIC",
            "TTLTRADGVOL",
        }
        identity: tuple[str, ...]
        date_fields: tuple[str, ...]
        old_nse = {
            "SYMBOL",
            "SERIES",
            "OPEN",
            "HIGH",
            "LOW",
            "CLOSE",
            "TOTTRDQTY",
            "ISIN",
            "TIMESTAMP",
        }
        old_bse = {"SC_CODE", "OPEN", "HIGH", "LOW", "CLOSE", "NO_OF_SHRS", "ISIN_CODE"}
        if not legacy and modern.issubset(header):
            fields = ("OPNPRIC", "HGHPRIC", "LWPRIC", "CLSPRIC", "TTLTRADGVOL")
            identity, date_fields, schema = (
                ("ISIN", "TCKRSYMB"),
                ("TRADDT", "BIZDT"),
                "equity-udiff/v1",
            )
        elif key == "NSE_EQUITY_BHAVCOPY" and legacy and old_nse.issubset(header):
            fields = ("OPEN", "HIGH", "LOW", "CLOSE", "TOTTRDQTY")
            identity, date_fields, schema = (
                ("ISIN", "SYMBOL", "SERIES"),
                ("TIMESTAMP",),
                "nse-equity-legacy/v1",
            )
        elif key == "BSE_EQUITY_BHAVCOPY" and old_bse.issubset(header) and filename_date:
            fields = ("OPEN", "HIGH", "LOW", "CLOSE", "NO_OF_SHRS")
            identity, date_fields, schema = (
                ("ISIN_CODE", "SC_CODE"),
                (),
                "bse-equity-legacy-filename-date/v1",
            )
        else:
            raise failure("SCHEMA_UNKNOWN", stage="validation")
        count = 0
        seen: set[tuple[str, ...]] = set()
        for values in reader:
            if len(values) != len(header):
                raise failure("PARTIAL_PAYLOAD", stage="validation")
            row = dict(zip(header, values, strict=True))
            if any(_date(row[field]) != requested for field in date_fields):
                raise failure("TRADE_DATE_MISMATCH", stage="validation")
            row_key = tuple(row[field].strip() for field in identity)
            if not all(row_key) or row_key in seen:
                raise failure("PARTIAL_PAYLOAD", stage="validation")
            seen.add(row_key)
            try:
                numbers = [Decimal(row[field]) for field in fields]
            except InvalidOperation as exc:
                raise failure("PARTIAL_PAYLOAD", stage="validation") from exc
            if any(not number.is_finite() or number < 0 for number in numbers):
                raise failure("PARTIAL_PAYLOAD", stage="validation")
            opening, high, low, close, volume = numbers
            if (
                high < max(opening, low, close)
                or low > min(opening, high, close)
                or volume != volume.to_integral_value()
            ):
                raise failure("PARTIAL_PAYLOAD", stage="validation")
            count += 1
            if count > limits.max_rows:
                raise failure("BODY_LIMIT_EXCEEDED", stage="validation")
        if count == 0:
            raise failure("PAYLOAD_EMPTY", stage="validation")
        return schema, count
    except csv.Error as exc:
        raise failure("PARTIAL_PAYLOAD", stage="validation") from exc


def validate_payload(
    key: str,
    payload: bytes,
    requested: date | None,
    limits: AcquisitionLimits,
    content_type: str = "",
) -> PayloadValidation:
    check_body(payload, content_type, limits)
    era = "unknown" if requested is None else resolve_era(key, requested).name
    digest = hashlib.sha256(payload).hexdigest()
    if key in {"NSE_EQUITY_BHAVCOPY", "BSE_EQUITY_BHAVCOPY"}:
        mime = content_type.split(";", 1)[0].strip().lower()
        accepted = {
            "",
            "application/octet-stream",
            "application/zip",
            "application/x-zip-compressed",
            "text/csv",
            "application/csv",
            "text/plain",
        }
        if (
            mime not in accepted
            or ("zip" in mime and not payload.startswith(b"PK"))
            or ("csv" in mime and payload.startswith(b"PK"))
        ):
            raise failure("SCHEMA_UNKNOWN", stage="validation")
        if requested is None:
            raise failure("SCHEMA_UNKNOWN", stage="validation")
        legacy = key.startswith("NSE") and requested.year < 2020
        filename_date = False
        csv_payload = payload
        if payload.startswith(b"PK"):
            try:
                with zipfile.ZipFile(io.BytesIO(payload)) as zf:
                    entries = zf.infolist()
                    if (
                        len(entries) > limits.zip_entries
                        or sum(e.file_size for e in entries) > limits.archive_bytes
                    ):
                        raise failure("ARCHIVE_TOO_LARGE", stage="validation")
                    names = set()
                    for item in entries:
                        name = PurePosixPath(item.filename.replace("\\", "/"))
                        if (
                            name.is_absolute()
                            or ".." in name.parts
                            or ":" in item.filename
                            or item.filename in names
                            or item.flag_bits & 1
                            or stat.S_ISLNK(item.external_attr >> 16)
                            or name.suffix.lower() in {".zip", ".gz", ".7z"}
                        ):
                            raise failure("ZIP_ENTRY_UNSAFE", stage="validation")
                        names.add(item.filename)
                        if (
                            item.file_size > limits.archive_bytes
                            or item.file_size
                            > max(1, item.compress_size) * limits.compression_ratio
                        ):
                            raise failure("ARCHIVE_TOO_LARGE", stage="validation")
                    expected = (
                        (
                            (f"cm{requested:%d%b%Y}bhav.csv",)
                            if legacy
                            else (f"BhavCopy_NSE_CM_0_0_0_{requested:%Y%m%d}_F_0000.csv",)
                        )
                        if key.startswith("NSE")
                        else (
                            f"BhavCopy_BSE_CM_0_0_0_{requested:%Y%m%d}_F_0000.csv",
                            f"EQ_ISINCODE_{requested:%d%m%y}_T0.csv",
                            f"BSE_EQ_BHAVCOPY_{requested:%d%m%Y}_T0.csv",
                        )
                    )
                    chosen = [
                        e
                        for e in entries
                        if PurePosixPath(e.filename).name.lower() in {v.lower() for v in expected}
                    ]
                    if len(chosen) != 1:
                        csv_entries = [e for e in entries if e.filename.lower().endswith(".csv")]
                        reason = (
                            "TRADE_DATE_MISMATCH"
                            if len(csv_entries) == 1
                            and re.search(r"\d{8}|\d{2}[A-Za-z]{3}\d{4}", csv_entries[0].filename)
                            else "SCHEMA_UNKNOWN"
                        )
                        raise failure(reason, stage="validation")
                    filename_date = True
                    with zf.open(chosen[0]) as member:
                        csv_payload = member.read(limits.archive_bytes + 1)
                    if len(csv_payload) > limits.archive_bytes:
                        raise failure("ARCHIVE_TOO_LARGE", stage="validation")
            except (zipfile.BadZipFile, EOFError, RuntimeError, NotImplementedError) as exc:
                if isinstance(exc, DownloadError):
                    raise
                raise failure("ARCHIVE_INVALID", stage="validation") from exc
        elif key.startswith("NSE"):
            raise failure("ARCHIVE_INVALID", stage="validation")
        schema, rows = _csv(csv_payload, key, requested, legacy, filename_date, limits)
        return PayloadValidation(schema, era, rows, "PAYLOAD_STRUCTURALLY_VALID", digest)
    json_keys = {"NSE_CORPORATE_ACTIONS", "BSE_CORPORATE_ACTIONS", "NSE_FII_DII", "INDIA_VIX"}
    if key in json_keys:
        try:
            parsed = json.loads(payload.decode("utf-8-sig"), object_pairs_hook=unique_object)
        except (ValueError, UnicodeError) as exc:
            raise failure("SCHEMA_UNKNOWN", stage="validation") from exc
        if isinstance(parsed, dict) and any(
            field.lower() in {"message", "error", "login", "captcha"} for field in parsed
        ):
            raise failure("PAYLOAD_HTML_DENIAL", stage="validation")
        if not isinstance(parsed, (dict, list)) or not parsed:
            raise failure("SCHEMA_UNKNOWN", stage="validation")
        return PayloadValidation(
            "json-structure-only/v1", era, len(parsed), "HTTP_RECEIVED", digest
        )
    return PayloadValidation("unverified-format/v1", era, 0, "HTTP_RECEIVED", digest)
