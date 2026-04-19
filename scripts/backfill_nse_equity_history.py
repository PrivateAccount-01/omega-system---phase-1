from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from omegadata.track_a.download_manager import DownloadError, DownloadManager
from omegadata.track_a.trading_calendar import TradingCalendar

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = REPO_ROOT / "artifacts/verification/nse_historical_backfill_report.json"


def _iter_candidate_days(start_date: date, end_date: date) -> list[date]:
    calendar = TradingCalendar.from_config()
    values: list[date] = []
    current = start_date
    while current <= end_date:
        if calendar.is_trading_day("NSE", current, strict=False):
            values.append(current)
        current += timedelta(days=1)
    return values


def _calendar_range_coverage(calendar: TradingCalendar, start_date: date, end_date: date) -> dict[str, object]:
    years = sorted(set(range(start_date.year, end_date.year + 1)))
    missing = [year for year in years if not calendar.year_is_covered("NSE", year)]
    return {
        "exchange": "NSE",
        "required_years": years,
        "covered_years": sorted(calendar.coverage_years_by_exchange.get("NSE", set())),
        "missing_years": missing,
        "complete": not missing and calendar.config_state == "loaded",
        "config_state": calendar.config_state,
        "config_path": calendar.config_path,
        "config_error": calendar.config_error,
    }


def _apply_sample_mode(candidate_days: list[date], sample_mode: str) -> list[date]:
    if sample_mode == "all":
        return candidate_days
    if sample_mode == "first_trading_day_per_year":
        sampled: list[date] = []
        by_year: dict[int, list[date]] = {}
        for value in candidate_days:
            by_year.setdefault(value.year, []).append(value)
        for year in sorted(by_year):
            if by_year[year]:
                sampled.append(by_year[year][0])
        return sampled
    if sample_mode == "first_week_per_year":
        sampled: list[date] = []
        by_year: dict[int, list[date]] = {}
        for value in candidate_days:
            by_year.setdefault(value.year, []).append(value)
        for year in sorted(by_year):
            sampled.extend(by_year[year][:5])
        return sampled
    raise ValueError(f"Unsupported sample_mode: {sample_mode}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill and measure NSE historical bhavcopy downloads.")
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument(
        "--sample-mode",
        choices=["all", "first_trading_day_per_year", "first_week_per_year"],
        default="all",
        help="Sample strategy for the requested range.",
    )
    args = parser.parse_args()

    start_date = date.fromisoformat(args.start_date)
    end_date = date.fromisoformat(args.end_date)
    manager = DownloadManager()
    calendar = TradingCalendar.from_config()
    coverage = _calendar_range_coverage(calendar, start_date, end_date)
    candidate_days = _apply_sample_mode(_iter_candidate_days(start_date, end_date), args.sample_mode)

    rows: list[dict[str, object]] = []
    successes = 0
    legacy_failures = 0
    for as_of in candidate_days:
        try:
            artifact = manager.download("NSE_EQUITY_BHAVCOPY", as_of)
            used_url = artifact.used_url
            rows.append(
                {
                    "date": as_of.isoformat(),
                    "status": "ok",
                    "bytes_downloaded": artifact.bytes_downloaded,
                    "used_url": used_url,
                    "used_legacy_host": "historical/EQUITIES" in used_url,
                    "attempts": artifact.attempts,
                }
            )
            successes += 1
        except Exception as exc:  # noqa: BLE001
            legacy_host = "historical/EQUITIES" in str(exc) or "www1.nseindia.com" in str(exc)
            if legacy_host:
                legacy_failures += 1
            status_code = exc.status_code if isinstance(exc, DownloadError) else None
            stage = exc.stage if isinstance(exc, DownloadError) else None
            rows.append(
                {
                    "date": as_of.isoformat(),
                    "status": "failed",
                    "status_code": status_code,
                    "stage": stage,
                    "error": str(exc),
                    "legacy_host_path": legacy_host,
                }
            )

    failure_count = len(rows) - successes
    failure_rate = 0.0 if not rows else failure_count / len(rows)
    artifact = {
        "generated_at": datetime.now(UTC).isoformat(),
        "range": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
        "calendar_coverage": coverage,
        "sample_mode": args.sample_mode,
        "years_covered": sorted({value.year for value in candidate_days}),
        "candidate_trading_days": len(candidate_days),
        "successful_downloads": successes,
        "failed_downloads": failure_count,
        "failure_rate": failure_rate,
        "legacy_host_failures": legacy_failures,
        "browser_fallback_required": legacy_failures > 0 and failure_rate > 0.0,
        "note": (
            "Browser/session fallback is only recommended when the measured historical failure set remains on the "
            "legacy NSE archive host after the direct transport stack is exhausted."
        ),
        "results": rows,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")
    if not bool(coverage["complete"]):
        raise SystemExit("Historical backfill proof requires complete NSE trading-calendar coverage for the requested range.")


if __name__ == "__main__":
    main()
