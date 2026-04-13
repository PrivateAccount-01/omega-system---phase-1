from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

from omegadata.track_a.download_manager import DownloadManager
from omegadata.track_a.trading_calendar import TradingCalendar


def _probe_dict(result: object) -> dict[str, object]:
    payload = dict(result.__dict__)
    if isinstance(payload.get("as_of"), date):
        payload["as_of"] = payload["as_of"].isoformat()
    return payload


def main() -> None:
    manager = DownloadManager()
    calendar = TradingCalendar.from_config()
    business_days = calendar.recent_trading_days("BSE", anchor_date=date.today(), limit=3)
    probe_date = business_days[0]
    probe_profiles = manager._header_profiles()[:1]
    nse_probes = [
        _probe_dict(probe)
        for probe in manager.probe_source_candidates(
            "NSE_CORPORATE_ACTIONS",
            date.today(),
            limit=1,
            profiles=probe_profiles,
        )
    ]
    bse_page_probes = [
        _probe_dict(probe)
        for probe in manager.probe_source_candidates(
            "BSE_EQUITY_BHAVCOPY",
            probe_date,
            limit=4,
            profiles=probe_profiles,
        )
    ]
    bse_recent_history = []
    for candidate_date in business_days:
        candidate_results = manager.probe_source_candidates(
            "BSE_EQUITY_BHAVCOPY",
            candidate_date,
            limit=4,
            profiles=probe_profiles,
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
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "probe_date": probe_date.isoformat(),
        "calendar_mode": "configured_trading_calendar",
        "probe_profile_count": len(probe_profiles),
        "nse_corporate_actions": nse_probes,
        "bse_equity_candidates": bse_page_probes,
        "bse_recent_history": bse_recent_history,
        "summary": {
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
