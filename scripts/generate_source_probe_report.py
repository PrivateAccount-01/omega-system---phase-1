from __future__ import annotations

import json
from contextlib import suppress
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import httpx

from omegadata.track_a.download_manager import DownloadManager


def _probe(url: str, headers: dict[str, str]) -> dict[str, object]:
    try:
        with httpx.Client(headers=headers, follow_redirects=True, timeout=30.0) as client:
            response = client.get(url)
        return {
            "url": url,
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type", ""),
            "body_preview": response.text[:220].replace("\n", " "),
        }
    except Exception as exc:  # noqa: BLE001
        return {"url": url, "error": str(exc)}


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


def _select_bse_probe_date(manager: DownloadManager, bse_headers: dict[str, str]) -> tuple[date, list[dict[str, object]]]:
    fallback_date = _recent_business_days(1)[0]
    fallback_urls = manager._candidate_urls("BSE_EQUITY_BHAVCOPY", fallback_date)[:3]
    fallback_probes = [_probe(url, bse_headers) for url in fallback_urls]

    for candidate_date in _recent_business_days(10):
        urls = manager._candidate_urls("BSE_EQUITY_BHAVCOPY", candidate_date)[:3]
        if not urls:
            continue
        probes = [_probe(url, bse_headers) for url in urls]
        if any(probe.get("status_code") == 200 for probe in probes):
            return candidate_date, probes

    return fallback_date, fallback_probes


def main() -> None:
    manager = DownloadManager()
    nse_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/",
    }
    bse_headers = {
        "User-Agent": nse_headers["User-Agent"],
        "Referer": "https://www.bseindia.com/",
    }

    warm_urls = [
        "https://www.nseindia.com",
        "https://www.nseindia.com/companies-listing/corporate-filings-actions",
    ]
    with httpx.Client(headers=nse_headers, follow_redirects=True, timeout=30.0) as client:
        for url in warm_urls:
            with suppress(Exception):
                client.get(url)

    probe_date, bse_probes = _select_bse_probe_date(manager, bse_headers)
    probes = [
        _probe("https://www.nseindia.com/api/corporates-corporateActions?index=equities", nse_headers),
        _probe("https://www.bseindia.com/markets/MarketInfo/BhavCopy.aspx?expandable=3", bse_headers),
    ]
    probes.extend(bse_probes)
    out_dir = Path("artifacts/verification")
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "probe_date": probe_date.isoformat(),
        "probes": probes,
    }
    out_path = out_dir / "source_probe_report.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
