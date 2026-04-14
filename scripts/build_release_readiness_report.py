from __future__ import annotations

import argparse
import json
from pathlib import Path

from omegadata.config import settings
from omegadata.db.session import get_session, init_db
from omegadata.track_b.release_readiness import ReleaseReadinessService

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url", default=None, help="Explicit database URL for readiness evaluation")
    args = parser.parse_args()

    if args.db_url:
        settings.db_url = str(args.db_url)
    elif settings.db_url.startswith("postgresql"):
        raise SystemExit(
            "build_release_readiness_report.py requires an explicit --db-url when the configured runtime DB is PostgreSQL. "
            "Auto-discovery is disabled for verification reproducibility."
        )

    init_db()
    service = ReleaseReadinessService()
    with get_session() as session:
        report = service.evaluate(session)
    out_path = REPO_ROOT / "artifacts/verification/release_readiness.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
