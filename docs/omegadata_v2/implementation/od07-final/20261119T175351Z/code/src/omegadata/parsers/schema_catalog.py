"""Explicit implemented decoder contracts, never official era certification.

No calendar routing or rights decision is derived from this catalogue. JSON
market feeds/BSE/FO are not new OD05-supported decoders merely because the
production acquisition registry lists them. Their promotion requires evidence.
"""
from __future__ import annotations

from typing import Any

from omegadata.parsers.reference_registry import LEGACY, MODERN


def supported_formats() -> tuple[dict[str, Any], ...]:
    """Return fresh metadata values; callers cannot mutate registry state."""
    return tuple({
        "source_id": "NSE_EQUITY_BHAVCOPY",
        "source_venue": "NSE_CM",
        "source_format": "CSV_OR_SINGLE_MEMBER_ZIP",
        "format_id": profile.format_id,
        "format_era": "ILLUSTRATIVE_NOT_AN_OFFICIAL_ERA",
        "effective_start": None,
        "effective_end": None,
        "schema_version": "od05.illustrative-cm/v1",
        "parser_version": "syn-v1",
        "encoding_rules": "UTF8_STRICT_CRLF_OR_LF",
        "date_rules": "EXACT_REQUESTED_ISO_DATE; NO_INTRADAY_TIMESTAMP_ORDER",
        "numeric_rules": "DECIMAL_FIXED_POINT_12_INTEGER_8_FRACTION; INT64_NONNEGATIVE_VOLUME",
        "units": "SYNTHETIC_PRICE_AND_INTEGER_QUANTITY",
        "recognized_columns": list(profile.columns),
        "required_columns": list(profile.columns),
        "optional_columns": [],
        "nullable_values": ["ISIN"],
        "unknown_column_policy": "PRESERVE_NOT_INTERPRETED",
        "source_authentication_state": "UNVERIFIED",
        "content_permission_state": "REGRESSION_ONLY_NO_SOURCE_GRANT",
        "golden_source_acceptance": "BLOCKED_AUTHENTIC_SOURCE_VALIDATION",
    } for profile in (LEGACY, MODERN))
