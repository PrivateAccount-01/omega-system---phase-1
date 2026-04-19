from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import select

from omegadata.config import settings
from omegadata.db.models import ConfirmedCorporateAction, CorporateActionStaging
from omegadata.db.session import get_session, init_db
from omegadata.domain import CorporateActionType, Exchange, ReleaseProfile
from omegadata.track_b.adjustment_engine import PriceAdjustmentEngine
from omegadata.track_b.corporate_actions import CorporateActionService
from omegadata.track_b.release_manager import ReleaseManager, _relative_repo_path

REPO_ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_PATH = REPO_ROOT / "tests/fixtures/official_source/corporate_action_matching_benchmark.json"
OUTPUT_PATH = REPO_ROOT / "artifacts/verification/pipeline_corporate_action_confirmation.json"


def _load_match_cases() -> list[dict[str, object]]:
    payload = json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))
    cases = payload.get("cases", [])
    return [
        dict(case)
        for case in cases
        if isinstance(case, dict) and str(case.get("expected")) == "match"
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay official matched corporate-action pairs into the canonical pipeline DB.")
    parser.add_argument("--db-url", required=True)
    parser.add_argument("--as-of", default="2026-04-13")
    parser.add_argument("--artifact-path", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()

    settings.db_url = args.db_url
    init_db()
    service = CorporateActionService()
    seeded_cases: list[str] = []
    seeded_rows = 0
    adjusted_rows = 0
    as_of = date.fromisoformat(args.as_of)

    with get_session() as session:
        for case in _load_match_cases():
            nse_payload = dict(case["nse"])
            bse_payload = dict(case["bse"])
            isin = str(nse_payload["isin"])
            action_type = CorporateActionType(str(nse_payload["action_type"]))
            ex_date = None if nse_payload["ex_date"] is None else date.fromisoformat(str(nse_payload["ex_date"]))

            existing_nse = session.scalar(
                select(CorporateActionStaging)
                .where(CorporateActionStaging.source == Exchange.NSE)
                .where(CorporateActionStaging.isin == isin)
                .where(CorporateActionStaging.action_type == action_type)
                .where(CorporateActionStaging.ex_date == ex_date)
            )
            if existing_nse is None:
                continue

            existing_bse = session.scalar(
                select(CorporateActionStaging)
                .where(CorporateActionStaging.source == Exchange.BSE)
                .where(CorporateActionStaging.isin == isin)
                .where(CorporateActionStaging.action_type == action_type)
                .where(CorporateActionStaging.ex_date == ex_date)
            )
            if existing_bse is None:
                service.add_staging_record(
                    session,
                    source=Exchange.BSE,
                    isin=isin,
                    action_type=action_type,
                    announcement_date=None
                    if bse_payload["announcement_date"] is None
                    else date.fromisoformat(str(bse_payload["announcement_date"])),
                    ex_date=ex_date,
                    record_date=None
                    if bse_payload["record_date"] is None
                    else date.fromisoformat(str(bse_payload["record_date"])),
                    payload={
                        "isin": isin,
                        "ex_date": str(bse_payload["ex_date"]),
                        "announcement_date": str(bse_payload["announcement_date"]),
                        **dict(bse_payload.get("payload", {})),
                    },
                )
                seeded_rows += 1
                seeded_cases.append(str(case["label"]))

        session.flush()
        confirmations = service.run_daily_confirmation(session, as_of=as_of)
        confirmed = session.scalars(select(ConfirmedCorporateAction)).all()
        affected_isins = sorted({row.isin for row in confirmed})
        for isin in affected_isins:
            adjusted_rows += PriceAdjustmentEngine().recompute_adjusted_series(
                session,
                isin=isin,
                exchange=Exchange.NSE,
            )
        release = ReleaseManager().build_release(
            session,
            as_of=as_of,
            profile=ReleaseProfile.EQUITY_CORE,
        )

    artifact = {
        "generated_at": datetime.now(UTC).isoformat(),
        "db_url": args.db_url,
        "seeded_rows": seeded_rows,
        "seeded_cases": seeded_cases,
        "confirmations_created": len(confirmations),
        "confirmed_total": len(confirmed),
        "confirmed_isins": affected_isins,
        "adjusted_rows_recomputed": adjusted_rows,
        "release": {
            "release_id": release.release_id,
            "profile": release.profile.value,
            "manifest_path": _relative_repo_path(release.manifest_path),
            "signature_path": None
            if release.signature_path is None
            else _relative_repo_path(release.signature_path),
            "quality_report_path": _relative_repo_path(release.quality_report_path),
            "lineage_report_path": _relative_repo_path(release.lineage_report_path),
            "warehouse_sync_status": release.warehouse_sync_status,
        },
    }
    args.artifact_path.parent.mkdir(parents=True, exist_ok=True)
    args.artifact_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(json.dumps(artifact, indent=2))


if __name__ == "__main__":
    main()
