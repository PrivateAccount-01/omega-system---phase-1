from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import select

from omegadata.config import settings
from omegadata.db.models import UniverseMembership
from omegadata.db.session import get_session, init_db
from omegadata.domain import ReleaseProfile
from omegadata.track_b.release_manager import ReleaseManager, _relative_repo_path
from omegadata.track_b.universe_manager import PointInTimeUniverseManager

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SEED_PACK = PROJECT_ROOT / "tests" / "fixtures" / "official_source" / "pit_universe_reference_pack.json"
OUTPUT_PATH = PROJECT_ROOT / "artifacts" / "verification" / "pit_universe_proof.json"


def _load_pack(path: Path) -> dict[str, object]:
    return dict(json.loads(path.read_text(encoding="utf-8")))


def main() -> None:
    parser = argparse.ArgumentParser(description="Build official-backed PIT universe verification proof.")
    parser.add_argument("--db-url", required=True)
    parser.add_argument("--seed-pack", type=Path, default=DEFAULT_SEED_PACK)
    parser.add_argument("--raw-root", type=Path, default=PROJECT_ROOT / "data" / "raw")
    parser.add_argument("--release-as-of", default="2026-04-13")
    parser.add_argument("--artifact-path", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()

    settings.db_url = args.db_url
    init_db()
    manager = PointInTimeUniverseManager()
    pack = _load_pack(args.seed_pack)
    snapshots = [item for item in pack.get("snapshots", []) if isinstance(item, dict)]
    latest_snapshot_date = max(date.fromisoformat(str(item["effective_date"])) for item in snapshots)
    previous_snapshot_date = sorted(
        {date.fromisoformat(str(item["effective_date"])) for item in snapshots}
    )[-2]

    with get_session() as session:
        loaded = manager.backfill_from_seed_pack(session, pack, raw_root=args.raw_root)
        validation = manager.validate_seed_pack(session, pack, raw_root=args.raw_root)
        latest_snapshot = manager.get_universe(session, "NIFTY50", latest_snapshot_date)
        previous_snapshot = manager.get_universe(session, "NIFTY50", previous_snapshot_date)
        latest_isins = {item.isin for item in latest_snapshot}
        previous_isins = {item.isin for item in previous_snapshot}
        persisted_rows = len(session.scalars(select(UniverseMembership)).all())
        release_result = ReleaseManager().build_release(
            session,
            as_of=date.fromisoformat(args.release_as_of),
            profile=ReleaseProfile.EQUITY_CORE,
        )

    artifact = {
        "generated_at": datetime.now(UTC).isoformat(),
        "seed_pack": _relative_repo_path(args.seed_pack),
        "official_backed": "official_source" in args.seed_pack.as_posix(),
        "db_url": args.db_url,
        "loaded_rows": loaded,
        "persisted_membership_rows": int(persisted_rows or 0),
        "validation_count": len(validation),
        "matched_validation_count": sum(1 for item in validation if item.matched),
        "latest_snapshot_date": latest_snapshot_date.isoformat(),
        "latest_snapshot_count": len(latest_snapshot),
        "previous_snapshot_date": previous_snapshot_date.isoformat(),
        "snapshot_diff": {
            "added_isins": sorted(latest_isins - previous_isins),
            "removed_isins": sorted(previous_isins - latest_isins),
        },
        "release": {
            "release_id": release_result.release_id,
            "profile": release_result.profile.value,
            "manifest_path": _relative_repo_path(release_result.manifest_path),
            "signature_path": None
            if release_result.signature_path is None
            else _relative_repo_path(release_result.signature_path),
            "quality_report_path": _relative_repo_path(release_result.quality_report_path),
            "lineage_report_path": _relative_repo_path(release_result.lineage_report_path),
            "warehouse_sync_status": release_result.warehouse_sync_status,
        },
    }
    args.artifact_path.parent.mkdir(parents=True, exist_ok=True)
    args.artifact_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(json.dumps(artifact, indent=2))


if __name__ == "__main__":
    main()
