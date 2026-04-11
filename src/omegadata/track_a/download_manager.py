from __future__ import annotations

import hashlib
import json
import random
import ssl
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from omegadata.config import settings
from omegadata.track_a.alerting import AlertEvent, AlertRouter
from omegadata.track_a.monitoring import DOWNLOAD_COUNTER, DOWNLOAD_LATENCY, FAILOVER_COUNTER
from omegadata.track_a.source_registry import SOURCE_REGISTRY, resolve_era


class DownloadError(RuntimeError):
    pass


@dataclass(frozen=True)
class DownloadArtifact:
    source_key: str
    as_of: date
    path: Path
    manifest_path: Path
    checksum: str
    bytes_downloaded: int
    used_url: str
    attempts: int


class DownloadManager:
    def __init__(self) -> None:
        self.raw_root = Path(settings.raw_root)
        self.raw_root.mkdir(parents=True, exist_ok=True)
        self.alert_router = AlertRouter()

    @staticmethod
    def _is_nse_url(url: str) -> bool:
        return "nseindia.com" in url or "nsearchives.nseindia.com" in url

    @staticmethod
    def _is_bse_url(url: str) -> bool:
        return "bseindia.com" in url

    @staticmethod
    def _is_tls_error(exc: Exception) -> bool:
        text = str(exc).lower()
        markers = (
            "tlsv1_alert_internal_error",
            "ssleoferror",
            "ssl",
            "wrong version number",
            "unexpected eof",
            "certificate",
        )
        return any(marker in text for marker in markers)

    @staticmethod
    def _header_profiles() -> list[dict[str, str]]:
        user_agents = [
            (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) "
                "Gecko/20100101 Firefox/125.0"
            ),
            (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 "
                "(KHTML, like Gecko) Version/17.4 Safari/605.1.15"
            ),
        ]
        random.shuffle(user_agents)
        return [
            {
                "User-Agent": ua,
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Connection": "keep-alive",
                "Referer": "https://www.nseindia.com/",
                "Pragma": "no-cache",
                "Cache-Control": "no-cache",
            }
            for ua in user_agents
        ]

    def _profile_for_url(self, base_profile: dict[str, str], url: str) -> dict[str, str]:
        profile = dict(base_profile)
        if self._is_bse_url(url):
            profile["Referer"] = "https://www.bseindia.com/"
            profile["Origin"] = "https://www.bseindia.com"
            profile["Accept"] = "application/json, text/plain, */*"
        elif self._is_nse_url(url):
            profile["Referer"] = "https://www.nseindia.com/"
            profile["Origin"] = "https://www.nseindia.com"
        return profile

    @staticmethod
    def _hash_content(data: bytes, algo: str) -> str:
        if algo.lower() == "md5":
            return hashlib.md5(data, usedforsecurity=False).hexdigest()
        return hashlib.sha256(data).hexdigest()

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, DownloadError)),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def _request(self, client: httpx.Client, url: str) -> bytes:
        response = client.get(url, timeout=60.0)
        if response.status_code in {403, 429}:
            raise DownloadError(f"Blocked by remote source ({response.status_code}): {url}")
        response.raise_for_status()
        if not response.content:
            raise DownloadError(f"Empty payload: {url}")
        return response.content

    def _bootstrap_nse_session(self, client: httpx.Client) -> None:
        # NSE APIs require a warmed session with cookies set by the landing page.
        bootstrap_urls = [
            "https://www.nseindia.com",
            "https://www.nseindia.com/market-data/live-equity-market",
            "https://www.nseindia.com/companies-listing/corporate-filings-actions",
        ]
        last_error: Exception | None = None
        for bootstrap_url in bootstrap_urls:
            try:
                bootstrap = client.get(bootstrap_url, timeout=30.0)
                if bootstrap.status_code in {200, 204, 304}:
                    return
                last_error = DownloadError(
                    f"Unexpected NSE bootstrap status {bootstrap.status_code} for {bootstrap_url}"
                )
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                continue
        raise DownloadError(f"Unable to bootstrap NSE session: {last_error}")

    def _request_via_urllib(self, url: str, headers: dict[str, str]) -> bytes:
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        req = Request(url=url, headers=headers, method="GET")
        try:
            with urlopen(req, timeout=60.0, context=context) as response:
                payload = bytes(response.read())
        except HTTPError as exc:
            raise DownloadError(f"HTTP {exc.code} via urllib for {url}") from exc
        except URLError as exc:
            raise DownloadError(f"URL error via urllib for {url}: {exc}") from exc

        if not payload:
            raise DownloadError(f"Empty payload via urllib: {url}")
        return payload

    def _request_with_workarounds(
        self,
        client: httpx.Client,
        url: str,
        request_headers: dict[str, str],
    ) -> bytes:
        try:
            return self._request(client, url)
        except Exception as exc:  # noqa: BLE001
            if not self._is_nse_url(url) or not self._is_tls_error(exc):
                raise
        return self._request_via_urllib(url=url, headers=request_headers)

    def _render_url(self, source_key: str, as_of: date) -> str:
        era = resolve_era(source_key, as_of)
        return self._render_pattern(era.url_pattern, as_of)

    @staticmethod
    def _render_pattern(pattern: str, as_of: date) -> str:
        return (
            pattern.replace("{YYYY}", f"{as_of.year:04d}")
            .replace("{MM}", f"{as_of.month:02d}")
            .replace("{DD}", f"{as_of.day:02d}")
            .replace("{DDMMYY}", as_of.strftime("%d%m%y"))
            .replace("{YYYYMMDD}", as_of.strftime("%Y%m%d"))
            .replace("{DDMONYYYY}", as_of.strftime("%d%b%Y").upper())
            .replace("{MON}", as_of.strftime("%b").upper())
            .replace("{HH}", "00")
        )

    def _candidate_urls(self, source_key: str, as_of: date) -> list[str]:
        source = SOURCE_REGISTRY[source_key]
        urls = [self._render_url(source_key, as_of)]
        urls.extend(self._render_pattern(pattern, as_of) for pattern in source.failover_url_patterns)
        # Preserve order while deduplicating.
        return list(dict.fromkeys(urls))

    @staticmethod
    def _validate_payload(source_key: str, payload: bytes) -> None:
        text = payload.decode("utf-8", errors="ignore").strip()
        if not text:
            raise DownloadError(f"Empty payload for {source_key}")

        json_sources = {
            "NSE_CORPORATE_ACTIONS",
            "BSE_CORPORATE_ACTIONS",
            "NSE_FII_DII",
            "INDIA_VIX",
        }
        if source_key in json_sources:
            try:
                parsed = json.loads(text)
            except Exception as exc:  # noqa: BLE001
                raise DownloadError(f"Non-JSON payload for {source_key}") from exc

            if source_key == "NSE_CORPORATE_ACTIONS" and isinstance(parsed, dict) and str(
                parsed.get("message", "")
            ).lower().startswith("missing index"):
                raise DownloadError("NSE corporate actions payload indicates missing index")

    def download(self, source_key: str, as_of: date) -> DownloadArtifact:
        if source_key not in SOURCE_REGISTRY:
            raise KeyError(f"Unknown source key: {source_key}")
        source = SOURCE_REGISTRY[source_key]
        candidate_urls = self._candidate_urls(source_key, as_of)
        attempts = 0
        last_error: Exception | None = None
        payload: bytes | None = None
        used_url: str | None = None

        with DOWNLOAD_LATENCY.labels(source=source_key).time():
            consecutive_failures = 0
            for profile in self._header_profiles():
                for idx, url in enumerate(candidate_urls):
                    attempts += 1
                    try:
                        request_headers = self._profile_for_url(profile, url)
                        with httpx.Client(headers=request_headers, follow_redirects=True) as client:
                            if self._is_nse_url(url):
                                self._bootstrap_nse_session(client)
                            payload = self._request_with_workarounds(client, url, request_headers)
                            self._validate_payload(source_key, payload)
                            used_url = url
                            if idx > 0:
                                FAILOVER_COUNTER.labels(source=source_key).inc()
                            break
                    except Exception as exc:  # noqa: BLE001
                        last_error = exc
                        consecutive_failures += 1
                        if self._is_nse_url(url) and self._is_tls_error(exc):
                            delay = min(8.0, 0.75 * (2 ** min(consecutive_failures, 4)))
                            delay += random.uniform(0.05, 0.35)
                            time.sleep(delay)
                        continue
                if payload is not None:
                    break

        if payload is None or used_url is None:
            DOWNLOAD_COUNTER.labels(source=source_key, status="failed").inc()
            self.alert_router.route(
                AlertEvent(
                    severity="ERROR",
                    title="Source Download Failure",
                    message=(
                        f"{source_key} failed after {attempts} attempts. "
                        f"Last error: {last_error}"
                    ),
                    source="download_manager",
                    created_at=datetime.now(UTC),
                )
            )
            raise DownloadError(
                f"Unable to download {source_key} after {attempts} attempts; last error: {last_error}"
            )
        if attempts > 1:
            self.alert_router.route(
                AlertEvent(
                    severity="WARN",
                    title="Source Failover Triggered",
                    message=f"{source_key} succeeded after failover in {attempts} attempts via {used_url}",
                    source="download_manager",
                    created_at=datetime.now(UTC),
                )
            )
        DOWNLOAD_COUNTER.labels(source=source_key, status="success").inc()

        digest = self._hash_content(payload, source.checksum)
        out_dir = self.raw_root / source_key.lower() / f"year={as_of.year:04d}" / f"month={as_of.month:02d}"
        out_dir.mkdir(parents=True, exist_ok=True)

        suffix = ".bin"
        if used_url.endswith(".zip"):
            suffix = ".zip"
        elif used_url.endswith(".csv"):
            suffix = ".csv"
        elif used_url.endswith(".json"):
            suffix = ".json"
        elif used_url.endswith(".txt"):
            suffix = ".txt"

        artifact_stem = f"{as_of.strftime('%Y%m%d')}__{digest[:12]}"
        output = out_dir / f"{artifact_stem}{suffix}"
        if not output.exists():
            output.write_bytes(payload)

        manifest_payload = {
            "source_key": source_key,
            "as_of": as_of.isoformat(),
            "checksum": digest,
            "storage_mode": "immutable_versioned",
            "artifact_path": str(output),
            "bytes_downloaded": len(payload),
            "used_url": used_url,
            "attempts": attempts,
            "downloaded_at": datetime.now(UTC).isoformat(),
        }
        manifest_path = out_dir / f"{artifact_stem}.manifest.json"
        if not manifest_path.exists():
            manifest_path.write_text(json.dumps(manifest_payload, indent=2), encoding="utf-8")

        latest_pointer = out_dir / f"{as_of.strftime('%Y%m%d')}.latest.json"
        latest_pointer.write_text(json.dumps(manifest_payload, indent=2), encoding="utf-8")
        return DownloadArtifact(
            source_key=source_key,
            as_of=as_of,
            path=output,
            manifest_path=manifest_path,
            checksum=digest,
            bytes_downloaded=len(payload),
            used_url=used_url,
            attempts=attempts,
        )

    def fetch_bse_stockreach_graph(
        self,
        scrip_code: str,
        from_date: date,
        to_date: date,
    ) -> dict[str, object]:
        if not scrip_code.strip():
            raise DownloadError("scrip_code is required for StockReachGraph")

        base_urls = (
            "https://api.bseindia.com/BseIndiaAPI/api/StockReachGraph/w",
            "https://api.bseindia.com/RealTimeBseIndiaAPI/api/StockReachGraph/w",
        )

        headers = self._profile_for_url(self._header_profiles()[0], base_urls[0])
        last_error: Exception | None = None
        query = (
            f"scripcode={scrip_code}&flag=1&fromdate={from_date:%Y%m%d}"
            f"&todate={to_date:%Y%m%d}&seriesid="
        )

        for base in base_urls:
            url = f"{base}?{query}"
            try:
                with httpx.Client(headers=headers, follow_redirects=True) as client:
                    payload = self._request(client, url)
                    self._validate_payload("BSE_CORPORATE_ACTIONS", payload)
                parsed = json.loads(payload.decode("utf-8", errors="ignore"))
                if not isinstance(parsed, dict):
                    raise DownloadError("Unexpected StockReachGraph payload type")
                return parsed
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                continue

        raise DownloadError(f"Unable to fetch BSE StockReachGraph for {scrip_code}: {last_error}")
