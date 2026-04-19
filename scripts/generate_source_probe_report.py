from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime
from pathlib import Path

from omegadata.config import settings
from omegadata.track_a.download_manager import DownloadManager
from omegadata.track_a.source_registry import SOURCE_REGISTRY
from omegadata.track_a.trading_calendar import TradingCalendar

REPO_ROOT = Path(__file__).resolve().parents[1]


def _probe_dict(result: object) -> dict[str, object]:
    payload = dict(result.__dict__)
    if isinstance(payload.get("as_of"), date):
        payload["as_of"] = payload["as_of"].isoformat()
    return payload


def _is_calendar_current(statuses: list[dict[str, object]], exchange: str) -> bool:
    for status in statuses:
        if status.get("exchange") != exchange:
            continue
        return str(status.get("status")) == "healthy"
    return False


def _summarize_candidate_history(
    *,
    candidate_date: date,
    results: list[dict[str, object]],
) -> dict[str, object]:
    primary = next((item for item in results if item["role"] == "primary"), None)
    fallbacks = [item for item in results if item["role"] == "fallback"]
    return {
        "date": candidate_date.isoformat(),
        "primary_validated": bool(primary and primary["validated"]),
        "primary_status_code": None if primary is None else primary["status_code"],
        "healthy_fallback_count": sum(1 for item in fallbacks if item["validated"]),
        "failed_fallback_count": sum(1 for item in fallbacks if not item["validated"]),
        "overall_validated": any(item["validated"] for item in results),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile-mode", choices=["deterministic", "full"], default=settings.source_probe_profile_mode)
    parser.add_argument(
        "--workflow",
        choices=["diagnostic", "scheduled_verification"],
        default="diagnostic",
    )
    args = parser.parse_args()

    manager = DownloadManager()
    calendar = TradingCalendar.from_config()
    calendar_maintenance = calendar.all_coverage_statuses(
        anchor_date=date.today(),
        warning_window_days=calendar.maintenance.renewal_window_days,
    )
    bse_calendar_current = calendar.config_state == "loaded" and _is_calendar_current(
        calendar_maintenance,
        "BSE",
    )
    nse_calendar_current = calendar.config_state == "loaded" and _is_calendar_current(
        calendar_maintenance,
        "NSE",
    )
    bse_business_days = calendar.recent_trading_days(
        "BSE",
        anchor_date=date.today(),
        limit=settings.probe_history_days,
    )
    nse_business_days = calendar.recent_trading_days(
        "NSE",
        anchor_date=date.today(),
        limit=settings.probe_history_days,
    )
    probe_date = bse_business_days[0]
    nse_probe_date = nse_business_days[0]
    bse_source = SOURCE_REGISTRY["BSE_EQUITY_BHAVCOPY"]
    expected_primary_url = manager._render_url("BSE_EQUITY_BHAVCOPY", probe_date)
    expected_fallback_urls = {
        manager._render_pattern(pattern, probe_date) for pattern in bse_source.failover_url_patterns
    }
    expected_supported_candidate_urls = {expected_primary_url, *expected_fallback_urls}
    all_profiles = manager._header_profiles()
    probe_mode = args.profile_mode.lower().strip()
    if probe_mode == "full":
        probe_profiles = all_profiles
    else:
        probe_mode = "deterministic"
        probe_profiles = all_profiles[:1]

    nse_probes = [
        _probe_dict(probe)
        for probe in manager.probe_source_candidates(
            "NSE_CORPORATE_ACTIONS",
            date.today(),
            limit=1,
            profiles=probe_profiles,
            request_timeout_seconds=settings.source_probe_timeout_seconds,
        )
    ]
    nse_equity_probes = [
        _probe_dict(probe)
        for probe in manager.probe_source_candidates(
            "NSE_EQUITY_BHAVCOPY",
            nse_probe_date,
            limit=1,
            profiles=probe_profiles,
            request_timeout_seconds=settings.source_probe_timeout_seconds,
        )
    ]
    nse_fo_probes = [
        _probe_dict(probe)
        for probe in manager.probe_source_candidates(
            "NSE_FO_BHAVCOPY",
            nse_probe_date,
            limit=1,
            profiles=probe_profiles,
            request_timeout_seconds=settings.source_probe_timeout_seconds,
        )
    ]
    bse_page_probes = [
        _probe_dict(probe)
        for probe in manager.probe_source_candidates(
            "BSE_EQUITY_BHAVCOPY",
            probe_date,
            limit=None,
            profiles=probe_profiles,
            request_timeout_seconds=settings.source_probe_timeout_seconds,
        )
    ]

    bse_recent_history = []
    for candidate_date in bse_business_days:
        candidate_results = [
            _probe_dict(probe)
            for probe in manager.probe_source_candidates(
                "BSE_EQUITY_BHAVCOPY",
                candidate_date,
                limit=None,
                profiles=probe_profiles,
                request_timeout_seconds=settings.source_probe_timeout_seconds,
            )
        ]
        entry = _summarize_candidate_history(candidate_date=candidate_date, results=candidate_results)
        fallbacks = [item for item in candidate_results if item["role"] == "fallback"]
        entry["all_supported_fallbacks_probed"] = len(fallbacks) == len(expected_fallback_urls)
        entry["all_supported_fallbacks_healthy"] = bool(fallbacks) and all(item["validated"] for item in fallbacks)
        bse_recent_history.append(entry)

    nse_equity_recent_history = []
    for candidate_date in nse_business_days:
        candidate_results = [
            _probe_dict(probe)
            for probe in manager.probe_source_candidates(
                "NSE_EQUITY_BHAVCOPY",
                candidate_date,
                limit=1,
                profiles=probe_profiles,
                request_timeout_seconds=settings.source_probe_timeout_seconds,
            )
        ]
        nse_equity_recent_history.append(
            _summarize_candidate_history(candidate_date=candidate_date, results=candidate_results)
        )

    out_dir = REPO_ROOT / "artifacts/verification"
    out_dir.mkdir(parents=True, exist_ok=True)
    probed_urls = {item["url"] for item in bse_page_probes}
    probed_fallback_urls = {item["url"] for item in bse_page_probes if item["role"] == "fallback"}
    healthy_fallback_count = sum(
        1 for item in bse_page_probes if item["role"] == "fallback" and item["validated"]
    )
    failed_fallback_count = sum(
        1 for item in bse_page_probes if item["role"] == "fallback" and not item["validated"]
    )
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "workflow": args.workflow,
        "probe_date": probe_date.isoformat(),
        "nse_equity_probe_date": nse_probe_date.isoformat(),
        "calendar_mode": (
            "configured_trading_calendar"
            if bse_calendar_current and nse_calendar_current
            else "weekday_fallback_due_to_missing_invalid_or_expired_calendar_coverage"
        ),
        "calendar_config_state": calendar.config_state,
        "calendar_config_path": calendar.config_path,
        "calendar_config_error": calendar.config_error,
        "probe_profile_mode": probe_mode,
        "probe_profile_count": len(probe_profiles),
        "probe_timeout_seconds": settings.source_probe_timeout_seconds,
        "calendar_maintenance": calendar_maintenance,
        "bse_supported_candidate_count": len(expected_supported_candidate_urls),
        "bse_probed_candidate_count": len(probed_urls),
        "bse_supported_fallback_count": len(expected_fallback_urls),
        "bse_probed_fallback_count": len(probed_fallback_urls),
        "bse_probe_scope": "full_supported_registry_candidates",
        "nse_corporate_actions": nse_probes,
        "nse_equity_bhavcopy": nse_equity_probes,
        "nse_fo_bhavcopy": nse_fo_probes,
        "nse_equity_recent_history": nse_equity_recent_history,
        "bse_equity_candidates": bse_page_probes,
        "bse_recent_history": bse_recent_history,
        "summary": {
            "all_supported_candidates_probed": expected_supported_candidate_urls.issubset(probed_urls),
            "all_supported_fallbacks_probed": expected_fallback_urls.issubset(probed_fallback_urls),
            "nse_equity_primary_validated": any(
                item["role"] == "primary" and item["validated"] for item in nse_equity_probes
            ),
            "nse_fo_primary_validated": any(
                item["role"] == "primary" and item["validated"] for item in nse_fo_probes
            ),
            "bse_primary_validated": any(item["role"] == "primary" and item["validated"] for item in bse_page_probes),
            "bse_any_fallback_validated": healthy_fallback_count > 0,
            "all_supported_fallbacks_healthy": healthy_fallback_count == len(expected_fallback_urls),
            "healthy_fallback_count": healthy_fallback_count,
            "failed_fallback_count": failed_fallback_count,
            "bse_any_candidate_validated": any(item["validated"] for item in bse_page_probes),
            "bse_failed_candidates": [item["url"] for item in bse_page_probes if not item["validated"]],
        },
    }
    out_path = out_dir / "source_probe_report.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")
    if args.workflow == "scheduled_verification":
        summary = report["summary"]
        if not (bse_calendar_current and nse_calendar_current):
            raise SystemExit("Scheduled verification requires loaded and current trading-calendar configuration.")
        if not bool(summary["nse_equity_primary_validated"]):
            raise SystemExit("Scheduled verification failed: NSE equity bhavcopy primary probe is unhealthy.")
        if not bool(summary["nse_fo_primary_validated"]):
            raise SystemExit("Scheduled verification failed: NSE F&O bhavcopy primary probe is unhealthy.")
        if not bool(summary["bse_primary_validated"]):
            raise SystemExit("Scheduled verification failed: BSE equity bhavcopy primary probe is unhealthy.")
        if not bool(summary["all_supported_fallbacks_healthy"]):
            raise SystemExit(
                "Scheduled verification failed: not all supported BSE fallbacks are healthy."
            )


if __name__ == "__main__":
    main()
