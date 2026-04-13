from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from omegadata.track_a.download_manager import DownloadManager


def _probe_dict(result: object) -> dict[str, object]:
    payload = dict(result.__dict__)
    if isinstance(payload.get("as_of"), date):
        payload["as_of"] = payload["as_of"].isoformat()
    return payload


def _recent_business_days(limit: int = 10) -> list[date]:
    today = date.today()
    values: list[date] = []
    offset = 1
    while len(values) < limit:
        candidate = today - timedelta(days=offset)
        offset += 1
        if candidate.weekday() >= 5:
            continue
        values.append(candidate)
    return values


def main() -> None:
    manager = DownloadManager()
    business_days = _recent_business_days(3)
    probe_date = business_days[0]
    nse_probes = [_probe_dict(probe) for probe in manager.probe_source_candidates("NSE_CORPORATE_ACTIONS", date.today(), limit=1)]
    bse_page_probes = [_probe_dict(probe) for probe in manager.probe_source_candidates("BSE_EQUITY_BHAVCOPY", probe_date, limit=4)]
    bse_recent_history = []
    for candidate_date in business_days:
        candidate_results = manager.probe_source_candidates("BSE_EQUITY_BHAVCOPY", candidate_date, limit=4)
        primary = next((item for item in candidate_results if item.role == "primary"), None)
        fallbacks = [item for item in candidate_results if item.role == "fallback"]
        bse_recent_history.append(
            {
                "date": candidate_date.isoformat(),
                "primary_validated": bool(primary and primary.validated),
                "primary_status_code": None if primary is None else primary.status_code,
                "fallback_validated": any(item.validated for item in fallbacks),
                "overall_validated": any(item.validated for item in candidate_results),
            }
        )

    out_dir = Path("artifacts/verification")
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "probe_date": probe_date.isoformat(),
        "nse_corporate_actions": nse_probes,
        "bse_equity_candidates": bse_page_probes,
        "bse_recent_history": bse_recent_history,
        "summary": {
            "bse_primary_validated": any(item["role"] == "primary" and item["validated"] for item in bse_page_probes),
            "bse_fallback_validated": any(item["role"] == "fallback" and item["validated"] for item in bse_page_probes),
            "bse_any_candidate_validated": any(item["validated"] for item in bse_page_probes),
        },
    }
    out_path = out_dir / "source_probe_report.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
