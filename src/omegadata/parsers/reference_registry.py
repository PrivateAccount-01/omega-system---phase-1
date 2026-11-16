"""Fixed illustrative profiles, not official exchange format specifications."""

from __future__ import annotations

from dataclasses import dataclass

from omegadata.parsers.contracts import ParseRequest, ParserError


@dataclass(frozen=True)
class Profile:
    format_id: str
    columns: tuple[str, ...]


LEGACY = Profile(
    "legacy-illustrative",
    ("SYMBOL", "SERIES", "ISIN", "TIMESTAMP", "OPEN", "HIGH", "LOW", "CLOSE", "TOTTRDQTY"),
)
MODERN = Profile(
    "udiff-illustrative",
    (
        "TckrSymb",
        "SctySrs",
        "ISIN",
        "TradDt",
        "BizDt",
        "OpnPric",
        "HghPric",
        "LwPric",
        "ClsPric",
        "TtlTradgVol",
    ),
)


def select(request: ParseRequest) -> Profile:
    if request.source_key != "NSE_EQUITY_BHAVCOPY" or request.source_mode != "SYNTHETIC_TEST_ONLY":
        raise ParserError("SOURCE_SCOPE_DENIED")
    if request.parser_version != "syn-v1":
        raise ParserError("VERSION_UNSUPPORTED")
    if request.reference_id != "synthetic-v1":
        raise ParserError("REFERENCE_PENDING")
    if request.format_id in ("unknown", "ambiguous", "official-2024-cutover"):
        raise ParserError("ERA_UNKNOWN")
    for profile in (LEGACY, MODERN):
        if profile.format_id == request.format_id:
            return profile
    raise ParserError("FORMAT_UNSUPPORTED")
