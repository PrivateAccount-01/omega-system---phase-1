from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.parse import urlparse

from omegadata.config import settings
from omegadata.db.session import init_db
from omegadata.pipelines.sequential_pipeline import OmegaDataSequentialPipeline
from omegadata.track_a.trading_calendar import TradingCalendar

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run OmegaData full pipeline across recent days.")
    parser.add_argument("--days", type=int, default=10, help="Number of recent days to attempt.")
    parser.add_argument(
        "--dates",
        nargs="*",
        default=None,
        help="Explicit ISO dates to run instead of deriving a recent window.",
    )
    parser.add_argument("--market-isin", default=settings.market_proxy_isin or None, help="Explicit market benchmark ISIN")
    parser.add_argument("--db-url", default=None, help="Optional database URL override for the run")
    parser.add_argument(
        "--reset-sqlite-db",
        action="store_true",
        help="Delete the target SQLite file before initializing the run.",
    )
    parser.add_argument(
        "--calendar-mode",
        choices=["trading", "calendar"],
        default="trading",
        help="Use recent trading days or raw calendar days when building the run window.",
    )
    args = parser.parse_args()

    if args.db_url:
        settings.db_url = str(args.db_url)

    if args.reset_sqlite_db:
        parsed = urlparse(settings.db_url)
        if parsed.scheme != "sqlite":
            raise ValueError("--reset-sqlite-db is only supported for sqlite db URLs")
        db_path = Path(parsed.path.lstrip("/"))
        if db_path.exists():
            db_path.unlink()

    init_db()
    pipe = OmegaDataSequentialPipeline()
    runs: list[dict[str, object]] = []
    errors: list[dict[str, str]] = []

    if args.dates:
        as_of_dates = [date.fromisoformat(value) for value in args.dates]
    elif args.calendar_mode == "trading":
        as_of_dates = list(
            reversed(
                TradingCalendar.from_config().recent_trading_days(
                    "NSE",
                    anchor_date=date.today(),
                    limit=args.days,
                    strict=False,
                )
            )
        )
    else:
        from datetime import timedelta

        as_of_dates = [date.today() - timedelta(days=offset) for offset in range(args.days, 0, -1)]

    for as_of in as_of_dates:
        try:
            summary = pipe.run_full_day(as_of=as_of, market_isin=args.market_isin)
            runs.append({
                "as_of": as_of.isoformat(),
                "ingest_paths": summary.ingest_paths,
                "confirmed_actions": summary.confirmed_actions,
                "adjusted_rows": summary.adjusted_rows,
                "new_discontinuities": summary.discontinuities,
                "total_discontinuity_events": summary.total_discontinuity_events,
                "validations": summary.validations,
            })
        except Exception as exc:  # noqa: BLE001
            errors.append({"as_of": as_of.isoformat(), "error": str(exc)})

    output = {
        "generated_at": datetime.now(UTC).isoformat(),
        "db_url": settings.db_url,
        "market_isin": args.market_isin,
        "runs": runs,
        "summary": {
            "calendar_mode": args.calendar_mode,
            "explicit_dates": [item.isoformat() for item in as_of_dates],
            "successful_days": len(runs),
            "failed_days": len(errors),
            "total_confirmed_actions": sum(int(r["confirmed_actions"]) for r in runs),
            "total_adjusted_rows": sum(int(r["adjusted_rows"]) for r in runs),
            "total_new_discontinuities": sum(int(r["new_discontinuities"]) for r in runs),
            "latest_total_discontinuity_events": (
                int(runs[-1]["total_discontinuity_events"]) if runs else 0
            ),
            "total_validations": sum(int(r["validations"]) for r in runs),
        },
        "errors": errors,
    }
    out_path = REPO_ROOT / "artifacts/verification/pipeline_execution_result.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        json.dump(output, handle, indent=2)
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
