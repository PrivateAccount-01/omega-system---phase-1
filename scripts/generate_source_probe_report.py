from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

from omegadata.config import settings
from omegadata.track_a.download_manager import DownloadManager
from omegadata.track_a.source_registry import SOURCE_REGISTRY
from omegadata.track_a.trading_calendar import TradingCalendar


def _probe_dict(result: object) -> dict[str, object]:
    payload = dict(result.__dict__)
    if isinstance(payload.get("as_of"), date):
        payload["as_of"] = payload["as_of"].isoformat()
    return payload


def main() -> None:
    manager = DownloadManager()
    calendar = TradingCalendar.from_config()
    calendar_maintenance = calendar.all_coverage_statuses(
        anchor_date=date.today(),
        warning_window_days=calendar.maintenance.renewal_window_days,
    )
    bse_calendar_status = next(
        (item for item in calendar_maintenance if item["exchange"] == "BSE"),
        None,
    )
    business_days = calendar.recent_trading_days("BSE", anchor_date=date.today(), limit=3)
    probe_date = business_days[0]
    bse_source = SOURCE_REGISTRY["BSE_EQUITY_BHAVCOPY"]
    expected_primary_url = manager._render_url("BSE_EQUITY_BHAVCOPY", probe_date)
    expected_fallback_urls = {
        manager._render_pattern(pattern, probe_date) for pattern in bse_source.failover_url_patterns
    }
    expected_supported_candidate_urls = {expected_primary_url, *expected_fallback_urls}
    probe_mode = settings.source_probe_profile_mode.lower().strip()
    all_profiles = manager._header_profiles()
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
        candidate_results = manager.probe_source_candidates(
            "BSE_EQUITY_BHAVCOPY",
            candidate_date,
            limit=None,
            profiles=probe_profiles,
            request_timeout_seconds=settings.source_probe_timeout_seconds,
        )
        primary = next((item for item in candidate_results if item.role == "primary"), None)
        fallbacks = [item for item in candidate_results if item.role == "fallback"]
        bse_recent_history.append(
            {
                "date": candidate_date.isoformat(),
                "primary_validated": bool(primary and primary.validated),
                "primary_status_code": None if primary is None else primary.status_code,
                "any_fallback_validated": any(item.validated for item in fallbacks),
                "all_fallbacks_healthy": all(item.validated for item in fallbacks) if fallbacks else False,
                "overall_validated": any(item.validated for item in candidate_results),
            }
        )

    out_dir = Path("artifacts/verification")
    out_dir.mkdir(parents=True, exist_ok=True)
    probed_urls = {item["url"] for item in bse_page_probes}
    probed_fallback_urls = {item["url"] for item in bse_page_probes if item["role"] == "fallback"}
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "probe_date": probe_date.isoformat(),
        "calendar_mode": (
            "configured_trading_calendar"
            if calendar.config_state == "loaded"
            and bse_calendar_status
            and bse_calendar_status["status"] not in {"expired", "missing"}
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
            "bse_full_supported_candidate_coverage": expected_supported_candidate_urls.issubset(probed_urls),
            "bse_full_supported_fallback_coverage": expected_fallback_urls.issubset(probed_fallback_urls),
            "bse_primary_validated": any(item["role"] == "primary" and item["validated"] for item in bse_page_probes),
            "bse_any_fallback_validated": any(item["role"] == "fallback" and item["validated"] for item in bse_page_probes),
            "bse_all_fallbacks_healthy": all(
                item["validated"] for item in bse_page_probes if item["role"] == "fallback"
            ) if any(item["role"] == "fallback" for item in bse_page_probes) else False,
            "bse_any_candidate_validated": any(item["validated"] for item in bse_page_probes),
            "bse_failed_candidates": [item["url"] for item in bse_page_probes if not item["validated"]],
        },
    }
    out_path = out_dir / "source_probe_report.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
