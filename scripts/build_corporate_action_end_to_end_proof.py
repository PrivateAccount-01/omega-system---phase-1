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
from omegadata.domain import CorporateActionType, Exchange, InstrumentType, ReleaseProfile
from omegadata.track_b.adjustment_engine import PriceAdjustmentEngine
from omegadata.track_b.corporate_actions import CorporateActionService
from omegadata.track_b.release_manager import ReleaseManager

REPO_ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_PATH = REPO_ROOT / "tests/fixtures/official_source/corporate_action_matching_benchmark.json"
OUT_PATH = REPO_ROOT / "artifacts/verification/corporate_action_proof.json"


def _load_case(label: str) -> dict[str, object]:
    payload = json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))
    cases = payload.get("cases", [])
    for case in cases:
        if isinstance(case, dict) and case.get("label") == label:
            return case
    raise LookupError(f"No corporate action benchmark case named {label}")


def _extract_price_row(path: Path, *, symbol: str, isin: str) -> dict[str, object] | None:
    with zipfile.ZipFile(path) as zf:
        name = next(item for item in zf.namelist() if item.lower().endswith(".csv"))
        reader = csv.DictReader(io.TextIOWrapper(zf.open(name), encoding="utf-8"))
        for row in reader:
            found_symbol = str(row.get("SYMBOL") or row.get("TckrSymb") or "").strip().upper()
            found_isin = str(row.get("ISIN") or row.get("ISIN_NUMBER") or "").strip().upper()
            if found_symbol != symbol.upper() or found_isin != isin.upper():
                continue
            trade_date_text = str(row.get("TradDt") or row.get("DATE1") or row.get("TIMESTAMP") or "")
            trade_date = (
                date.fromisoformat(trade_date_text)
                if "-" in trade_date_text
                else datetime.strptime(trade_date_text, "%d-%b-%Y").date()
            )
            return {
                "trade_date": trade_date,
                "open_price": Decimal(str(row.get("OpnPric") or row.get("OPEN"))),
                "high_price": Decimal(str(row.get("HghPric") or row.get("HIGH"))),
                "low_price": Decimal(str(row.get("LwPric") or row.get("LOW"))),
                "close_price": Decimal(str(row.get("ClsPric") or row.get("CLOSE"))),
                "volume": Decimal(str(row.get("TtlTradgVol") or row.get("TOTTRDQTY"))),
                "raw_source": "nse_bhavcopy",
                "source_path": path.relative_to(REPO_ROOT).as_posix(),
            }
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a real official-source corporate-action end-to-end proof.")
    parser.add_argument("--case-label", default="CIEINDIA_DIVIDEND_MATCH")
    parser.add_argument("--db-url", default="sqlite:///artifacts/verification/corporate_action_proof.sqlite")
    parser.add_argument("--as-of", default="2026-04-13")
    args = parser.parse_args()

    from omegadata.config import settings

    settings.db_url = args.db_url
    proof_db = REPO_ROOT / args.db_url.removeprefix("sqlite:///")
    if proof_db.exists():
        proof_db.unlink()
    init_db()

    case = _load_case(args.case_label)
    nse_payload = dict(case["nse"])
    bse_payload = dict(case["bse"])
    isin = str(nse_payload["isin"])
    symbol = str(dict(nse_payload.get("payload", {})).get("symbol") or "")
    as_of = date.fromisoformat(args.as_of)

    price_paths = [
        REPO_ROOT / "data/raw/nse_equity_bhavcopy/year=2026/month=04/20260410__85e27e7c9338.zip",
        REPO_ROOT / "data/raw/nse_equity_bhavcopy/year=2026/month=04/20260413__23a7d04ecaac.zip",
    ]
    price_rows = [
        row
        for path in price_paths
        for row in [_extract_price_row(path, symbol=symbol, isin=isin)]
        if row is not None
    ]
    if not price_rows:
        raise RuntimeError(f"No real price rows found for {symbol}/{isin}")

    service = CorporateActionService()
    with get_session() as session:
        earliest_trade_date = min(row["trade_date"] for row in price_rows)
        session.add(
            InstrumentMaster(
                isin=isin,
                instrument_type=InstrumentType.EQUITY,
                primary_exchange=Exchange.NSE,
                company_name=symbol,
                listed_date=earliest_trade_date,
                active=True,
            )
        )
        session.add(
            SymbolMap(
                isin=isin,
                exchange=Exchange.NSE,
                symbol=symbol,
                valid_from=earliest_trade_date,
                valid_to=None,
            )
        )
        session.add(
            SymbolMap(
                isin=isin,
                exchange=Exchange.BSE,
                symbol=symbol,
                valid_from=earliest_trade_date,
                valid_to=None,
            )
        )

        for row in price_rows:
            session.add(
                PriceRecord(
                    isin=isin,
                    exchange=Exchange.NSE,
                    trade_date=row["trade_date"],  # type: ignore[index]
                    open_price=row["open_price"],  # type: ignore[index]
                    high_price=row["high_price"],  # type: ignore[index]
                    low_price=row["low_price"],  # type: ignore[index]
                    close_price=row["close_price"],  # type: ignore[index]
                    volume=row["volume"],  # type: ignore[index]
                    raw_source=row["raw_source"],  # type: ignore[index]
                    confidence_score=Decimal("1.00"),
                )
            )

        nse_staging = service.add_staging_record(
            session,
            source=Exchange.NSE,
            isin=isin,
            action_type=CorporateActionType(str(nse_payload["action_type"])),
            announcement_date=None if nse_payload["announcement_date"] is None else date.fromisoformat(str(nse_payload["announcement_date"])),
            ex_date=None if nse_payload["ex_date"] is None else date.fromisoformat(str(nse_payload["ex_date"])),
            record_date=None if nse_payload["record_date"] is None else date.fromisoformat(str(nse_payload["record_date"])),
            payload={
                "isin": isin,
                "ex_date": str(nse_payload["ex_date"]),
                "announcement_date": str(nse_payload["announcement_date"]),
                **dict(nse_payload.get("payload", {})),
            },
        )
        bse_staging = service.add_staging_record(
            session,
            source=Exchange.BSE,
            isin=isin,
            action_type=CorporateActionType(str(bse_payload["action_type"])),
            announcement_date=None if bse_payload["announcement_date"] is None else date.fromisoformat(str(bse_payload["announcement_date"])),
            ex_date=None if bse_payload["ex_date"] is None else date.fromisoformat(str(bse_payload["ex_date"])),
            record_date=None if bse_payload["record_date"] is None else date.fromisoformat(str(bse_payload["record_date"])),
            payload={
                "isin": isin,
                "ex_date": str(bse_payload["ex_date"]),
                "announcement_date": str(bse_payload["announcement_date"]),
                **dict(bse_payload.get("payload", {})),
            },
        )
        session.flush()
        confirmations = service.run_daily_confirmation(session, as_of=as_of)
        confirmed = session.scalar(select(ConfirmedCorporateAction).where(ConfirmedCorporateAction.isin == isin))
        if confirmed is None:
            raise RuntimeError("Expected a confirmed corporate action but none was created")

        adjusted_rows = PriceAdjustmentEngine().recompute_adjusted_series(session, isin=isin, exchange=Exchange.NSE)
        release = ReleaseManager().build_release(session, as_of=as_of, profile=ReleaseProfile.EQUITY_CORE)

        published_rows = session.scalars(
            select(PriceRecord)
            .where(PriceRecord.isin == isin)
            .where(PriceRecord.exchange == Exchange.NSE)
            .order_by(PriceRecord.trade_date.asc())
        ).all()

        artifact = {
            "generated_at": datetime.now(UTC).isoformat(),
            "case_label": args.case_label,
            "official_snapshot_paths": dict(case.get("snapshot_paths", {})),
            "staged_records": [
                {
                    "id": nse_staging.id,
                    "source": nse_staging.source.value,
                    "isin": nse_staging.isin,
                    "action_type": nse_staging.action_type.value,
                    "ex_date": None if nse_staging.ex_date is None else nse_staging.ex_date.isoformat(),
                    "matched": nse_staging.matched,
                },
                {
                    "id": bse_staging.id,
                    "source": bse_staging.source.value,
                    "isin": bse_staging.isin,
                    "action_type": bse_staging.action_type.value,
                    "ex_date": None if bse_staging.ex_date is None else bse_staging.ex_date.isoformat(),
                "matched": bse_staging.matched,
                },
            ],
            "expected_outcome": str(case.get("expected")),
            "confirmation_results": [
                {"confirmed_id": item.confirmed_id, "confidence": item.confidence.value}
                for item in confirmations
            ],
            "confirmed_action": {
                "id": confirmed.id,
                "isin": confirmed.isin,
                "action_type": confirmed.action_type.value,
                "confidence": confirmed.confidence.value,
                "announcement_date": None if confirmed.announcement_date is None else confirmed.announcement_date.isoformat(),
                "ex_date": None if confirmed.ex_date is None else confirmed.ex_date.isoformat(),
                "record_date": None if confirmed.record_date is None else confirmed.record_date.isoformat(),
                "parameters": confirmed.parameters,
                "source_preference": confirmed.source_preference.value,
            },
            "adjusted_rows_written": adjusted_rows,
            "price_rows": [
                {
                    "trade_date": row.trade_date.isoformat(),
                    "raw_close": str(row.close_price),
                    "adjusted_close": None if row.adjusted_close_price is None else str(row.adjusted_close_price),
                    "adjusted_open": None if row.adjusted_open_price is None else str(row.adjusted_open_price),
                    "adjusted_high": None if row.adjusted_high_price is None else str(row.adjusted_high_price),
                    "adjusted_low": None if row.adjusted_low_price is None else str(row.adjusted_low_price),
                    "adjusted_volume": None if row.adjusted_volume is None else str(row.adjusted_volume),
                }
                for row in published_rows
            ],
            "source_price_paths": [row["source_path"] for row in price_rows],
            "release": {
                "release_id": release.release_id,
                "profile": release.profile.value,
                "manifest_path": release.manifest_path.relative_to(REPO_ROOT).as_posix(),
                "signature_path": None if release.signature_path is None else release.signature_path.relative_to(REPO_ROOT).as_posix(),
                "quality_report_path": release.quality_report_path.relative_to(REPO_ROOT).as_posix(),
                "lineage_report_path": release.lineage_report_path.relative_to(REPO_ROOT).as_posix(),
                "warehouse_sync_status": release.warehouse_sync_status,
            },
        }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
