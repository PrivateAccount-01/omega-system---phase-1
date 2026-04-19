from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import select

from omegadata.db.models import MarketIndexDaily, ParticipantFlowDaily
from omegadata.db.session import get_session, init_db
from omegadata.domain import ReleaseProfile
from omegadata.pipelines.sequential_pipeline import OmegaDataSequentialPipeline
from omegadata.track_b.release_manager import ReleaseManager

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = REPO_ROOT / "artifacts/verification/sidefeed_proof.json"


def _repo_relative(path: str | Path | None) -> str | None:
    if path is None:
        return None
    candidate = Path(path)
    try:
        return candidate.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except Exception:
        raw = str(path).replace("\\", "/")
        marker = "data/raw/"
        if marker in raw:
            return raw[raw.index(marker) :]
        return raw


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a real FII/DII and India VIX parse-to-table proof artifact.")
    parser.add_argument("--db-url", default="sqlite:///artifacts/verification/sidefeed_proof.sqlite")
    parser.add_argument("--as-of", default="2026-04-13")
    args = parser.parse_args()

    from omegadata.config import settings

    settings.db_url = args.db_url
    proof_db = REPO_ROOT / args.db_url.removeprefix("sqlite:///")
    if proof_db.exists():
        proof_db.unlink()
    init_db()

    pipeline = OmegaDataSequentialPipeline()
    fii_paths = [
        REPO_ROOT / "data/raw/nse_fii_dii/year=2026/month=04/20260410__eea1384a7f94.bin",
        REPO_ROOT / "data/raw/nse_fii_dii/year=2026/month=04/20260413__eea1384a7f94.bin",
    ]
    index_paths = [
        REPO_ROOT / "data/raw/india_vix/year=2026/month=04/20260410__cb8ef906a7d7.bin",
        REPO_ROOT / "data/raw/india_vix/year=2026/month=04/20260413__cb8ef906a7d7.bin",
    ]

    with get_session() as session:
        fii_loaded = 0
        for path in fii_paths:
            fii_loaded += pipeline._load_fii_dii(session, path)
            session.flush()

        index_loaded = 0
        for path in index_paths:
            trade_date = date.fromisoformat(path.name.split("__", 1)[0])
            index_loaded += pipeline._load_market_indices(session, path, trade_date)
            session.flush()

        release = ReleaseManager().build_release(
            session,
            as_of=date.fromisoformat(args.as_of),
            profile=ReleaseProfile.EQUITY_PLUS_SIDEFEEDS,
        )

        flows = session.scalars(
            select(ParticipantFlowDaily).order_by(ParticipantFlowDaily.trade_date.asc(), ParticipantFlowDaily.participant_category.asc())
        ).all()
        indices = session.scalars(
            select(MarketIndexDaily).order_by(MarketIndexDaily.trade_date.asc(), MarketIndexDaily.index_symbol.asc())
        ).all()

        artifact = {
            "generated_at": datetime.now(UTC).isoformat(),
            "source_payloads": {
                "nse_fii_dii": [path.relative_to(REPO_ROOT).as_posix() for path in fii_paths],
                "india_vix": [path.relative_to(REPO_ROOT).as_posix() for path in index_paths],
            },
            "observed_trade_dates": {
                "participant_flow_daily": sorted({row.trade_date.isoformat() for row in flows}),
                "market_index_daily": sorted({row.trade_date.isoformat() for row in indices}),
            },
            "rows_loaded": {
                "participant_flow_daily": fii_loaded,
                "market_index_daily": index_loaded,
                "participant_flow_total": len(flows),
                "market_index_total": len(indices),
            },
            "participant_flow_sample": [
                {
                    "trade_date": row.trade_date.isoformat(),
                    "participant_category": row.participant_category,
                    "buy_value": str(row.buy_value),
                    "sell_value": str(row.sell_value),
                    "net_value": str(row.net_value),
                    "source_artifact_path": _repo_relative(row.source_artifact_path),
                }
                for row in flows[:5]
            ],
            "market_index_sample": [
                {
                    "trade_date": row.trade_date.isoformat(),
                    "index_symbol": row.index_symbol,
                    "index_kind": row.index_kind,
                    "close_price": str(row.close_price),
                    "source_artifact_path": _repo_relative(row.source_artifact_path),
                }
                for row in indices[:8]
            ],
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
