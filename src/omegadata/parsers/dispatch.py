"""Explicit synthetic entry point and optional rights-aware pinned archive facade."""

from __future__ import annotations

import hashlib
import re
from dataclasses import replace
from datetime import date

from omegadata.parsers.contracts import Limits, ParseRequest, ParserError, ParseResult
from omegadata.parsers.nse_cm import decode, digest
from omegadata.parsers.reference_registry import select
from omegadata.track_a.raw_archive import RawArchive
from omegadata.track_a.source_rights import SourceOperation


def parse(raw: bytes, request: ParseRequest, limits: Limits | None = None) -> ParseResult:
    limits = limits if limits is not None else Limits()
    if type(raw) is not bytes:
        raise TypeError("BYTES_REQUIRED")
    actual = hashlib.sha256(raw).hexdigest()
    try:
        if request.observation_id is not None:
            raise ParserError("SOURCE_SCOPE_DENIED")
        profile = select(request)
        if type(request.requested_business_date) is not date:
            raise ParserError("DATE_MISMATCH")
        if (
            not isinstance(request.raw_sha256, str)
            or not re.fullmatch("[0-9a-f]{64}", request.raw_sha256)
            or request.raw_sha256 != actual
        ):
            raise ParserError("RAW_HASH_MISMATCH")
        rows, columns = decode(raw, request, profile, limits)
        return ParseResult(
            "PARSED_UNVERIFIED",
            actual,
            rows,
            semantic_sha256=digest(rows, columns, request),
            source_columns=columns,
            format_id=profile.format_id,
        )
    except ParserError as error:
        return ParseResult("QUARANTINED", actual, reasons=(error.reason_code,))


def parse_archive(
    archive: RawArchive, request: ParseRequest, consumer_purpose: SourceOperation
) -> ParseResult:
    if not request.observation_id:
        raise ValueError("OBSERVATION_REQUIRED")
    if consumer_purpose not in tuple(SourceOperation):
        raise ValueError("CONSUMER_PURPOSE_REQUIRED")
    # Existing service enforces current rights/source/date before payload read.
    raw, observation = archive.read_verified(
        request.observation_id,
        request.source_key,
        request.requested_business_date,
        consumer_purpose,
    )
    if observation.request.source_mode != request.source_mode:
        return ParseResult(
            "QUARANTINED", hashlib.sha256(raw).hexdigest(), reasons=("SOURCE_SCOPE_DENIED",)
        )
    return replace(
        parse(raw, replace(request, observation_id=None)), observation_id=request.observation_id
    )
