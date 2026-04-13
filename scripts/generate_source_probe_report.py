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
    calendar_loaded_and_current = calendar.config_state == "loaded" and _is_calendar_current(
        calendar_maintenance,
        "BSE",
    )
    business_days = calendar.recent_trading_days(
        "BSE",
        anchor_date=date.today(),
        limit=settings.probe_history_days,
    )
    probe_date = business_days[0]
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
    for candidate_date in business_days:
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
        primary = next((item for item in candidate_results if item["role"] == "primary"), None)
        fallbacks = [item for item in candidate_results if item["role"] == "fallback"]
        bse_recent_history.append(
            {
                "date": candidate_date.isoformat(),
                "primary_validated": bool(primary and primary["validated"]),
                "primary_status_code": None if primary is None else primary["status_code"],
                "all_supported_fallbacks_probed": len(fallbacks) == len(expected_fallback_urls),
                "healthy_fallback_count": sum(1 for item in fallbacks if item["validated"]),
                "failed_fallback_count": sum(1 for item in fallbacks if not item["validated"]),
                "all_supported_fallbacks_healthy": bool(fallbacks) and all(item["validated"] for item in fallbacks),
                "overall_validated": any(item["validated"] for item in candidate_results),
            }
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
        "calendar_mode": (
            "configured_trading_calendar"
            if calendar_loaded_and_current
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
        "bse_equity_candidates": bse_page_probes,
        "bse_recent_history": bse_recent_history,
        "summary": {
            "all_supported_candidates_probed": expected_supported_candidate_urls.issubset(probed_urls),
            "all_supported_fallbacks_probed": expected_fallback_urls.issubset(probed_fallback_urls),
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
    if args.workflow == "scheduled_verification" and not calendar_loaded_and_current:
        raise SystemExit("Scheduled verification requires loaded and current trading-calendar configuration.")


if __name__ == "__main__":
    main()
