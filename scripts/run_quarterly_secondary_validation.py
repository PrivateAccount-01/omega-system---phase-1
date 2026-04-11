from __future__ import annotations

import argparse
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from omegadata.config import settings
from omegadata.db.session import get_session, init_db
from omegadata.track_b.cross_source_validation import CrossSourceValidator


def _decimal(value: object) -> Decimal:
    return Decimal(str(value))


def run_validation_pack(pack: dict[str, object]) -> dict[str, object]:
    validator = CrossSourceValidator()
    results: list[dict[str, object]] = []

    with get_session() as session:
        for item in pack.get("fii_vs_rbi", []):
            outcome = validator.validate_monthly_flow_consistency(
                session=session,
                data_date=date.fromisoformat(item["data_date"]),
                nse_net_flow=_decimal(item["nse_net_flow"]),
                rbi_net_flow=_decimal(item["rbi_net_flow"]),
            )
            results.append(
                {
                    "validation": "fii_vs_rbi",
                    "data_date": item["data_date"],
                    "result": outcome.result.value,
                    "difference_pct": str(outcome.difference_pct),
                }
            )

        for item in pack.get("iv_spot_checks", []):
            outcome = validator.validate_implied_volatility_spot_check(
                session=session,
                isin=item["isin"],
                data_date=date.fromisoformat(item["data_date"]),
                omega_iv=_decimal(item["omega_iv"]),
                reference_iv=_decimal(item["reference_iv"]),
                reference_source=item.get("reference_source", "OPSTRA"),
            )
            results.append(
                {
                    "validation": "iv_spot_check",
                    "isin": item["isin"],
                    "data_date": item["data_date"],
                    "result": outcome.result.value,
                    "difference_pct": str(outcome.difference_pct),
                }
            )

        for item in pack.get("secondary_adjusted_prices", []):
            outcome = validator.validate_secondary_adjusted_price(
                session=session,
                isin=item["isin"],
                data_date=date.fromisoformat(item["data_date"]),
                omegadata_adjusted_price=_decimal(item["omegadata_adjusted_price"]),
                secondary_adjusted_price=_decimal(item["secondary_adjusted_price"]),
                secondary_source=item.get("secondary_source", "YFINANCE"),
            )
            results.append(
                {
                    "validation": "secondary_adjusted_price",
                    "isin": item["isin"],
                    "data_date": item["data_date"],
                    "result": outcome.result.value,
                    "difference_pct": str(outcome.difference_pct),
                }
            )

    return {"results": results}


def run_validation_pack_file(path: Path) -> dict[str, object]:
    pack = json.loads(path.read_text(encoding="utf-8"))
    return run_validation_pack(pack)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run OmegaData quarterly secondary-source validation pack")
    parser.add_argument(
        "--input",
        default=settings.quarterly_validation_pack,
        help="Path to validation-pack JSON file",
    )
    args = parser.parse_args()

    init_db()
    report = run_validation_pack_file(Path(args.input))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
