from __future__ import annotations

import argparse
import csv
import io
import json
import time
import zipfile
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from omegadata.track_a.download_manager import DownloadError, DownloadManager
from omegadata.track_a.source_registry import resolve_era
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


def _relative_repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except Exception:  # noqa: BLE001
        return path.as_posix().replace("\\", "/")


def _read_columns(path: Path) -> tuple[list[str], list[str]]:
    payload = path.read_bytes()
    anomalies: list[str] = []
    csv_name = path.name
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
            if not names:
                return [], ["missing_csv_member"]
            csv_name = names[0]
            payload = archive.read(names[0])
    try:
        text = payload.decode("utf-8", errors="ignore")
        reader = csv.DictReader(io.StringIO(text))
        columns = list(reader.fieldnames or [])
    except Exception as exc:  # noqa: BLE001
        return [], [f"csv_parse_error:{exc}"]
    normalized = {column.strip().upper().replace(" ", "_") for column in columns}
    required_any = (
        {"SYMBOL", "SERIES", "OPEN", "HIGH", "LOW", "CLOSE", "TOTTRDQTY", "ISIN"},
        {"SYMBOL", "SERIES", "OPEN_PRICE", "HIGH_PRICE", "LOW_PRICE", "CLOSE_PRICE", "TOT_TRD_QTY", "ISIN_NUMBER"},
        {"TCKRSYMB", "SCTYSRS", "OPNPRIC", "HGHPRIC", "LWPRIC", "CLSPRIC", "TTLTRADGVOL", "ISIN"},
    )
    if not any(required.issubset(normalized) for required in required_any):
        anomalies.append("unexpected_columns")
    return columns + [f"__csv_member__:{csv_name}"], anomalies


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
    parser.add_argument(
        "--request-timeout-seconds",
        type=float,
        default=15.0,
        help="Per-request timeout for historical proof downloads.",
    )
    parser.add_argument(
        "--max-request-attempts",
        type=int,
        default=1,
        help="Per-transport retry count for historical proof downloads.",
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
    failure_classes: dict[str, int] = {}
    anomaly_counts: dict[str, int] = {}
    era_stats: dict[str, dict[str, int]] = {}
    started = time.perf_counter()
    for as_of in candidate_days:
        era = resolve_era("NSE_EQUITY_BHAVCOPY", as_of)
        stats = era_stats.setdefault(
            era.name,
            {
                "attempted_days": 0,
                "successful_downloads": 0,
                "failed_downloads": 0,
                "anomaly_count": 0,
            },
        )
        stats["attempted_days"] += 1
        try:
            artifact = manager.download(
                "NSE_EQUITY_BHAVCOPY",
                as_of,
                request_timeout_seconds=args.request_timeout_seconds,
                max_request_attempts=args.max_request_attempts,
            )
            used_url = artifact.used_url
            columns, anomalies = _read_columns(artifact.path)
            csv_member = next(
                (column.split(":", 1)[1] for column in columns if column.startswith("__csv_member__:")),
                artifact.path.name,
            )
            columns = [column for column in columns if not column.startswith("__csv_member__:")]
            for anomaly in anomalies:
                anomaly_counts[anomaly] = anomaly_counts.get(anomaly, 0) + 1
            if anomalies:
                stats["anomaly_count"] += len(anomalies)
            rows.append(
                {
                    "date": as_of.isoformat(),
                    "status": "ok",
                    "era": era.name,
                    "era_schema_note": era.schema_note,
                    "bytes_downloaded": artifact.bytes_downloaded,
                    "used_url": used_url,
                    "used_legacy_host": "historical/EQUITIES" in used_url,
                    "attempts": artifact.attempts,
                    "artifact_path": _relative_repo_path(artifact.path),
                    "csv_member": csv_member,
                    "columns": columns,
                    "anomalies": anomalies,
                }
            )
            successes += 1
            stats["successful_downloads"] += 1
        except Exception as exc:  # noqa: BLE001
            legacy_host = "historical/EQUITIES" in str(exc) or "www1.nseindia.com" in str(exc)
            if legacy_host:
                legacy_failures += 1
            status_code = exc.status_code if isinstance(exc, DownloadError) else None
            stage = exc.stage if isinstance(exc, DownloadError) else None
            failure_class = stage or "unknown"
            failure_classes[failure_class] = failure_classes.get(failure_class, 0) + 1
            rows.append(
                {
                    "date": as_of.isoformat(),
                    "status": "failed",
                    "era": era.name,
                    "era_schema_note": era.schema_note,
                    "status_code": status_code,
                    "stage": stage,
                    "error": str(exc),
                    "legacy_host_path": legacy_host,
                }
            )
            stats["failed_downloads"] += 1

    failure_count = len(rows) - successes
    failure_rate = 0.0 if not rows else failure_count / len(rows)
    elapsed_seconds = time.perf_counter() - started
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
        "throughput_seconds": round(elapsed_seconds, 3),
        "average_seconds_per_day": round(elapsed_seconds / len(candidate_days), 3) if candidate_days else 0.0,
        "failure_classes": failure_classes,
        "anomaly_counts": anomaly_counts,
        "per_era_coverage": era_stats,
        "request_timeout_seconds": args.request_timeout_seconds,
        "max_request_attempts": args.max_request_attempts,
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
