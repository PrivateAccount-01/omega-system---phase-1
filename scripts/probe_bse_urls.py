from __future__ import annotations

import httpx


def main() -> None:
    date_token = "060426"
    patterns = [
        "https://www.bseindia.com/download/BhavCopy/Equity/EQ_ISINCODE_{d}.zip",
        "https://www.bseindia.com/download/BhavCopy/Equity/EQ_ISINCODE_{d}.ZIP",
        "https://www.bseindia.com/download/BhavCopy/Equity/eq{d}_csv.zip",
        "https://www.bseindia.com/download/BhavCopy/Equity/eq{d}_csv.ZIP",
        "https://www.bseindia.com/download/BhavCopy/Equity/EQ{d}.zip",
        "https://www.bseindia.com/download/BhavCopy/Equity/EQ{d}.ZIP",
        "https://www.bseindia.com/BSEDownload/EQ{d}_CSV.ZIP",
        "https://www.bseindia.com/download/BhavCopy/Equity/BhavCopy_EQUITY_{d}.zip",
        "https://www.bseindia.com/download/BhavCopy/Equity/BhavCopy_EQUITY_{d}.csv",
    ]

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.bseindia.com/",
        "Accept": "*/*",
    }

    with httpx.Client(headers=headers, follow_redirects=True, timeout=20.0) as client:
        for pattern in patterns:
            url = pattern.format(d=date_token)
            try:
                resp = client.get(url)
                print(url)
                print("status", resp.status_code, "len", len(resp.content), "ctype", resp.headers.get("content-type"))
                print(resp.text[:120].replace("\n", " "))
                print("---")
            except Exception as exc:  # noqa: BLE001
                print(url)
                print("error", str(exc))
                print("---")


if __name__ == "__main__":
    main()
