from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path

from omegadata.config import settings
from omegadata.db.session import init_db
from omegadata.pipelines.sequential_pipeline import OmegaDataSequentialPipeline

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run OmegaData full pipeline across recent days.")
    parser.add_argument("--days", type=int, default=10, help="Number of recent days to attempt.")
    parser.add_argument("--market-isin", default=settings.market_proxy_isin or None, help="Explicit market benchmark ISIN")
    args = parser.parse_args()

    init_db()
    pipe = OmegaDataSequentialPipeline()
    runs: list[dict[str, object]] = []
    errors: list[dict[str, str]] = []

    for offset in range(args.days, 0, -1):
        as_of = date.today() - timedelta(days=offset)
        try:
            summary = pipe.run_full_day(as_of=as_of, market_isin=args.market_isin)
            runs.append({
                "as_of": as_of.isoformat(),
                "ingest_paths": summary.ingest_paths,
                "confirmed_actions": summary.confirmed_actions,
                "adjusted_rows": summary.adjusted_rows,
                "discontinuities": summary.discontinuities,
                "validations": summary.validations,
            })
        except Exception as exc:  # noqa: BLE001
            errors.append({"as_of": as_of.isoformat(), "error": str(exc)})

    output = {
        "runs": runs,
        "summary": {
            "successful_days": len(runs),
            "failed_days": len(errors),
            "total_confirmed_actions": sum(int(r["confirmed_actions"]) for r in runs),
            "total_adjusted_rows": sum(int(r["adjusted_rows"]) for r in runs),
            "total_discontinuities": sum(int(r["discontinuities"]) for r in runs),
            "total_validations": sum(int(r["validations"]) for r in runs),
        },
        "errors": errors,
    }
    out_path = REPO_ROOT / "artifacts/verification/pipeline_execution_result.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        json.dump(output, handle, indent=2)
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
