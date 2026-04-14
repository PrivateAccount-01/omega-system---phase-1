from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session

from omegadata.config import settings
from omegadata.db.models import DiscontinuityEvent, ManualReviewQueue, PriceRecord
from omegadata.db.session import get_session, init_db
from omegadata.domain import Exchange
from omegadata.pipelines.sequential_pipeline import OmegaDataSequentialPipeline

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DB = REPO_ROOT / "system_test_april_local.db"
DEFAULT_WORK_DB = REPO_ROOT / "artifacts/verification/discontinuity_spike_reaudit.sqlite"
OUTPUT_PATH = REPO_ROOT / "artifacts/verification/discontinuity_spike_report.json"


def _source_event_summary(source_db: Path) -> dict[str, object]:
    engine = create_engine(f"sqlite:///{source_db.as_posix()}", future=True)
    with Session(engine) as session:
        existing_rows = session.scalars(
            select(DiscontinuityEvent).order_by(DiscontinuityEvent.event_date.asc(), DiscontinuityEvent.isin.asc())
        ).all()

    by_date = Counter(row.event_date.isoformat() for row in existing_rows)
    unique_keys = {(row.isin, row.event_date.isoformat(), row.category.value) for row in existing_rows}
    return {
        "existing_total_event_count": len(existing_rows),
        "existing_unique_event_count": len(unique_keys),
        "existing_duplicate_event_count": len(existing_rows) - len(unique_keys),
        "existing_counts_by_date": [
            {"event_date": event_date, "count": count}
            for event_date, count in sorted(by_date.items())
        ],
    }


def _discover_market_proxy() -> str:
    candidates = (
        "INF204KB14I2",  # NIFTYBEES
        "INF732E01045",  # JUNIORBEES
    )
    with get_session() as session:
        present = {
            row[0]
            for row in session.execute(
                select(PriceRecord.isin).where(PriceRecord.exchange == Exchange.NSE).distinct()
            ).all()
        }
    for isin in candidates:
        if isin in present:
            return isin
    raise LookupError("Unable to auto-discover a market ETF proxy in the working database")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-db", default=str(DEFAULT_SOURCE_DB))
    parser.add_argument("--market-isin", default=None)
    args = parser.parse_args()

    source_db = Path(args.source_db).resolve()
    source_summary = _source_event_summary(source_db)
    work_db = DEFAULT_WORK_DB
    work_db.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_db, work_db)

    settings.db_url = f"sqlite:///{work_db.as_posix()}"
    init_db()

    with get_session() as session:
        session.execute(delete(DiscontinuityEvent))
        session.execute(
            delete(ManualReviewQueue).where(ManualReviewQueue.category == "DISCONTINUITY_REVIEW")
        )

    market_isin = args.market_isin or _discover_market_proxy()
    pipe = OmegaDataSequentialPipeline()
    with get_session() as session:
        new_events = pipe.discontinuity_detector.detect(
            session,
            market_isin=market_isin,
            exchange=Exchange.NSE,
        )
        session.flush()
        persisted_rows = session.scalars(
            select(DiscontinuityEvent).order_by(DiscontinuityEvent.event_date.asc(), DiscontinuityEvent.isin.asc())
        ).all()
        persisted = [
            {
                "isin": event.isin,
                "event_date": event.event_date.isoformat(),
                "category": event.category.value,
                "overnight_return": float(Decimal(str(event.overnight_return))),
                "market_return": float(Decimal(str(event.market_return))),
                "beta_used": float(Decimal(str(event.beta_used))),
                "idiosyncratic_return": float(Decimal(str(event.idiosyncratic_return))),
            }
            for event in persisted_rows
        ]

    by_date = Counter(event["event_date"] for event in persisted)
    by_date_category = Counter((event["event_date"], event["category"]) for event in persisted)
    top_spike_date = max(by_date, key=by_date.get) if by_date else None
    top_spike_events: list[dict[str, object]] = []
    top_spike_market_return: float | None = None
    top_spike_average_abs_idio: float | None = None
    if top_spike_date is not None:
        for event in persisted:
            if event["event_date"] != top_spike_date:
                continue
            top_spike_events.append(event)
        if top_spike_events:
            top_spike_market_return = float(top_spike_events[0]["market_return"])
            top_spike_average_abs_idio = sum(abs(float(item["idiosyncratic_return"])) for item in top_spike_events) / len(
                top_spike_events
            )
        top_spike_events.sort(key=lambda item: abs(float(item["idiosyncratic_return"])), reverse=True)
        top_spike_events = top_spike_events[:20]

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_db": source_db.name,
        "work_db": work_db.relative_to(REPO_ROOT).as_posix(),
        "market_proxy_isin": market_isin,
        "source_summary": source_summary,
        "new_events_detected": len(new_events),
        "persisted_event_count": len(persisted),
        "counts_by_date": [
            {"event_date": event_date, "count": count}
            for event_date, count in sorted(by_date.items())
        ],
        "counts_by_date_category": [
            {"event_date": event_date, "category": category, "count": count}
            for (event_date, category), count in sorted(by_date_category.items())
        ],
        "top_spike_date": top_spike_date,
        "top_spike_market_return": top_spike_market_return,
        "top_spike_average_abs_idiosyncratic_return": top_spike_average_abs_idio,
        "analysis": {
            "duplicate_persistence_detected_in_source": bool(source_summary["existing_duplicate_event_count"]),
            "top_spike_has_extreme_market_move": bool(
                top_spike_market_return is not None and abs(top_spike_market_return) >= 0.05
            ),
            "note": (
                "The re-audit clears existing discontinuity rows and recomputes from price history using an explicit market proxy. "
                "If the source DB shows duplicates but the re-audit does not, the historical spike was partly persistence inflation."
            ),
        },
        "top_spike_events": top_spike_events,
    }

    OUTPUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
