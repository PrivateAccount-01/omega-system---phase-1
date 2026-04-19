from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from omegadata.config import settings
from omegadata.db.models import ContinuousFutureDaily, ReleaseRecord
from omegadata.db.session import get_session, init_db
from omegadata.domain import ReleaseProfile

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a futures continuation proof artifact from canonical DB state.")
    parser.add_argument("--db-url", default=None, help="Database URL override")
    parser.add_argument(
        "--artifact-path",
        default="artifacts/verification/futures_continuation_proof.json",
        help="Output artifact path",
    )
    args = parser.parse_args()

    if args.db_url:
        settings.db_url = str(args.db_url)
    init_db()

    with get_session() as session:
        release_record = session.scalar(
            select(ReleaseRecord)
            .where(ReleaseRecord.release_profile == ReleaseProfile.FULL_DERIVATIVES)
            .order_by(ReleaseRecord.generated_at.desc())
        )
        release_id = None if release_record is None else release_record.release_id
        db_rows = session.scalars(
            select(ContinuousFutureDaily)
            .order_by(
                ContinuousFutureDaily.underlying_symbol.asc(),
                ContinuousFutureDaily.trade_date.asc(),
            )
        ).all()
        rows = [
            {
                "trade_date": row.trade_date.isoformat(),
                "underlying_symbol": row.underlying_symbol,
                "underlying_isin": row.underlying_isin,
                "roll_rule": row.roll_rule,
                "contract_symbol": row.contract_symbol,
                "expiry_date": row.expiry_date.isoformat(),
                "close_price": None if row.close_price is None else str(row.close_price),
            }
            for row in db_rows
        ]

    proof = {
        "generated_at": datetime.now(UTC).isoformat(),
        "release_id": release_id,
        "status": "ok" if rows else "empty",
        "row_count": len(rows),
        "sample": rows[:10],
    }
    out_path = REPO_ROOT / args.artifact_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(proof, indent=2), encoding="utf-8")
    print(json.dumps(proof, indent=2))


if __name__ == "__main__":
    main()
