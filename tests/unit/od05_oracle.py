"""Independent literal SYN oracle; deliberately imports no production parser."""

import hashlib
import json
from pathlib import Path

LEGACY = b"SYMBOL,SERIES,ISIN,TIMESTAMP,OPEN,HIGH,LOW,CLOSE,TOTTRDQTY,NOTE\n000SYN,EQ,00001234,2019-12-31,10.10,12.20,9.05,11.15,0,inert\n"
MODERN = b"TckrSymb,SctySrs,ISIN,TradDt,BizDt,OpnPric,HghPric,LwPric,ClsPric,TtlTradgVol,NOTE\n000SYN,EQ,00001234,2026-04-10,2026-04-10,10.10,12.20,9.05,11.15,0,inert\n"
EXPECTED = {
    "symbol": "000SYN",
    "series": "EQ",
    "isin": "00001234",
    "ordinal": 1,
    "scaled_prices": [1010, 1220, 905, 1115],
    "volume": 0,
    "unknown": [("NOTE", "inert")],
}


def scaled(lexeme):
    """Independent integer grammar, no Decimal/parser functions used."""
    whole, dot, fraction = lexeme.partition(".")
    assert whole.isascii() and whole.isdecimal() and (not dot or fraction.isdecimal())
    assert len(fraction) <= 2
    return int(whole) * 100 + int(fraction.ljust(2, "0") or "0")


def canonical(body):
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def expected_digest(day, format_id, parser_version="syn-v1"):
    body = {
        "source": "NSE_EQUITY_BHAVCOPY",
        "format": format_id,
        "parser": parser_version,
        "reference": "synthetic-v1",
        "classification": "SYNTHETIC_TEST_ONLY",
        "columns": (LEGACY if format_id == "legacy-illustrative" else MODERN)
        .decode()
        .splitlines()[0]
        .split(","),
        "rows": [
            {
                "symbol": "000SYN",
                "series": "EQ",
                "isin": "00001234",
                "scrip": None,
                "ordinal": 1,
                "trade_date": day,
                "business_date": day,
                "prices": ["10.1", "12.2", "9.05", "11.15"],
                "volume": 0,
                "unknown": [["NOTE", "inert"]],
            }
        ],
    }
    return hashlib.sha256(canonical(body)).hexdigest()


def check(row):
    assert row.symbol == EXPECTED["symbol"] and row.series == EXPECTED["series"]
    assert row.isin == EXPECTED["isin"] and row.source_row_index == EXPECTED["ordinal"]
    assert [scaled(s) for s in row.price_lexemes] == EXPECTED["scaled_prices"]
    assert [scaled(format(p, "f")) for p in (row.open, row.high, row.low, row.close)] == EXPECTED[
        "scaled_prices"
    ]
    assert row.volume == EXPECTED["volume"] and list(row.unknown_fields) == EXPECTED["unknown"]
    assert row.published_at is None


def require_corpus(path: Path):
    assert path.is_file(), "MISSING_ORACLE"
    body = path.read_bytes()
    assert body == LEGACY, "CORRUPT_OR_EMPTY_ORACLE"
    return hashlib.sha256(body).hexdigest()
