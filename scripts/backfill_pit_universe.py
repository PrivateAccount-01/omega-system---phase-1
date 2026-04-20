from __future__ import annotations

import argparse
import json
from pathlib import Path

from omegadata.config import settings
from omegadata.db.session import get_session, init_db
from omegadata.track_b.universe_manager import PointInTimeUniverseManager

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SEED_PACK_PATH = PROJECT_ROOT / "data" / "reference" / "official" / "pit_universe_reference_pack.json"
ARTIFACT_PATH = PROJECT_ROOT / "artifacts" / "verification" / "pit_universe_backfill_report.json"


def _relative_repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except Exception:  # noqa: BLE001
        return path.as_posix().replace("\\", "/")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill point-in-time universe memberships from an official seed pack")
    parser.add_argument("--db-url", help="Database URL override for this run")
    parser.add_argument("--seed-pack", type=Path, default=SEED_PACK_PATH, help="Seed pack JSON path")
    parser.add_argument("--raw-root", type=Path, default=PROJECT_ROOT / "data" / "raw", help="Raw data root")
    parser.add_argument(
        "--artifact-path",
        type=Path,
        default=ARTIFACT_PATH,
        help="Output path for the validation artifact JSON",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.db_url:
        settings.db_url = args.db_url
    init_db()
    manager = PointInTimeUniverseManager()
    seed_pack = json.loads(args.seed_pack.read_text(encoding="utf-8"))

    with get_session() as session:
        loaded = manager.backfill_from_seed_pack(
            session,
            seed_pack,
            raw_root=args.raw_root,
        )
        validation = manager.validate_seed_pack(
            session,
            seed_pack,
            raw_root=args.raw_root,
        )

    report = {
        "seed_pack": _relative_repo_path(args.seed_pack),
        "db_url": settings.db_url,
        "official_backed": "reference/official" in args.seed_pack.as_posix() or "official_source" in args.seed_pack.as_posix(),
        "loaded_rows": loaded,
        "snapshot_validations": [
            {
                "index_name": item.index_name,
                "as_of_date": item.as_of_date.isoformat(),
                "matched": item.matched,
                "expected_count": len(item.expected_isins),
                "actual_count": len(item.actual_isins),
                "source": item.source,
            }
            for item in validation
        ],
        "matched_validation_count": sum(1 for item in validation if item.matched),
    }
    args.artifact_path.parent.mkdir(parents=True, exist_ok=True)
    args.artifact_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
