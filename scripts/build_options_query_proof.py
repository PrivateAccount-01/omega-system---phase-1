from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from omegadata.config import settings
from omegadata.db.models import OptionsContractMaster, OptionsEOD, ReleaseRecord
from omegadata.db.session import get_session, init_db
from omegadata.domain import ReleaseProfile

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an options query proof artifact from canonical DB state.")
    parser.add_argument("--db-url", default=None, help="Database URL override")
    parser.add_argument("--underlying", default="ABB", help="Underlying symbol to prove")
    parser.add_argument(
        "--artifact-path",
        default="artifacts/verification/options_query_proof.json",
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
        contract_rows = session.scalars(
            select(OptionsContractMaster)
            .where(OptionsContractMaster.underlying_symbol == args.underlying)
            .order_by(
                OptionsContractMaster.expiry_date.asc(),
                OptionsContractMaster.option_type.asc(),
                OptionsContractMaster.strike_price.asc(),
            )
        ).all()
        contract_ids = [row.id for row in contract_rows]
        eod_rows_db = session.scalars(
            select(OptionsEOD)
            .where(OptionsEOD.contract_id.in_(contract_ids))
            .order_by(OptionsEOD.trade_date.asc())
        ).all() if contract_ids else []
        contracts = [
            {
                "contract_symbol": row.contract_symbol,
                "expiry_date": row.expiry_date.isoformat(),
                "strike_price": str(row.strike_price),
                "option_type": row.option_type,
                "underlying_isin": row.underlying_isin,
            }
            for row in contract_rows
        ]
        eod_rows = [
            {
                "trade_date": row.trade_date.isoformat(),
                "contract_id": row.contract_id,
                "close_price": None if row.close_price is None else str(row.close_price),
                "open_interest": None if row.open_interest is None else str(row.open_interest),
                "volume": None if row.volume is None else str(row.volume),
            }
            for row in eod_rows_db
        ]

    proof = {
        "generated_at": datetime.now(UTC).isoformat(),
        "release_id": release_id,
        "underlying_symbol": args.underlying,
        "status": "ok" if contracts and eod_rows else "empty",
        "contract_count": len(contracts),
        "eod_row_count": len(eod_rows),
        "sample_contracts": contracts[:10],
        "sample_eod": eod_rows[:10],
    }
    out_path = REPO_ROOT / args.artifact_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(proof, indent=2), encoding="utf-8")
    print(json.dumps(proof, indent=2))


if __name__ == "__main__":
    main()
