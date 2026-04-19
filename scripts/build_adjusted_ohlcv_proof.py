from __future__ import annotations

import argparse
import csv
import io
import json
import zipfile
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

from omegadata.db.models import ConfirmedCorporateAction, InstrumentMaster, PriceRecord, SymbolMap
from omegadata.db.session import get_session, init_db
from omegadata.domain import ConfidenceLevel, CorporateActionType, Exchange, InstrumentType
from omegadata.track_b.adjustment_engine import PriceAdjustmentEngine

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = REPO_ROOT / "tests/fixtures/official_source/official_transformational_case_specs.json"
OUT_PATH = REPO_ROOT / "artifacts/verification/adjusted_ohlcv_proof.json"


def _load_specs() -> list[dict[str, object]]:
    payload = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("official_transformational_case_specs.json must be a list")
    return [item for item in payload if isinstance(item, dict)]


def _extract_price_rows(path: Path, *, symbol: str, isin: str) -> list[dict[str, Decimal | date]]:
    matched_rows: list[dict[str, Decimal | date]] = []
    symbol_fallback_rows: list[dict[str, Decimal | date]] = []
    with zipfile.ZipFile(path) as zf:
        name = [item for item in zf.namelist() if item.lower().endswith(".csv")][0]
        reader = csv.DictReader(io.TextIOWrapper(zf.open(name), encoding="utf-8"))
        for row in reader:
            found_symbol = str(row.get("SYMBOL") or row.get("TckrSymb") or "").strip().upper()
            found_isin = str(row.get("ISIN") or row.get("ISIN_NUMBER") or "").strip().upper()
            if found_symbol != symbol.upper():
                continue
            trade_date_text = str(row.get("TradDt") or row.get("DATE1") or row.get("TIMESTAMP") or "")
            trade_date = (
                date.fromisoformat(trade_date_text)
                if "-" in trade_date_text
                else datetime.strptime(trade_date_text, "%d-%b-%Y").date()
            )
            payload = {
                "trade_date": trade_date,
                "observed_isin": found_isin,
                "open_price": Decimal(str(row.get("OpnPric") or row.get("OPEN"))),
                "high_price": Decimal(str(row.get("HghPric") or row.get("HIGH"))),
                "low_price": Decimal(str(row.get("LwPric") or row.get("LOW"))),
                "close_price": Decimal(str(row.get("ClsPric") or row.get("CLOSE"))),
                "volume": Decimal(str(row.get("TtlTradgVol") or row.get("TOTTRDQTY"))),
            }
            if found_isin == isin.upper():
                matched_rows.append(payload)
            else:
                symbol_fallback_rows.append(payload)
    return matched_rows or symbol_fallback_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an official-source-backed adjusted OHLCV proof artifact.")
    parser.add_argument("--case-label", default="NESTLEIND_2024-01-05_SPLIT")
    parser.add_argument("--db-url", default="sqlite:///artifacts/verification/adjusted_ohlcv_proof.sqlite")
    args = parser.parse_args()

    from omegadata.config import settings

    settings.db_url = args.db_url
    proof_db = REPO_ROOT / args.db_url.removeprefix("sqlite:///")
    if proof_db.exists():
        proof_db.unlink()
    init_db()

    spec = next(item for item in _load_specs() if item.get("label") == args.case_label)
    isin = str(spec["isin"])
    symbol = str(spec["symbol"])
    ex_date = date.fromisoformat(str(spec["ex_date"]))
    record_date = date.fromisoformat(str(spec["record_date"]))
    action_type = CorporateActionType(str(spec["action_type"]))
    parameters = dict(spec.get("parameters", {}))
    price_paths = [REPO_ROOT / str(item) for item in spec.get("price_paths", [])]
    assertion_dates = {date.fromisoformat(str(item)) for item in spec.get("assertion_dates", [])}

    extracted_rows: list[dict[str, Decimal | date]] = []
    observed_isins: set[str] = set()
    for path in price_paths:
        current_rows = _extract_price_rows(path, symbol=symbol, isin=isin)
        extracted_rows.extend(current_rows)
        observed_isins.update(str(row.get("observed_isin") or "") for row in current_rows)

    persisted_isin = next((value for value in observed_isins if value), isin)

    proof_rows: list[dict[str, object]] = []
    completeness_ok = True
    with get_session() as session:
        session.add(
            InstrumentMaster(
                isin=persisted_isin,
                instrument_type=InstrumentType.EQUITY,
                primary_exchange=Exchange.NSE,
                company_name=str(spec["company_name"]),
                listed_date=min(date.fromisoformat(str(item)) for item in spec.get("price_dates", [])),
                active=True,
            )
        )
        session.add(
            SymbolMap(
                isin=persisted_isin,
                exchange=Exchange.NSE,
                symbol=symbol,
                valid_from=min(date.fromisoformat(str(item)) for item in spec.get("price_dates", [])),
                valid_to=None,
            )
        )
        for row in extracted_rows:
            session.add(
                PriceRecord(
                    isin=persisted_isin,
                    exchange=Exchange.NSE,
                    trade_date=row["trade_date"],  # type: ignore[index]
                    open_price=row["open_price"],  # type: ignore[index]
                    high_price=row["high_price"],  # type: ignore[index]
                    low_price=row["low_price"],  # type: ignore[index]
                    close_price=row["close_price"],  # type: ignore[index]
                    volume=row["volume"],  # type: ignore[index]
                    raw_source="nse_bhavcopy",
                    confidence_score=Decimal("1.00"),
                )
            )
        session.add(
            ConfirmedCorporateAction(
                isin=persisted_isin,
                action_type=action_type,
                confidence=ConfidenceLevel.HIGH,
                announcement_date=record_date,
                ex_date=ex_date,
                record_date=record_date,
                parameters={k: (None if v is None else str(v)) for k, v in parameters.items()},
                source_preference=Exchange.NSE,
                superseded=False,
            )
        )
        session.flush()
        engine = PriceAdjustmentEngine()
        adjusted_count = engine.recompute_adjusted_series(session, isin=persisted_isin, exchange=Exchange.NSE)
        rows = session.scalars(
            select(PriceRecord)
            .where(PriceRecord.isin == persisted_isin)
            .order_by(PriceRecord.trade_date.asc())
        ).all()
        for row in rows:
            if row.trade_date not in assertion_dates:
                continue
            current = {
                "trade_date": row.trade_date.isoformat(),
                "raw_open": str(row.open_price),
                "raw_high": str(row.high_price),
                "raw_low": str(row.low_price),
                "raw_close": str(row.close_price),
                "raw_volume": str(row.volume),
                "adjusted_open": None if row.adjusted_open_price is None else str(row.adjusted_open_price),
                "adjusted_high": None if row.adjusted_high_price is None else str(row.adjusted_high_price),
                "adjusted_low": None if row.adjusted_low_price is None else str(row.adjusted_low_price),
                "adjusted_close": None if row.adjusted_close_price is None else str(row.adjusted_close_price),
                "adjusted_volume": None if row.adjusted_volume is None else str(row.adjusted_volume),
                "price_factor": None if row.cumulative_price_factor is None else str(row.cumulative_price_factor),
                "volume_factor": None if row.cumulative_volume_factor is None else str(row.cumulative_volume_factor),
                "adjustment_chain": row.adjustment_chain or [],
            }
            fields = [
                current["adjusted_open"],
                current["adjusted_high"],
                current["adjusted_low"],
                current["adjusted_close"],
                current["adjusted_volume"],
            ]
            completeness_ok = completeness_ok and all(value is not None for value in fields)
            proof_rows.append(current)

    artifact = {
        "generated_at": datetime.now(UTC).isoformat(),
        "case_label": args.case_label,
        "expected_isin": isin,
        "observed_isins": sorted(value for value in observed_isins if value),
        "persisted_isin": persisted_isin,
        "official_snapshot_path": str(spec["snapshot_path"]),
        "price_paths": [str(path.relative_to(REPO_ROOT).as_posix()) for path in price_paths],
        "adjusted_rows_written": adjusted_count,
        "adjusted_ohlcv_complete": completeness_ok,
        "rows": proof_rows,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
