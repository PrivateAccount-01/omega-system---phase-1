from __future__ import annotations

import argparse
import csv
import io
import json
import zipfile
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from omegadata.track_a.source_rights import SourcePolicyError

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = REPO_ROOT / "data/raw/nse_equity_bhavcopy"
SEED_RAW_ROOT = REPO_ROOT / "data/seed_raw/omega_phase2_repo/nse_equity_bhavcopy"
CALENDAR_PATH = REPO_ROOT / "config/trading_holidays_india.json"
OUTPUT_PATH = REPO_ROOT / "artifacts/verification/nse_historical_backfill_report.json"
SEED_AUDIT_PATH = REPO_ROOT / "artifacts/verification/seed_import_audit.json"


def _load_calendar() -> dict[str, object]:
    return json.loads(CALENDAR_PATH.read_text(encoding="utf-8"))


def _holiday_set(payload: dict[str, object], exchange: str) -> set[str]:
    return set(payload.get("holidays", {}).get(exchange, []))


def _special_sessions(payload: dict[str, object], exchange: str) -> set[str]:
    sessions = payload.get("special_sessions", {}).get(exchange, [])
    return {str(item.get("date")) for item in sessions if isinstance(item, dict)}


def _standard_bhavcopy_special_sessions(payload: dict[str, object], exchange: str) -> set[str]:
    sessions = payload.get("special_sessions", {}).get(exchange, [])
    return {
        str(item.get("date"))
        for item in sessions
        if isinstance(item, dict) and str(item.get("kind", "")).strip().lower() != "muhurat_trading"
    }


def _is_trading_day(payload: dict[str, object], exchange: str, value: date) -> bool:
    iso = value.isoformat()
    if iso in _standard_bhavcopy_special_sessions(payload, exchange):
        return True
    if value.weekday() >= 5:
        return False
    return iso not in _holiday_set(payload, exchange)


def _iter_trading_days(start_date: date, end_date: date) -> list[date]:
    payload = _load_calendar()
    values: list[date] = []
    current = start_date
    while current <= end_date:
        if _is_trading_day(payload, "NSE", current):
            values.append(current)
        current += timedelta(days=1)
    return values


def _resolve_era(value: date) -> str:
    if value.year <= 2009:
        return "pre_2010"
    if value.year <= 2019:
        return "2010_2019"
    return "2019_present"


def _validate_archive(path: Path) -> tuple[bool, list[str], str | None]:
    try:
        with zipfile.ZipFile(path) as archive:
            members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
            if not members:
                return False, ["missing_csv_member"], None
            member = members[0]
            payload = archive.read(member)
        reader = csv.DictReader(io.StringIO(payload.decode("utf-8", errors="ignore")))
        headers = {str(value).strip() for value in (reader.fieldnames or [])}
    except Exception as exc:  # noqa: BLE001
        return False, [f"archive_parse_error:{exc}"], None

    valid_header_sets = (
        {"SYMBOL", "SERIES", "OPEN", "HIGH", "LOW", "CLOSE", "TOTTRDQTY", "ISIN"},
        {"TradDt", "BizDt", "ISIN", "TckrSymb", "SctySrs", "OpnPric", "HghPric", "LwPric", "ClsPric", "TtlTradgVol"},
    )
    anomalies: list[str] = []
    if not any(expected.issubset(headers) for expected in valid_header_sets):
        anomalies.append("unexpected_columns")
    return not anomalies, anomalies, member


def _relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _load_cached_archives(root: Path, start_date: date, end_date: date) -> dict[date, list[Path]]:
    archives: dict[date, list[Path]] = {}
    for path in root.glob("year=*/month=*/*.zip"):
        stem = path.stem.split("__")[0]
        if len(stem) != 8 or not stem.isdigit():
            continue
        as_of = date(int(stem[:4]), int(stem[4:6]), int(stem[6:8]))
        if start_date <= as_of <= end_date:
            archives.setdefault(as_of, []).append(path)
    return archives


def _read_seed_audit() -> dict[str, object] | None:
    if not SEED_AUDIT_PATH.exists():
        return None
    return json.loads(SEED_AUDIT_PATH.read_text(encoding="utf-8"))


def _attempt_live_download(as_of: date) -> tuple[bool, Path | None, list[str], str | None]:
    try:
        from omegadata.track_a.download_manager import DownloadManager
    except Exception as exc:  # noqa: BLE001
        return False, None, [f"download_manager_import_failed:{exc}"], None

    try:
        artifact = DownloadManager().download("NSE_EQUITY_BHAVCOPY", as_of)
    except SourcePolicyError:
        raise
    except Exception as exc:  # noqa: BLE001
        return False, None, [f"live_download_failed:{exc}"], None

    valid, anomalies, member = _validate_archive(artifact.path)
    return valid, artifact.path, anomalies, member


def _calendar_coverage(payload: dict[str, object], start_date: date, end_date: date) -> dict[str, object]:
    years = list(range(start_date.year, end_date.year + 1))
    covered = set(payload.get("coverage_years", {}).get("NSE", []))
    missing = [year for year in years if year not in covered]
    return {
        "exchange": "NSE",
        "required_years": years,
        "covered_years": sorted(covered),
        "missing_years": missing,
        "complete": not missing,
        "config_state": "loaded",
        "config_path": "config/trading_holidays_india.json",
        "config_error": None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a broad cache-backed NSE historical backfill artifact.")
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument(
        "--attempt-live-downloads",
        action="store_true",
        help="Attempt the normal live downloader for trading days still missing after canonical and seed cache lookup.",
    )
    args = parser.parse_args()

    start_date = date.fromisoformat(args.start_date)
    end_date = date.fromisoformat(args.end_date)
    calendar = _load_calendar()
    trading_days = _iter_trading_days(start_date, end_date)
    canonical_archives = _load_cached_archives(RAW_ROOT, start_date, end_date)
    seed_archives = _load_cached_archives(SEED_RAW_ROOT, start_date, end_date)
    seed_audit = _read_seed_audit()

    anomaly_counts: dict[str, int] = {}
    per_era: dict[str, dict[str, int]] = {}
    results: list[dict[str, object]] = []
    valid_days = 0
    invalid_days = 0
    seeded_hits = 0
    canonical_hits = 0
    live_hits = 0
    missing_days = 0

    for as_of in trading_days:
        era = _resolve_era(as_of)
        stats = per_era.setdefault(
            era,
            {
                "archived_days": 0,
                "seed_days": 0,
                "live_days": 0,
                "validated_archives": 0,
                "invalid_archives": 0,
                "anomaly_count": 0,
                "missing_days": 0,
            },
        )
        retrieval_mode = "missing"
        archive_path: Path | None = None
        anomalies: list[str] = []
        csv_member: str | None = None
        valid = False

        if canonical_archives.get(as_of):
            archive_path = sorted(canonical_archives[as_of])[0]
            retrieval_mode = "canonical_cached"
            stats["archived_days"] += 1
            valid, anomalies, csv_member = _validate_archive(archive_path)
            canonical_hits += 1
        elif seed_archives.get(as_of):
            archive_path = sorted(seed_archives[as_of])[0]
            retrieval_mode = "seed_cached"
            stats["archived_days"] += 1
            stats["seed_days"] += 1
            valid, anomalies, csv_member = _validate_archive(archive_path)
            seeded_hits += 1
        elif args.attempt_live_downloads:
            valid, archive_path, anomalies, csv_member = _attempt_live_download(as_of)
            retrieval_mode = "live_download" if archive_path is not None else "missing"
            if archive_path is not None:
                stats["archived_days"] += 1
                stats["live_days"] += 1
                live_hits += 1

        if archive_path is None:
            missing_days += 1
            stats["missing_days"] += 1
            results.append(
                {
                    "date": as_of.isoformat(),
                    "status": "missing",
                    "era": era,
                    "retrieval_mode": "missing",
                    "artifact_path": None,
                    "csv_member": None,
                    "anomalies": [],
                }
            )
            continue

        if valid:
            valid_days += 1
            stats["validated_archives"] += 1
        else:
            invalid_days += 1
            stats["invalid_archives"] += 1
            stats["anomaly_count"] += len(anomalies)
            for anomaly in anomalies:
                anomaly_counts[anomaly] = anomaly_counts.get(anomaly, 0) + 1
        results.append(
            {
                "date": as_of.isoformat(),
                "status": "ok" if valid else "invalid",
                "era": era,
                "retrieval_mode": retrieval_mode,
                "artifact_path": _relative(archive_path),
                "csv_member": csv_member,
                "anomalies": anomalies,
            }
        )

    archived_dates = [value for value in trading_days if any(item["date"] == value.isoformat() and item["artifact_path"] for item in results)]
    artifact = {
        "generated_at": datetime.now(UTC).isoformat(),
        "range": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
        "calendar_coverage": _calendar_coverage(calendar, start_date, end_date),
        "sample_mode": "broad_seed_augmented_research_window",
        "cache_only": not args.attempt_live_downloads,
        "years_covered": sorted({value.year for value in archived_dates}),
        "research_window_trading_days": len(trading_days),
        "candidate_trading_days": len([item for item in results if item["artifact_path"]]),
        "successful_downloads": valid_days,
        "cached_successes": canonical_hits + seeded_hits,
        "canonical_cache_hits": canonical_hits,
        "seed_cache_hits": seeded_hits,
        "network_successes": live_hits,
        "live_download_hits": live_hits,
        "failed_downloads": invalid_days,
        "missing_archive_days": missing_days,
        "still_missing_days": missing_days,
        "coverage_ratio": 0.0 if not trading_days else round(valid_days / len(trading_days), 6),
        "failure_rate": 0.0 if not archived_dates else round(invalid_days / len(archived_dates), 6),
        "legacy_host_failures": 0,
        "browser_fallback_required": missing_days > 0,
        "throughput_seconds": 0.0,
        "average_seconds_per_day": 0.0,
        "failure_classes": {"invalid_archive": invalid_days} if invalid_days else {},
        "anomaly_counts": anomaly_counts,
        "per_era_coverage": per_era,
        "request_timeout_seconds": None,
        "max_request_attempts": None,
        "seed_import_audit": None if seed_audit is None else {
            "accepted_count": seed_audit.get("accepted_count"),
            "rejected_count": seed_audit.get("rejected_count"),
            "duplicate_count": seed_audit.get("duplicate_count"),
        },
        "note": (
            "This is a broad research-window archive-coverage artifact built from the canonical immutable raw cache, "
            "the separated omega_phase2_repo seed cache, and optional live downloader fill-ins for remaining gaps. "
            "Seed payloads are treated only as cached raw archives, never as truth that bypasses official-source validation."
        ),
        "results": results,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
