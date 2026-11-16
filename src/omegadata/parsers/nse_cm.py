"""Strict bounded illustrative CSV/ZIP decoding. No I/O, clock or locale."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import stat
import zipfile
import zlib
from datetime import date
from decimal import Decimal

from omegadata.parsers.contracts import Limits, ParsedBar, ParseRequest, ParserError
from omegadata.parsers.reference_registry import LEGACY, Profile


def unpack(raw: bytes, limits: Limits) -> bytes:
    if len(raw) > limits.body_bytes:
        raise ParserError("ZIP_BUDGET")
    if not raw.startswith(b"PK"):
        if len(raw) > limits.archive_bytes:
            raise ParserError("ZIP_BUDGET")
        return raw
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            if len(entries) != 1:
                raise ParserError("ZIP_UNSAFE")
            info = entries[0]
            if (
                info.filename != "synthetic.csv"
                or info.is_dir()
                or stat.S_IFMT(info.external_attr >> 16) not in (0, stat.S_IFREG)
                or info.flag_bits & 1
                or info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
            ):
                raise ParserError("ZIP_UNSAFE")
            if (
                info.file_size > limits.archive_bytes
                or info.file_size / max(info.compress_size, 1) > limits.compression_ratio
            ):
                raise ParserError("ZIP_BUDGET")
            # No arbitrary trailer, comments or concatenated containers in this SYN contract.
            if len(raw) < 22 or raw[-22:-18] != b"PK\x05\x06" or raw[-2:] != b"\x00\x00":
                raise ParserError("ZIP_INVALID")
            with archive.open(info) as member:
                body = member.read(limits.archive_bytes + 1)
            if len(body) != info.file_size or len(body) > limits.archive_bytes:
                raise ParserError("ZIP_BUDGET")
            if body.startswith(b"PK"):
                raise ParserError("ZIP_UNSAFE")
            return body
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, OSError, EOFError, zlib.error):
        raise ParserError("ZIP_INVALID") from None


def lexical(text: str) -> None:
    """CSV reader strict=True still accepts quotes in unquoted fields; reject them."""
    state = "start"
    for char in text:
        if char == "\x00" or (ord(char) < 32 and char not in "\n\t"):
            raise ParserError("CSV_INVALID")
        if state == "quoted":
            if char == '"':
                state = "closed"
        elif state == "closed":
            if char == '"':
                state = "quoted"
            elif char in ",\n":
                state = "start"
            else:
                raise ParserError("CSV_INVALID")
        elif char == '"':
            if state != "start":
                raise ParserError("CSV_INVALID")
            state = "quoted"
        elif char in ",\n":
            state = "start"
        else:
            state = "plain"
    if state == "quoted":
        raise ParserError("CSV_INVALID")


def price(value: str) -> Decimal:
    if not re.fullmatch(r"[0-9]{1,12}(?:\.[0-9]{1,8})?", value, re.ASCII):
        raise ParserError("PRICE_INVALID")
    return Decimal(value)


def day(value: str, expected: date) -> date:
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value, re.ASCII):
        raise ParserError("DATE_MISMATCH")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ParserError("DATE_MISMATCH") from None
    if parsed != expected:
        raise ParserError("DATE_MISMATCH")
    return parsed


def decode(
    raw: bytes, request: ParseRequest, profile: Profile, limits: Limits
) -> tuple[tuple[ParsedBar, ...], tuple[str, ...]]:
    try:
        text = unpack(raw, limits).decode("utf-8", errors="strict")
    except UnicodeError:
        raise ParserError("CSV_INVALID") from None
    text = text.replace("\r\n", "\n")
    if "\r" in text:
        raise ParserError("CSV_INVALID")
    lexical(text)
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    try:
        header = next(reader, [])
        if (
            not header
            or len(header) > 64
            or any(not h or len(h) > 128 or h != h.strip() for h in header)
        ):
            raise ParserError("HEADER_MISSING")
        if len({h.casefold() for h in header}) != len(header):
            raise ParserError("HEADER_DUPLICATE")
        if not set(profile.columns).issubset(header):
            raise ParserError("HEADER_MISSING")
        rows: list[ParsedBar] = []
        identities: set[tuple[str, str, str | None, date]] = set()
        for ordinal, fields in enumerate(reader, 1):
            if ordinal > limits.max_rows:
                raise ParserError("ROW_INVALID")
            if len(fields) != len(header) or any(len(v) > 4096 for v in fields):
                raise ParserError("CSV_INVALID")
            record = dict(zip(header, fields, strict=True))
            columns = profile.columns
            symbol, series, isin = (record[c] for c in columns[:3])
            if (
                not symbol
                or not series
                or any(
                    len(v) > 128 or v != v.strip() or any(ord(c) < 32 for c in v)
                    for v in (symbol, series, isin)
                )
            ):
                raise ParserError("IDENTITY_AMBIGUOUS")
            dates = (columns[3],) if profile == LEGACY else columns[3:5]
            trade_date = day(record[dates[0]], request.requested_business_date)
            business_date = day(record[dates[-1]], request.requested_business_date)
            start = 4 if profile == LEGACY else 5
            lexemes = tuple(record[c] for c in columns[start : start + 4])
            opening, high, low, close = (price(value) for value in lexemes)
            if high < max(opening, close, low) or low > min(opening, close, high):
                raise ParserError("PRICE_INVALID")
            volume_token = record[columns[start + 4]]
            if not re.fullmatch(r"[0-9]{1,19}", volume_token, re.ASCII):
                raise ParserError("VOLUME_INVALID")
            volume = int(volume_token)
            if volume > 2**63 - 1:
                raise ParserError("VOLUME_INVALID")
            identity = (symbol, series, isin or None, trade_date)
            if identity in identities:
                raise ParserError("IDENTITY_AMBIGUOUS")
            identities.add(identity)
            unknown = tuple((h, record[h]) for h in header if h not in columns)
            rows.append(
                ParsedBar(
                    symbol,
                    series,
                    isin or None,
                    ordinal,
                    trade_date,
                    business_date,
                    opening,
                    high,
                    low,
                    close,
                    volume,
                    lexemes,
                    unknown,
                    volume_lexeme=volume_token,
                )
            )
    except csv.Error:
        raise ParserError("CSV_INVALID") from None
    if not rows:
        raise ParserError("ROW_INVALID")
    if request.expected_record_count is not None and (
        type(request.expected_record_count) is not int or request.expected_record_count != len(rows)
    ):
        raise ParserError("INTEGRITY")
    return tuple(rows), tuple(header)


def exact(value: Decimal) -> str:
    # format(f) never rounds to the ambient Decimal context, unlike normalize().
    result = format(value, "f")
    return result.rstrip("0").rstrip(".") if "." in result else result


def digest(rows: tuple[ParsedBar, ...], columns: tuple[str, ...], request: ParseRequest) -> str:
    body = {
        "source": request.source_key,
        "format": request.format_id,
        "parser": request.parser_version,
        "reference": request.reference_id,
        "classification": "SYNTHETIC_TEST_ONLY",
        "columns": columns,
        "rows": [
            {
                "symbol": r.symbol,
                "series": r.series,
                "isin": r.isin,
                "scrip": r.scrip_code,
                "ordinal": r.source_row_index,
                "trade_date": r.trade_date.isoformat(),
                "business_date": r.business_date.isoformat(),
                "prices": [exact(v) for v in (r.open, r.high, r.low, r.close)],
                "volume": r.volume,
                "unknown": r.unknown_fields,
            }
            for r in rows
        ],
    }
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()
