from __future__ import annotations

import csv
import io
import json
import zipfile
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from omegadata.track_b.corporate_action_parser import CorporateActionParser

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_ROOT = PROJECT_ROOT / "data" / "raw"
OUTPUT_PATH = PROJECT_ROOT / "tests" / "fixtures" / "official_source" / "adjustment_reference_corpus.json"
PRICE_MONTH_DIR = RAW_ROOT / "nse_equity_bhavcopy" / "year=2026" / "month=04"
ACTION_GLOB = RAW_ROOT / "nse_corporate_actions" / "year=2026"
ASSERTION_DATES = ("2026-04-01", "2026-04-02", "2026-04-06", "2026-04-07")
PARSER = CorporateActionParser()


def _to_iso_date(value: str) -> str:
    return datetime.strptime(value, "%d-%b-%Y").date().isoformat()


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


def _price_history() -> dict[str, list[dict[str, str]]]:
    history: dict[str, dict[str, dict[str, str]]] = {}
    for zip_path in sorted(PRICE_MONTH_DIR.glob("*.zip")):
        rows = _load_bhavcopy_rows(zip_path)
        trade_date = f"{zip_path.stem[:4]}-{zip_path.stem[4:6]}-{zip_path.stem[6:8]}"
        for symbol, row in rows.items():
            history.setdefault(symbol, {})[trade_date] = {
                "trade_date": trade_date,
                "close": str(row.get("CLOSE") or row.get("ClsPric") or "").strip(),
                "volume": str(row.get("TOTTRDQTY") or row.get("TtlTradgVol") or "").strip(),
            }
    return {
        symbol: [rows[key] for key in sorted(rows)]
        for symbol, rows in history.items()
    }


def _adjustment_factors(action_type: str, parameters: dict[str, str]) -> tuple[Decimal, Decimal]:
    if action_type == "BONUS":
        numerator = Decimal(parameters["bonus_ratio_numerator"])
        denominator = Decimal(parameters["bonus_ratio_denominator"])
        ratio = numerator / denominator
        price_factor = Decimal("1") / (Decimal("1") + ratio)
        return price_factor, Decimal("1") / price_factor
    if action_type == "SPLIT":
        old_face_value = Decimal(parameters["old_face_value"])
        new_face_value = Decimal(parameters["new_face_value"])
        return new_face_value / old_face_value, old_face_value / new_face_value
    return Decimal("1"), Decimal("1")


def _assertions(
    *,
    action_type: str,
    parameters: dict[str, str],
    prices_by_date: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    price_factor, volume_factor = _adjustment_factors(action_type, parameters)
    return [
        {
            "trade_date": trade_date,
            "raw_close": prices_by_date[trade_date]["close"],
            "raw_volume": prices_by_date[trade_date]["volume"],
            "expected_adjusted_close": _quantize_price(
                _parse_decimal(prices_by_date[trade_date]["close"]) * price_factor
            ),
            "expected_adjusted_volume": _quantize_volume(
                _parse_decimal(prices_by_date[trade_date]["volume"]) * volume_factor
            ),
            "expected_cumulative_price_factor": _quantize_factor(price_factor),
            "expected_cumulative_volume_factor": _quantize_factor(volume_factor),
        }
        for trade_date in ASSERTION_DATES
        if trade_date in prices_by_date
    ]


def _raw_action_rows() -> list[dict[str, str]]:
    seen: set[tuple[str, str, str]] = set()
    rows: list[dict[str, str]] = []
    for path in sorted(ACTION_GLOB.glob("month=*/*.bin")):
        parsed = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        if not isinstance(parsed, list):
            continue
        for item in parsed:
            if not isinstance(item, dict):
                continue
            symbol = str(item.get("symbol") or "").strip()
            isin = str(item.get("isin") or "").strip()
            subject = str(item.get("subject") or "").strip()
            ex_date = str(item.get("exDate") or "").strip()
            if not symbol or not isin or not subject or not ex_date:
                continue
            dedupe_key = (isin, ex_date, subject)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            rows.append(
                {
                    "isin": isin,
                    "symbol": symbol,
                    "company_name": str(item.get("comp") or symbol).strip(),
                    "subject": subject,
                    "ex_date": _to_iso_date(ex_date),
                    "record_date": _to_iso_date(str(item.get("recDate") or ex_date).strip()),
                    "snapshot_path": path.relative_to(PROJECT_ROOT).as_posix(),
                }
            )
    return rows


def build_reference_corpus() -> dict[str, object]:
    price_history = _price_history()
    cases: list[dict[str, object]] = []

    for raw in _raw_action_rows():
        prices = price_history.get(raw["symbol"])
        if not prices:
            continue
        prices_by_date = {row["trade_date"]: row for row in prices}
        parameters: dict[str, object] = {}
        action_type = PARSER.map_action_type(raw["subject"])
        PARSER.enrich_payload_from_subject(
            payload=parameters,
            action_type=action_type,
            purpose=raw["subject"],
        )
        normalized_parameters = {key: str(value) for key, value in parameters.items()}
        cases.append(
            {
                "label": f"{raw['symbol']}_{raw['ex_date']}_{action_type.value}",
                "isin": raw["isin"],
                "symbol": raw["symbol"],
                "company_name": raw["company_name"],
                "action_type": action_type.value,
                "ex_date": raw["ex_date"],
                "record_date": raw["record_date"],
                "subject": raw["subject"],
                "parameters": normalized_parameters,
                "snapshot_path": raw["snapshot_path"],
                "price_paths": list(
                    dict.fromkeys(
                        f"data/raw/nse_equity_bhavcopy/year=2026/month=04/{row['trade_date'].replace('-', '')}.zip"
                        for row in prices
                    )
                ),
                "prices": prices,
                "assertions": _assertions(
                    action_type=action_type.value,
                    parameters=normalized_parameters,
                    prices_by_date=prices_by_date,
                ),
            }
        )

    transformational_types = {"BONUS", "SPLIT", "SPLIT_REVERSE", "RIGHTS", "RIGHTS_RENOUNCE", "MERGER_TARGET", "DEMERGER_PARENT"}
    transformational_cases = [case for case in cases if case["action_type"] in transformational_types]
    return {
        "case_count": len(cases),
        "transformational_case_count": len(transformational_cases),
        "transformational_case_labels": [case["label"] for case in transformational_cases],
        "cases": cases,
    }


def main() -> None:
    corpus = build_reference_corpus()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(corpus, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH} with {corpus['case_count']} cases")


if __name__ == "__main__":
    main()
