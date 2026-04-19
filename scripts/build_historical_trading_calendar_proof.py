from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime
from pathlib import Path

from omegadata.track_a.trading_calendar import TradingCalendar

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = REPO_ROOT / "artifacts/verification/historical_trading_calendar_proof.json"


def _year_range(start_date: date, end_date: date) -> list[int]:
    return list(range(start_date.year, end_date.year + 1))


def _exchange_proof(
    calendar: TradingCalendar,
    exchange: str,
    *,
    start_date: date,
    end_date: date,
) -> dict[str, object]:
    required_years = _year_range(start_date, end_date)
    covered_years = sorted(calendar.coverage_years_by_exchange.get(exchange, set()))
    missing_years = [year for year in required_years if year not in covered_years]
    holiday_counts = {
        str(year): sum(1 for value in calendar.holidays_by_exchange.get(exchange, set()) if value.year == year)
        for year in required_years
    }
    special_sessions = calendar.special_sessions_by_exchange.get(exchange, {})
    special_session_counts = {
        str(year): sum(1 for value in special_sessions if value.year == year)
        for year in required_years
    }
    missing_special_session_years = [
        year for year in required_years if special_session_counts[str(year)] == 0
    ]
    return {
        "exchange": exchange,
        "required_years": required_years,
        "covered_years": covered_years,
        "missing_years": missing_years,
        "holiday_count_by_year": holiday_counts,
        "special_session_count_by_year": special_session_counts,
        "missing_special_session_years": missing_special_session_years,
        "sample_special_sessions": [
            {
                "date": session_date.isoformat(),
                "kind": session_kind,
            }
            for session_date, session_kind in sorted(special_sessions.items())
            if start_date.year <= session_date.year <= end_date.year
        ],
        "coverage_complete": not missing_years,
        "special_sessions_complete": not missing_special_session_years,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build long-window historical India trading-calendar proof.")
    parser.add_argument("--start-date", default="2019-01-01")
    parser.add_argument("--end-date", default="2026-12-31")
    args = parser.parse_args()

    start_date = date.fromisoformat(args.start_date)
    end_date = date.fromisoformat(args.end_date)
    calendar = TradingCalendar.from_config()
    exchanges = list(calendar.maintenance.supported_exchanges)
    proofs = [
        _exchange_proof(calendar, exchange, start_date=start_date, end_date=end_date)
        for exchange in exchanges
    ]
    coverage_complete = all(bool(item["coverage_complete"]) for item in proofs)
    special_sessions_complete = all(bool(item["special_sessions_complete"]) for item in proofs)
    artifact = {
        "generated_at": datetime.now(UTC).isoformat(),
        "range": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "calendar_config_state": calendar.config_state,
        "calendar_config_path": calendar.config_path,
        "calendar_config_error": calendar.config_error,
        "supported_exchanges": exchanges,
        "coverage_complete": coverage_complete and calendar.config_state == "loaded",
        "special_sessions_complete": special_sessions_complete and calendar.config_state == "loaded",
        "proofs": proofs,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")
    if not artifact["coverage_complete"] or not artifact["special_sessions_complete"]:
        raise SystemExit("Historical trading-calendar proof is incomplete for the required research window.")


if __name__ == "__main__":
    main()
