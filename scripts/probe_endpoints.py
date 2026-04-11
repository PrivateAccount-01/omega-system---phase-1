from __future__ import annotations

from datetime import date, timedelta

import httpx


def probe_corporate_actions() -> None:
    urls = [
        "https://www.nseindia.com/api/corporates-corporateActions",
        "https://www.nseindia.com/api/corporates-corporateActions?index=equities",
        "https://www.nseindia.com/api/corporate-announcements?index=equities",
        "https://api.bseindia.com/BseIndiaAPI/api/Corpforthresults/w",
        "https://api.bseindia.com/BseIndiaAPI/api/Corpforthresults/w?strCat=-1",
    ]
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/",
    }

    with httpx.Client(headers=headers, follow_redirects=True, timeout=30.0) as client:
        for warm in [
            "https://www.nseindia.com",
            "https://www.nseindia.com/companies-listing/corporate-filings-actions",
        ]:
            try:
                client.get(warm)
            except Exception:
                pass

        for url in urls:
            try:
                resp = client.get(url)
                print("URL", url)
                print("STATUS", resp.status_code)
                print("CTYPE", resp.headers.get("content-type"))
                print("BODY", resp.text[:220].replace("\n", " "))
                print("---")
            except Exception as exc:  # noqa: BLE001
                print("URL", url)
                print("ERROR", str(exc))
                print("---")


def probe_bse_bhavcopy() -> None:
    patterns = [
        "https://www.bseindia.com/download/BhavCopy/Equity/EQ{d}_CSV.ZIP",
        "https://www.bseindia.com/download/BhavCopy/Equity/EQ{d}.CSV",
        "https://www.bseindia.com/download/BhavCopy/Equity/EQ{d}_CSV.zip",
    ]
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.bseindia.com/",
    }
    with httpx.Client(headers=headers, follow_redirects=True, timeout=30.0) as client:
        for i in range(1, 5):
            d = (date.today() - timedelta(days=i)).strftime("%d%m%y")
            print("DATE", d)
            for pattern in patterns:
                url = pattern.format(d=d)
                try:
                    resp = client.get(url)
                    print(
                        "BSE_URL",
                        url,
                        "STATUS",
                        resp.status_code,
                        "LEN",
                        len(resp.content),
                        "CTYPE",
                        resp.headers.get("content-type"),
                    )
                except Exception as exc:  # noqa: BLE001
                    print("BSE_URL", url, "ERROR", str(exc))
            print("===")


if __name__ == "__main__":
    probe_corporate_actions()
    probe_bse_bhavcopy()
