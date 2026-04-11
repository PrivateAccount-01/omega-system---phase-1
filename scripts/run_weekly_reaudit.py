from __future__ import annotations

import argparse
import json
from datetime import date, timedelta

from omegadata.db.models import DiscontinuityEvent
from omegadata.db.session import get_session, init_db
from omegadata.pipelines.sequential_pipeline import OmegaDataSequentialPipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Run OmegaData weekly Track B re-audit")
    parser.add_argument("--days", type=int, default=35, help="Historical window to refresh")
    parser.add_argument("--market-isin", default=None, help="Explicit market benchmark ISIN")
    args = parser.parse_args()

    init_db()
    pipeline = OmegaDataSequentialPipeline()
    as_of = date.today()
    refreshed_days: list[str] = []

    for offset in range(args.days, -1, -1):
        audit_date = as_of - timedelta(days=offset)
        try:
            pipeline.run_track_b(as_of=audit_date, market_isin=args.market_isin)
            refreshed_days.append(audit_date.isoformat())
        except Exception:
            continue

    with get_session() as session:
        discontinuities = session.query(DiscontinuityEvent).count()

    payload = {
        "as_of": as_of.isoformat(),
        "refreshed_days": refreshed_days,
        "discontinuity_events_total": discontinuities,
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
