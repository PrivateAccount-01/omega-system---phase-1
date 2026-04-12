from __future__ import annotations

import json
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path

import httpx


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


def main() -> None:
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

    probes = [
        _probe("https://www.nseindia.com/api/corporates-corporateActions?index=equities", nse_headers),
        _probe("https://www.bseindia.com/download/BhavCopy/Equity/EQ_ISINCODE_100426.ZIP", bse_headers),
    ]
    out_dir = Path("artifacts/verification")
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "probes": probes,
    }
    out_path = out_dir / "source_probe_report.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
