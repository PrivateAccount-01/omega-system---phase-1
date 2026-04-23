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


def _release_profile_value(release: object) -> str:
    profile = getattr(release, "profile", None)
    if profile is not None:
        return profile.value
    release_profile = release.release_profile  # type: ignore[attr-defined]
    return release_profile.value


def _release_path(value: object) -> Path:
    return value if isinstance(value, Path) else Path(str(value))


def _latest_release_payload(profile: str) -> dict[str, object] | None:
    latest_path = PROJECT_ROOT / "artifacts" / "releases" / f"latest_{profile}.json"
    if not latest_path.exists():
        return None
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    manifest_path = PROJECT_ROOT / str(latest["manifest_path"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    signature_rel = str(latest["manifest_path"]) + ".asc"
    return {
        "release_id": str(manifest["release_id"]),
        "profile": profile,
        "manifest_path": str(latest["manifest_path"]),
        "signature_path": signature_rel if (PROJECT_ROOT / signature_rel).exists() else None,
        "quality_report_path": str(manifest.get("quality_report_path") or ""),
        "lineage_report_path": str(manifest.get("lineage_report_path") or ""),
        "warehouse_sync_status": str(manifest.get("warehouse_sync_status") or "UNKNOWN"),
    }

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SEED_PACK = PROJECT_ROOT / "data" / "reference" / "official" / "pit_universe_reference_pack.json"
OUTPUT_PATH = PROJECT_ROOT / "artifacts" / "verification" / "pit_universe_proof.json"


def _load_pack(path: Path) -> dict[str, object]:
    return dict(json.loads(path.read_text(encoding="utf-8")))


def main() -> None:
    parser = argparse.ArgumentParser(description="Build official-backed PIT universe verification proof.")
    parser.add_argument("--db-url", required=True)
    parser.add_argument("--seed-pack", type=Path, default=DEFAULT_SEED_PACK)
    parser.add_argument("--raw-root", type=Path, default=PROJECT_ROOT / "data" / "raw")
    parser.add_argument("--release-as-of", default="2026-04-13")
    parser.add_argument(
        "--reuse-latest-release",
        action="store_true",
        help="Reuse the latest existing equity_core release instead of forcing a rebuild.",
    )
    parser.add_argument("--artifact-path", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()

    settings.db_url = args.db_url
    init_db()
    manager = PointInTimeUniverseManager()
    pack = _load_pack(args.seed_pack)
    snapshots = [item for item in pack.get("snapshots", []) if isinstance(item, dict)]
    security_master = [item for item in pack.get("security_master", []) if isinstance(item, dict)]
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
        release_manager = ReleaseManager()
        if args.reuse_latest_release:
            release_payload = _latest_release_payload("equity_core")
            if release_payload is None:
                raise RuntimeError("No latest equity_core release exists to reuse")
        else:
            release_result = release_manager.build_release(
                session,
                as_of=date.fromisoformat(args.release_as_of),
                profile=ReleaseProfile.EQUITY_CORE,
            )
            release_payload = {
                "release_id": release_result.release_id,
                "profile": _release_profile_value(release_result),
                "manifest_path": _relative_repo_path(_release_path(release_result.manifest_path)),
                "signature_path": None
                if release_result.signature_path is None
                else _relative_repo_path(_release_path(release_result.signature_path)),
                "quality_report_path": _relative_repo_path(_release_path(release_result.quality_report_path)),
                "lineage_report_path": _relative_repo_path(_release_path(release_result.lineage_report_path)),
                "warehouse_sync_status": release_result.warehouse_sync_status,
            }

    artifact = {
        "generated_at": datetime.now(UTC).isoformat(),
        "seed_pack": _relative_repo_path(args.seed_pack),
        "official_backed": "reference/official" in args.seed_pack.as_posix() or "official_source" in args.seed_pack.as_posix(),
        "snapshot_count": len(snapshots),
        "security_master_count": len(security_master),
        "expected_membership_rows_across_snapshots": sum(len(item.expected_isins) for item in validation),
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
        "release": release_payload,
    }
    args.artifact_path.parent.mkdir(parents=True, exist_ok=True)
    args.artifact_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(json.dumps(artifact, indent=2))


if __name__ == "__main__":
    main()
