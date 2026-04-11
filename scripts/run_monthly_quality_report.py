from __future__ import annotations

import argparse
from datetime import date

from omegadata.db.session import init_db
from omegadata.pipelines.monthly_quality_pipeline import run_monthly_quality_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate OmegaData monthly quality report")
    parser.add_argument("--as-of", default=date.today().isoformat(), help="As-of date in YYYY-MM-DD")
    args = parser.parse_args()

    as_of = date.fromisoformat(args.as_of)
    init_db()
    result = run_monthly_quality_report(as_of=as_of)
    print(f"Generated report for {result.year}-{result.month:02d}: {result.path}")


if __name__ == "__main__":
    main()
