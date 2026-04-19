from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from omegadata.config import settings
from omegadata.db.session import get_session, init_db
from omegadata.domain import ReleaseProfile
from omegadata.track_b.release_manager import ReleaseManager, _relative_repo_path

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a signed OmegaData release bundle.")
    parser.add_argument("--as-of", required=True, help="Release as-of date in YYYY-MM-DD")
    parser.add_argument("--db-url", default=None, help="Explicit database URL override")
    parser.add_argument(
        "--profile",
        choices=[profile.value for profile in ReleaseProfile],
        default=settings.release_default_profile,
        help="Release profile to build",
    )
    args = parser.parse_args()

    if args.db_url:
        settings.db_url = str(args.db_url)
    init_db()
    manager = ReleaseManager()
    as_of = date.fromisoformat(args.as_of)
    profile = ReleaseProfile(args.profile)
    with get_session() as session:
        result = manager.build_release(session, as_of=as_of, profile=profile)

    payload = {
        "release_id": result.release_id,
        "profile": result.profile.value,
        "manifest_path": _relative_repo_path(result.manifest_path),
        "signature_path": None if result.signature_path is None else _relative_repo_path(result.signature_path),
        "quality_report_path": _relative_repo_path(result.quality_report_path),
        "lineage_report_path": _relative_repo_path(result.lineage_report_path),
        "warehouse_sync_status": result.warehouse_sync_status,
    }
    out_path = REPO_ROOT / "artifacts/verification" / f"release_build_{profile.value}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
