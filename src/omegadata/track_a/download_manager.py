from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import ssl
import subprocess
import tempfile
import time
import zipfile
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

import httpx

from omegadata.config import settings
from omegadata.track_a.alerting import AlertEvent, AlertRouter
from omegadata.track_a.monitoring import DOWNLOAD_COUNTER, DOWNLOAD_LATENCY, FAILOVER_COUNTER
from omegadata.track_a.source_registry import SOURCE_REGISTRY, resolve_era


class DownloadError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        stage: str = "request",
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.stage = stage


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


@dataclass(frozen=True)
class FetchResult:
    payload: bytes
    status_code: int | None
    content_type: str
    transport: str
    request_attempts: int


@dataclass(frozen=True)
class SourceProbeResult:
    source_key: str
    as_of: date
    url: str
    role: str
    validated: bool
    status_code: int | None
    content_type: str
    bytes_downloaded: int
    attempts: int
    request_attempts: int
    transport: str | None
    header_profile: str | None
    elapsed_seconds: float
    failure_stage: str | None
    error: str | None
    validation_error: str | None
    body_preview: str


class DownloadManager:
    def __init__(self) -> None:
        self.raw_root = Path(settings.raw_root)
        self.raw_root.mkdir(parents=True, exist_ok=True)
        self.alert_router = AlertRouter()

    def _load_cached_artifact(self, source_key: str, as_of: date) -> DownloadArtifact | None:
        out_dir = self.raw_root / source_key.lower() / f"year={as_of.year:04d}" / f"month={as_of.month:02d}"
        latest_pointer = out_dir / f"{as_of.strftime('%Y%m%d')}.latest.json"
        if not latest_pointer.exists():
            return None
        try:
            manifest_payload = json.loads(latest_pointer.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return None

        artifact_path = self._path_from_manifest(str(manifest_payload.get("artifact_path", "")))
        manifest_path = self._path_from_manifest(str(manifest_payload.get("manifest_path", latest_pointer)))
        if not artifact_path.exists():
            return None
        if not manifest_path.is_absolute():
            manifest_path = out_dir / manifest_path.name
        checksum = str(manifest_payload.get("checksum", "")).strip()
        if not checksum:
            return None
        actual_checksum = self._hash_content(artifact_path.read_bytes(), SOURCE_REGISTRY[source_key].checksum)
        if actual_checksum != checksum:
            return None
        return DownloadArtifact(
            source_key=source_key,
            as_of=as_of,
            path=artifact_path,
            manifest_path=manifest_path if manifest_path.exists() else latest_pointer,
            checksum=checksum,
            bytes_downloaded=int(manifest_payload.get("bytes_downloaded", artifact_path.stat().st_size)),
            used_url=str(manifest_payload.get("used_url", "")),
            attempts=int(manifest_payload.get("attempts", 0)),
        )

    @staticmethod
    def _path_from_manifest(raw_path: str) -> Path:
        normalized = raw_path.replace("\\", "/").strip()
        if not normalized:
            return Path(raw_path)
        return Path(normalized)

    @staticmethod
    def _expected_bse_equity_markers(as_of: date) -> tuple[str, ...]:
        return (
            f"BhavCopy_BSE_CM_0_0_0_{as_of:%Y%m%d}_F_0000.CSV".lower(),
            f"EQ_ISINCODE_{as_of:%d%m%y}_T0.CSV".lower(),
            f"BSE_EQ_BHAVCOPY_{as_of:%d%m%Y}_T0.ZIP".lower(),
            f"EQ{as_of:%d%m%y}_CSV.ZIP".lower(),
            f"eq{as_of:%d%m%y}_csv.zip".lower(),
        )

    @staticmethod
    def _looks_like_bse_equity_url(url: str, as_of: date) -> bool:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        if host and not (host == "bseindia.com" or host.endswith(".bseindia.com")):
            return False
        path = parsed.path.lower()
        if "bhavcopy" not in path or "equity" not in path:
            return False
        lowered = url.lower()
        return any(marker in lowered for marker in DownloadManager._expected_bse_equity_markers(as_of))

    @staticmethod
    def _extract_bse_links_from_html(page_html: str, base_url: str) -> list[str]:
        class _LinkExtractor(HTMLParser):
            def __init__(self) -> None:
                super().__init__()
                self.links: list[str] = []

            def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
                for name, value in attrs:
                    if name.lower() not in {"href", "src", "data-url"} or not value:
                        continue
                    self.links.append(urljoin(base_url, value))

        parser = _LinkExtractor()
        parser.feed(page_html)
        return parser.links

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
    def _is_retryable_nse_request_error(exc: Exception) -> bool:
        if isinstance(exc, DownloadError):
            if exc.stage != "request":
                return False
            return exc.status_code not in {403, 404, 429}
        return isinstance(exc, httpx.HTTPError)

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
    def _profile_name(profile: dict[str, str]) -> str:
        user_agent = profile.get("User-Agent", "")
        if "Chrome" in user_agent:
            return "chrome_desktop"
        if "Firefox" in user_agent:
            return "firefox_desktop"
        if "Safari" in user_agent and "Chrome" not in user_agent:
            return "safari_desktop"
        return "generic"

    @staticmethod
    def _hash_content(data: bytes, algo: str) -> str:
        if algo.lower() == "md5":
            return hashlib.md5(data, usedforsecurity=False).hexdigest()
        return hashlib.sha256(data).hexdigest()

    def _request_once(self, client: httpx.Client, url: str, *, timeout_seconds: float = 60.0) -> FetchResult:
        response = client.get(url, timeout=timeout_seconds)
        if response.status_code in {403, 429}:
            raise DownloadError(
                f"Blocked by remote source ({response.status_code}): {url}",
                status_code=response.status_code,
                stage="request",
            )
        if response.status_code >= 400:
            raise DownloadError(
                f"HTTP {response.status_code} for {url}",
                status_code=response.status_code,
                stage="request",
            )
        if not response.content:
            raise DownloadError(f"Empty payload: {url}", stage="request")
        return FetchResult(
            payload=response.content,
            status_code=response.status_code,
            content_type=response.headers.get("content-type", ""),
            transport="httpx",
            request_attempts=1,
        )

    def _request(self, client: httpx.Client, url: str, *, timeout_seconds: float = 60.0) -> FetchResult:
        attempts = 0
        last_error: Exception | None = None
        while attempts < 5:
            attempts += 1
            try:
                result = self._request_once(client, url, timeout_seconds=timeout_seconds)
                return FetchResult(
                    payload=result.payload,
                    status_code=result.status_code,
                    content_type=result.content_type,
                    transport=result.transport,
                    request_attempts=attempts,
                )
            except (httpx.HTTPError, DownloadError) as exc:
                last_error = exc
                if attempts >= 5:
                    raise
                delay = min(30.0, 2 ** (attempts - 1))
                time.sleep(delay)
        raise DownloadError(f"Request failed for {url}: {last_error}", stage="request")

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

    def _request_via_urllib(
        self,
        url: str,
        headers: dict[str, str],
        *,
        timeout_seconds: float = 60.0,
    ) -> FetchResult:
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        req = Request(url=url, headers=headers, method="GET")
        try:
            with urlopen(req, timeout=timeout_seconds, context=context) as response:
                payload = bytes(response.read())
                content_type = response.headers.get("content-type", "")
        except HTTPError as exc:
            raise DownloadError(
                f"HTTP {exc.code} via urllib for {url}",
                status_code=exc.code,
                stage="request",
            ) from exc
        except URLError as exc:
            raise DownloadError(f"URL error via urllib for {url}: {exc}", stage="request") from exc

        if not payload:
            raise DownloadError(f"Empty payload via urllib: {url}", stage="request")
        return FetchResult(
            payload=payload,
            status_code=200,
            content_type=content_type,
            transport="urllib",
            request_attempts=1,
        )

    @staticmethod
    def _attach_cookie_header(
        headers: dict[str, str],
        client: httpx.Client | None,
    ) -> dict[str, str]:
        if client is None or not client.cookies:
            return headers
        cookie_header = "; ".join(f"{name}={value}" for name, value in client.cookies.items())
        if not cookie_header:
            return headers
        enriched = dict(headers)
        enriched["Cookie"] = cookie_header
        return enriched

    def _request_via_curl(
        self,
        url: str,
        headers: dict[str, str],
        *,
        timeout_seconds: float = 60.0,
    ) -> FetchResult:
        with tempfile.NamedTemporaryFile() as body_handle, tempfile.NamedTemporaryFile(mode="w+", encoding="utf-8") as header_handle:
            cmd = [
                "curl",
                "--http1.1",
                "--location",
                "--silent",
                "--show-error",
                "--fail",
                "--retry",
                "2",
                "--retry-all-errors",
                "--connect-timeout",
                str(int(timeout_seconds)),
                "--max-time",
                str(int(timeout_seconds)),
                "--dump-header",
                header_handle.name,
                "--output",
                body_handle.name,
            ]
            for name, value in headers.items():
                cmd.extend(["-H", f"{name}: {value}"])
            cmd.append(url)

            try:
                completed = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=timeout_seconds + 10.0,
                )
            except subprocess.TimeoutExpired as exc:
                raise DownloadError(
                    f"curl timeout for {url}",
                    stage="request",
                ) from exc

            if completed.returncode != 0:
                message = completed.stderr.strip() or completed.stdout.strip() or f"curl exited {completed.returncode}"
                raise DownloadError(
                    f"curl failed for {url}: {message}",
                    stage="request",
                )

            payload = Path(body_handle.name).read_bytes()
            if not payload:
                raise DownloadError(f"Empty payload via curl: {url}", stage="request")

            status_code: int | None = None
            content_type = ""
            for raw_line in Path(header_handle.name).read_text(encoding="utf-8", errors="ignore").splitlines():
                line = raw_line.strip()
                if line.startswith("HTTP/"):
                    parts = line.split()
                    if len(parts) >= 2 and parts[1].isdigit():
                        status_code = int(parts[1])
                elif ":" in line:
                    name, value = line.split(":", 1)
                    if name.lower().strip() == "content-type":
                        content_type = value.strip()

            if status_code is not None and status_code >= 400:
                raise DownloadError(
                    f"HTTP {status_code} via curl for {url}",
                    status_code=status_code,
                    stage="request",
                )

            return FetchResult(
                payload=payload,
                status_code=status_code or 200,
                content_type=content_type,
                transport="curl",
                request_attempts=1,
            )

    def _request_with_workarounds(
        self,
        client: httpx.Client,
        url: str,
        request_headers: dict[str, str],
        *,
        timeout_seconds: float = 60.0,
    ) -> FetchResult:
        try:
            return self._request(client, url, timeout_seconds=timeout_seconds)
        except Exception as exc:  # noqa: BLE001
            if not self._is_nse_url(url) or not self._is_retryable_nse_request_error(exc):
                raise
        fallback_headers = self._attach_cookie_header(request_headers, client)
        try:
            return self._request_via_urllib(url=url, headers=fallback_headers, timeout_seconds=timeout_seconds)
        except Exception as urllib_exc:  # noqa: BLE001
            if not self._is_retryable_nse_request_error(urllib_exc) and not self._is_tls_error(urllib_exc):
                raise
        return self._request_via_curl(url=url, headers=fallback_headers, timeout_seconds=timeout_seconds)

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
            .replace("{DDMMYYYY}", as_of.strftime("%d%m%Y"))
            .replace("{YYYYMMDD}", as_of.strftime("%Y%m%d"))
            .replace("{DDMONYYYY}", as_of.strftime("%d%b%Y").upper())
            .replace("{MON}", as_of.strftime("%b").upper())
            .replace("{HH}", "00")
        )

    @staticmethod
    def _extract_bse_equity_urls(page_html: str, as_of: date) -> list[str]:
        base_url = "https://www.bseindia.com/markets/MarketInfo/BhavCopy.aspx?expandable=3"
        candidates: list[str] = []
        for url in DownloadManager._extract_bse_links_from_html(page_html, base_url):
            if DownloadManager._looks_like_bse_equity_url(url, as_of):
                candidates.append(url)

        text_pattern = re.compile(r"(?:https://www\.bseindia\.com|/download)/[^\"'\s<]+", re.IGNORECASE)
        for raw in text_pattern.findall(page_html):
            url = urljoin(base_url, raw)
            if DownloadManager._looks_like_bse_equity_url(url, as_of):
                candidates.append(url)
        return list(dict.fromkeys(candidates))

    def _discover_bse_equity_urls(self, as_of: date) -> list[str]:
        page_url = "https://www.bseindia.com/markets/MarketInfo/BhavCopy.aspx?expandable=3"
        base_profile = self._header_profiles()[0]
        headers = self._profile_for_url(base_profile, page_url)
        try:
            with httpx.Client(headers=headers, follow_redirects=True, timeout=30.0) as client:
                response = client.get(page_url)
                response.raise_for_status()
        except Exception:
            return []
        return self._extract_bse_equity_urls(response.text, as_of)

    def _candidate_urls(self, source_key: str, as_of: date) -> list[str]:
        source = SOURCE_REGISTRY[source_key]
        urls: list[str] = []
        if source_key == "BSE_EQUITY_BHAVCOPY":
            urls.extend(self._discover_bse_equity_urls(as_of))
        urls.append(self._render_url(source_key, as_of))
        urls.extend(self._render_pattern(pattern, as_of) for pattern in source.failover_url_patterns)
        # Preserve order while deduplicating.
        return list(dict.fromkeys(urls))

    @staticmethod
    def _validate_csv_header(header_line: str, expected_columns: tuple[str, ...], *, source_key: str) -> None:
        if "html" in header_line.lower():
            raise DownloadError(f"{source_key} returned HTML instead of market data", stage="validation")
        reader = csv.reader([header_line])
        row = next(reader, [])
        normalized = {column.strip().lower() for column in row}
        if not any(column.lower() in normalized for column in expected_columns):
            raise DownloadError(f"{source_key} payload is missing expected columns", stage="validation")

    @staticmethod
    def _select_bse_equity_zip_member(zf: zipfile.ZipFile, as_of: date | None) -> str:
        names = [name for name in zf.namelist() if name.lower().endswith(".csv")]
        if not names:
            raise DownloadError("BSE equity bhavcopy zip contains no CSV files", stage="validation")

        marker_scores: list[tuple[int, str]] = []
        expected_markers = set()
        if as_of is not None:
            expected_markers = set(DownloadManager._expected_bse_equity_markers(as_of))

        for name in names:
            lowered = name.lower()
            score = 0
            if expected_markers and any(marker in lowered for marker in expected_markers):
                score += 100
            if "bse_eq_bhavcopy" in lowered:
                score += 50
            if "eq_isincode" in lowered:
                score += 40
            if "bhavcopy_bse_cm" in lowered:
                score += 30
            if "eq" in lowered:
                score += 5
            marker_scores.append((score, name))

        marker_scores.sort(key=lambda item: (-item[0], item[1].lower()))
        best_score, best_name = marker_scores[0]
        if best_score <= 0:
            raise DownloadError("BSE equity bhavcopy zip contains no expected CSV member", stage="validation")
        return best_name

    @staticmethod
    def _validate_bse_equity_zip_payload(payload: bytes, as_of: date | None = None) -> None:
        try:
            with zipfile.ZipFile(io.BytesIO(payload)) as zf:
                chosen_name = DownloadManager._select_bse_equity_zip_member(zf, as_of)
                lines = zf.read(chosen_name).decode("utf-8", errors="ignore").splitlines()
        except zipfile.BadZipFile as exc:
            raise DownloadError("BSE equity bhavcopy zip payload is invalid", stage="validation") from exc

        if not lines:
            raise DownloadError("BSE equity bhavcopy zip CSV is empty", stage="validation")
        DownloadManager._validate_csv_header(
            lines[0],
            ("ISIN", "ISIN_CODE", "SC_CODE", "TckrSymb"),
            source_key="BSE_EQUITY_BHAVCOPY",
        )

    @staticmethod
    def _validate_payload(source_key: str, payload: bytes, *, as_of: date | None = None) -> None:
        if source_key == "BSE_EQUITY_BHAVCOPY":
            if payload.startswith(b"PK\x03\x04"):
                DownloadManager._validate_bse_equity_zip_payload(payload, as_of)
                return
            text = payload.decode("utf-8", errors="ignore").strip()
            if not text:
                raise DownloadError(f"Empty payload for {source_key}", stage="validation")
            header = text.splitlines()[0] if text.splitlines() else ""
            DownloadManager._validate_csv_header(
                header,
                ("ISIN", "ISIN_CODE", "SC_CODE", "TckrSymb"),
                source_key=source_key,
            )
            return

        text = payload.decode("utf-8", errors="ignore").strip()
        if not text:
            raise DownloadError(f"Empty payload for {source_key}", stage="validation")

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
                raise DownloadError(f"Non-JSON payload for {source_key}", stage="validation") from exc

            if source_key == "NSE_CORPORATE_ACTIONS" and isinstance(parsed, dict) and str(
                parsed.get("message", "")
            ).lower().startswith("missing index"):
                raise DownloadError("NSE corporate actions payload indicates missing index", stage="validation")

    def _fetch_candidate(
        self,
        source_key: str,
        as_of: date,
        *,
        url: str,
        profile: dict[str, str],
        request_timeout_seconds: float = 60.0,
    ) -> FetchResult:
        request_headers = self._profile_for_url(profile, url)
        with httpx.Client(headers=request_headers, follow_redirects=True) as client:
            if self._is_nse_url(url):
                with suppress(Exception):
                    self._bootstrap_nse_session(client)
            result = self._request_with_workarounds(
                client,
                url,
                request_headers,
                timeout_seconds=request_timeout_seconds,
            )
        self._validate_payload(source_key, result.payload, as_of=as_of)
        return result

    def probe_source_candidates(
        self,
        source_key: str,
        as_of: date,
        *,
        limit: int | None = None,
        profiles: list[dict[str, str]] | None = None,
        request_timeout_seconds: float = 15.0,
    ) -> list[SourceProbeResult]:
        candidate_urls = self._candidate_urls(source_key, as_of)
        if limit is not None:
            candidate_urls = candidate_urls[:limit]
        probe_profiles = profiles or self._header_profiles()

        results: list[SourceProbeResult] = []
        for idx, url in enumerate(candidate_urls):
            role = "primary" if idx == 0 else "fallback"
            last_error: str | None = None
            last_validation_error: str | None = None
            last_status_code: int | None = None
            last_content_type = ""
            last_bytes = 0
            last_preview = ""
            last_transport: str | None = None
            last_failure_stage: str | None = None
            last_profile_name: str | None = None
            last_request_attempts = 0
            validated = False
            attempts = 0
            elapsed_seconds = 0.0

            for profile in probe_profiles:
                attempts += 1
                last_profile_name = self._profile_name(profile)
                started = time.perf_counter()
                try:
                    result = self._fetch_candidate(
                        source_key,
                        as_of,
                        url=url,
                        profile=profile,
                        request_timeout_seconds=request_timeout_seconds,
                    )
                    last_status_code = result.status_code
                    last_content_type = result.content_type
                    last_bytes = len(result.payload)
                    last_preview = result.payload[:220].decode("utf-8", errors="ignore").replace("\n", " ")
                    last_transport = result.transport
                    last_request_attempts = result.request_attempts
                    elapsed_seconds = time.perf_counter() - started
                    validated = True
                    last_error = None
                    last_validation_error = None
                    last_failure_stage = None
                    break
                except Exception as exc:  # noqa: BLE001
                    elapsed_seconds = time.perf_counter() - started
                    last_error = str(exc)
                    last_preview = ""
                    if isinstance(exc, DownloadError):
                        last_status_code = exc.status_code
                        last_failure_stage = exc.stage
                        if exc.stage == "validation":
                            last_validation_error = last_error
                    elif "payload" in last_error.lower() or "html" in last_error.lower() or "csv" in last_error.lower():
                        last_validation_error = last_error
                    continue

            results.append(
                SourceProbeResult(
                    source_key=source_key,
                    as_of=as_of,
                    url=url,
                    role=role,
                    validated=validated,
                    status_code=last_status_code,
                    content_type=last_content_type,
                    bytes_downloaded=last_bytes,
                    attempts=attempts,
                    request_attempts=last_request_attempts,
                    transport=last_transport,
                    header_profile=last_profile_name,
                    elapsed_seconds=elapsed_seconds,
                    failure_stage=last_failure_stage,
                    error=last_error,
                    validation_error=last_validation_error,
                    body_preview=last_preview,
                )
            )
        return results

    def download(self, source_key: str, as_of: date) -> DownloadArtifact:
        if source_key not in SOURCE_REGISTRY:
            raise KeyError(f"Unknown source key: {source_key}")
        cached = self._load_cached_artifact(source_key, as_of)
        if cached is not None:
            DOWNLOAD_COUNTER.labels(source=source_key, status="cached").inc()
            return cached
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
                        result = self._fetch_candidate(
                            source_key,
                            as_of,
                            url=url,
                            profile=profile,
                        )
                        payload = result.payload
                        used_url = url
                        if idx > 0:
                            FAILOVER_COUNTER.labels(source=source_key).inc()
                        break
                    except Exception as exc:  # noqa: BLE001
                        last_error = exc
                        consecutive_failures += 1
                        if self._is_nse_url(url) and self._is_tls_error(exc):
                            delay = min(8.0, 0.75 * (2 ** min(consecutive_failures, 4)))
                            delay += 0.2
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
                    result = self._request(client, url)
                    self._validate_payload("BSE_CORPORATE_ACTIONS", result.payload)
                parsed = json.loads(result.payload.decode("utf-8", errors="ignore"))
                if not isinstance(parsed, dict):
                    raise DownloadError("Unexpected StockReachGraph payload type")
                return parsed
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                continue

        raise DownloadError(f"Unable to fetch BSE StockReachGraph for {scrip_code}: {last_error}")
