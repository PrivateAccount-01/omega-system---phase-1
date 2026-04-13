from __future__ import annotations

import argparse
import json
from pathlib import Path

from omegadata.config import settings
from omegadata.db.session import get_session, init_db
from omegadata.track_b.release_readiness import ReleaseReadinessService

REPO_ROOT = Path(__file__).resolve().parents[1]


def _discover_sqlite_candidates() -> list[Path]:
    excluded_parts = {".venv", ".git", ".mypy_cache", "__pycache__", "node_modules"}
    candidates: list[Path] = []
    for pattern in ("*.db", "*.sqlite", "*.sqlite3"):
        for path in REPO_ROOT.rglob(pattern):
            if any(part in excluded_parts for part in path.parts):
                continue
            candidates.append(path)
    preferred = sorted(
        set(candidates),
        key=lambda path: (path.name != "system_test_april_local.db", str(path)),
    )
    return preferred


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url", default=None)
    args = parser.parse_args()

    if args.db_url:
        settings.db_url = str(args.db_url)
    elif settings.db_url.startswith("postgresql"):
        candidates = _discover_sqlite_candidates()
        if candidates:
            settings.db_url = f"sqlite:///{candidates[0].resolve().as_posix()}"

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
