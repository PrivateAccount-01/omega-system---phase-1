from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import zipfile


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_ROOT = PROJECT_ROOT / "data" / "raw"
OUTPUT_PATH = PROJECT_ROOT / "tests" / "fixtures" / "adjustment_reference_corpus.json"


@dataclass(frozen=True)
class ReferenceCaseSpec:
    isin: str
    symbol: str
    action_type: str
    ex_date: str
    record_date: str
    subject: str
    snapshot_path: str
    assertion_dates: tuple[str, ...]
    parameters: dict[str, str]


CASE_SPECS = (
    ReferenceCaseSpec(
        isin="INE200M01013",
        symbol="VBL",
        action_type="DIVIDEND_CASH",
        ex_date="2026-04-08",
        record_date="2026-04-08",
        subject="Dividend - Re 0.50 Per Share",
        snapshot_path="data/raw/nse_corporate_actions/year=2026/month=04/20260402.bin",
        assertion_dates=("2026-04-01", "2026-04-02", "2026-04-06", "2026-04-07"),
        parameters={"dividend_per_share": "0.50"},
    ),
    ReferenceCaseSpec(
        isin="INE039O01011",
        symbol="JASH",
        action_type="DIVIDEND_CASH",
        ex_date="2026-04-10",
        record_date="2026-04-10",
        subject="Interim Dividend - Re 0.60 Per Share",
        snapshot_path="data/raw/nse_corporate_actions/year=2026/month=04/20260402.bin",
        assertion_dates=("2026-04-01", "2026-04-02", "2026-04-06", "2026-04-07"),
        parameters={"dividend_per_share": "0.60"},
    ),
    ReferenceCaseSpec(
        isin="INE219Y01018",
        symbol="RMDRIP",
        action_type="BONUS",
        ex_date="2026-04-10",
        record_date="2026-04-10",
        subject="Bonus 5:7",
        snapshot_path="data/raw/nse_corporate_actions/year=2026/month=04/20260402.bin",
        assertion_dates=("2026-04-01", "2026-04-02", "2026-04-06", "2026-04-07"),
        parameters={"bonus_ratio_numerator": "5", "bonus_ratio_denominator": "7"},
    ),
)


def _parse_decimal(value: str) -> Decimal:
    return Decimal(str(value).replace(",", "").strip())


def _quantize_price(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))


def _quantize_volume(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


def _quantize_factor(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.000000000001"), rounding=ROUND_HALF_UP))


def _load_bhavcopy_rows(zip_path: Path) -> dict[str, dict[str, str]]:
    with zipfile.ZipFile(zip_path) as zf:
        csv_name = next(name for name in zf.namelist() if name.lower().endswith(".csv"))
        with zf.open(csv_name) as handle:
            reader = csv.DictReader(io.TextIOWrapper(handle, encoding="utf-8"))
            rows = {}
            for row in reader:
                symbol = (row.get("SYMBOL") or row.get("TckrSymb") or "").strip()
                if symbol:
                    rows[symbol] = row
            return rows


def _read_prices(symbol: str) -> list[dict[str, str]]:
    month_dir = RAW_ROOT / "nse_equity_bhavcopy" / "year=2026" / "month=04"
    prices: list[dict[str, str]] = []
    for zip_path in sorted(month_dir.glob("*.zip")):
        rows = _load_bhavcopy_rows(zip_path)
        if symbol not in rows:
            continue
        row = rows[symbol]
        prices.append(
            {
                "trade_date": f"{zip_path.stem[:4]}-{zip_path.stem[4:6]}-{zip_path.stem[6:8]}",
                "close": str(row.get("CLOSE") or row.get("ClsPric") or "").strip(),
                "volume": str(row.get("TOTTRDQTY") or row.get("TtlTradgVol") or "").strip(),
            }
        )
    return prices


def _expected_values(spec: ReferenceCaseSpec, trade_date: str, prices_by_date: dict[str, dict[str, str]]) -> dict[str, str]:
    row = prices_by_date[trade_date]
    raw_close = _parse_decimal(row["close"])
    raw_volume = _parse_decimal(row["volume"])

    if spec.action_type == "BONUS":
        factor = Decimal("7") / Decimal("12")
        volume_factor = Decimal("12") / Decimal("7")
    else:
        factor = Decimal("1")
        volume_factor = Decimal("1")

    return {
        "trade_date": trade_date,
        "raw_close": row["close"],
        "raw_volume": row["volume"],
        "expected_adjusted_close": _quantize_price(raw_close * factor),
        "expected_adjusted_volume": _quantize_volume(raw_volume * volume_factor),
        "expected_cumulative_price_factor": _quantize_factor(factor),
        "expected_cumulative_volume_factor": _quantize_factor(volume_factor),
    }


def build_reference_corpus() -> dict[str, object]:
    cases: list[dict[str, object]] = []
    for spec in CASE_SPECS:
        prices = _read_prices(spec.symbol)
        prices_by_date = {row["trade_date"]: row for row in prices}
        assertions = [
            _expected_values(spec, trade_date=trade_date, prices_by_date=prices_by_date)
            for trade_date in spec.assertion_dates
        ]
        cases.append(
            {
                "isin": spec.isin,
                "symbol": spec.symbol,
                "action_type": spec.action_type,
                "ex_date": spec.ex_date,
                "record_date": spec.record_date,
                "subject": spec.subject,
                "parameters": spec.parameters,
                "snapshot_path": spec.snapshot_path,
                "price_paths": [
                    f"data/raw/nse_equity_bhavcopy/year=2026/month=04/{row['trade_date'].replace('-', '')}.zip"
                    for row in prices
                ],
                "prices": prices,
                "assertions": assertions,
            }
        )

    return {
        "case_count": sum(len(case["assertions"]) for case in cases),
        "cases": cases,
    }


def main() -> None:
    corpus = build_reference_corpus()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(corpus, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH} with {corpus['case_count']} assertions")


if __name__ == "__main__":
    main()
