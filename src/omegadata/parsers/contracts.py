"""Frozen pure parser contracts; synthetic semantics confer no source authority."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal


class ParserError(ValueError):
    """Bounded code-only public failure, never payload excerpts."""

    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        super().__init__(reason_code)


@dataclass(frozen=True)
class Limits:
    body_bytes: int = 2_000_000
    archive_bytes: int = 8_000_000
    max_rows: int = 10_000
    compression_ratio: float = 100.0

    def __post_init__(self) -> None:
        for value, ceiling in (
            (self.body_bytes, 2_000_000),
            (self.archive_bytes, 8_000_000),
            (self.max_rows, 10_000),
        ):
            if type(value) is not int or not 0 < value <= ceiling:
                raise ValueError("INVALID_LIMIT")
        if (
            type(self.compression_ratio) not in (float, int)
            or not math.isfinite(self.compression_ratio)
            or not 0 < self.compression_ratio <= 100
        ):
            raise ValueError("INVALID_LIMIT")


@dataclass(frozen=True)
class ParseRequest:
    source_key: str
    requested_business_date: date
    raw_sha256: str
    source_mode: str
    format_id: str
    parser_version: str
    reference_id: str
    observation_id: str | None = None
    expected_record_count: int | None = None


@dataclass(frozen=True)
class ParsedBar:
    symbol: str
    series: str
    isin: str | None
    source_row_index: int
    trade_date: date
    business_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    price_lexemes: tuple[str, ...]
    unknown_fields: tuple[tuple[str, str], ...]
    volume_lexeme: str = ""
    source_key: str = "NSE_EQUITY_BHAVCOPY"
    exchange: str = "NSE"
    scrip_code: str | None = None
    published_at: None = None
    units: str = "SYNTHETIC_PRICE_AND_INTEGER_QUANTITY"


@dataclass(frozen=True)
class ParseResult:
    state: Literal["PARSED_UNVERIFIED", "QUARANTINED"]
    raw_sha256: str
    rows: tuple[ParsedBar, ...] = ()
    reasons: tuple[str, ...] = ()
    semantic_sha256: str | None = None
    source_columns: tuple[str, ...] = ()
    source_key: str = "NSE_EQUITY_BHAVCOPY"
    format_id: str | None = None
    parser_version: str = "syn-v1"
    reference_id: str = "synthetic-v1"
    reference_classification: str = "SYNTHETIC_TEST_ONLY"
    observation_id: str | None = None
