from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import subprocess as subprocess
import time
import zipfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from pathlib import Path, PureWindowsPath
from threading import RLock
from urllib.parse import urljoin, urlparse
from urllib.request import urlopen as urlopen

import httpx

from omegadata.config import settings
from omegadata.track_a.acquisition import (
    AcquisitionLimits,
    DownloadError,
    PayloadValidation,
    RequestBudget,
    check_status,
    failure,
    load_limits,
    safe_url,
    validate_payload,
    validate_request_options,
)
from omegadata.track_a.alerting import AlertEvent, AlertRouter
from omegadata.track_a.monitoring import DOWNLOAD_COUNTER, DOWNLOAD_LATENCY, FAILOVER_COUNTER
from omegadata.track_a.source_registry import SOURCE_REGISTRY, resolve_era
from omegadata.track_a.source_rights import (
    PolicyProvider,
    PolicyRequest,
    SourceOperation,
    SourcePolicyDecision,
    SourcePolicyError,
    SourceTransport,
    authorize_source,
    load_policy_register,
    policy_url_host,
)

HTTPX_CLIENT_TYPE = httpx.Client

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
    policy_decisions: tuple[SourcePolicyDecision, ...] = ()
    source_mode: str = "source_unverified"
    acquisition_state: str = "HTTP_RECEIVED"
    sha256: str = ""


@dataclass(frozen=True)
class FetchResult:
    payload: bytes
    status_code: int | None
    content_type: str
    transport: str
    request_attempts: int
    final_url: str = ""


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
    policy_decisions: tuple[SourcePolicyDecision, ...] = ()
    acquisition_state: str = "HTTP_RECEIVED"


class DownloadManager:
    def __init__(
        self,
        *,
        policy_provider: PolicyProvider | None = None,
        decision_clock: Callable[[], datetime] | None = None,
        acquisition_limits: AcquisitionLimits | None = None,
        acquisition_clock: Callable[[], float] | None = None,
        acquisition_sleep: Callable[[float], None] | None = None,
        offline_adapters: dict[SourceTransport, Callable[[str, dict[str, str], float], FetchResult]] | None = None,
    ) -> None:
        self.raw_root = Path(settings.raw_root)
        self.seed_raw_root = Path(settings.seed_raw_root)
        self.alert_router = AlertRouter()
        self._policy_provider = load_policy_register if policy_provider is None else policy_provider
        self._decision_clock = decision_clock or (lambda: datetime.now(UTC))
        self._policy_source: ContextVar[str] = ContextVar("download_policy_source", default="")
        self.limits = acquisition_limits or load_limits()
        self._acquisition_clock = acquisition_clock or time.monotonic
        self._acquisition_sleep = acquisition_sleep or time.sleep
        self._job: ContextVar[RequestBudget | None] = ContextVar("acquisition_job", default=None)
        self._offline_adapters = dict(offline_adapters or {})
        # Serialize this manager's candidate bundle writes only. Cross-process
        # atomic publication remains OD-04 work.
        self._candidate_lock = RLock()

    @contextmanager
    def _job_scope(self) -> Iterator[RequestBudget]:
        active = self._job.get()
        if active is not None:
            yield active
            return
        budget = RequestBudget(self.limits, self._acquisition_clock, self._acquisition_sleep)
        budget.remaining()
        token = self._job.set(budget)
        try:
            yield budget
        finally:
            self._job.reset(token)

    @contextmanager
    def _source_scope(self, source_key: str) -> Iterator[None]:
        token = self._policy_source.set(source_key)
        try:
            yield
        finally:
            self._policy_source.reset(token)

    def _authorize(
        self,
        source_key: str,
        operation: SourceOperation,
        transport: SourceTransport,
        host: str | None = None,
        consumer_purpose: SourceOperation | None = None,
    ) -> SourcePolicyDecision:
        return authorize_source(
            PolicyRequest(
                source_key=source_key or "UNSCOPED_TRANSPORT",
                operation=operation,
                decision_at=self._decision_clock(),
                requested_transport=transport,
                requested_host=host,
                consumer_purpose=consumer_purpose,
            ),
            self._policy_provider,
        )

    def _authorize_url(
        self,
        source_key: str,
        url: str,
        transport: SourceTransport,
        operation: SourceOperation = SourceOperation.FETCH,
        consumer_purpose: SourceOperation | None = None,
    ) -> SourcePolicyDecision:
        host = policy_url_host(url)
        decision = self._authorize(source_key, operation, transport, host, consumer_purpose)
        budget = self._job.get()
        if budget is not None:
            budget.context.update(source_key=source_key, candidate=safe_url(url),
                transport=transport.value, policy_revision=decision.policy_revision,
                policy_id=decision.policy_id)
        return decision

    def _load_cached_artifact_from_root(
        self,
        root: Path,
        source_key: str,
        as_of: date,
    ) -> DownloadArtifact | None:
        decision = self._authorize(
            source_key, SourceOperation.READ_CACHED,
            SourceTransport.CACHE if root == self.raw_root else SourceTransport.SEED_CACHE,
        )
        out_dir = root / source_key.lower() / f"year={as_of.year:04d}" / f"month={as_of.month:02d}"
        latest_pointer = out_dir / f"{as_of.strftime('%Y%m%d')}.latest.json"
        try:
            canonical_root = root.resolve()
            partition = out_dir.resolve()
            if not partition.is_relative_to(canonical_root) or not latest_pointer.resolve().is_relative_to(partition):
                return None
            manifest_payload = self._read_cache_manifest(latest_pointer)
            artifact_path = self._path_from_manifest(
                manifest_payload.get("artifact_path"), partition=partition,
            )
            manifest_path = self._path_from_manifest(
                manifest_payload.get("manifest_path", str(latest_pointer)), partition=partition,
            )
            if not artifact_path.is_file():
                return None
            if not manifest_path.is_file():
                # Legacy pointers are self-contained even when the optional
                # sidecar is absent. Its reference was already confined above.
                manifest_path = latest_pointer.resolve()
            # Legacy missing identity is constrained by the dated pointer and filename.
            if not artifact_path.name.startswith((f"{as_of:%Y%m%d}.", f"{as_of:%Y%m%d}__")):
                return None
            records = [manifest_payload]
            if manifest_path.resolve() != latest_pointer.resolve():
                records.append(self._read_cache_manifest(manifest_path))
            checksum = manifest_payload.get("checksum")
            if not isinstance(checksum, str) or not re.fullmatch(
                r"[0-9a-f]{32}" if SOURCE_REGISTRY[source_key].checksum == "md5" else r"[0-9a-f]{64}", checksum,
            ):
                return None
            size = artifact_path.stat().st_size
            for record in records:
                if record.get("source_key", source_key) != source_key or any(
                    field in record and record[field] != as_of.isoformat()
                    for field in ("as_of", "trade_date")
                ) or record.get("checksum") != checksum:
                    return None
                if self._path_from_manifest(record.get("artifact_path"), partition=partition) != artifact_path:
                    return None
                length = record.get("bytes_downloaded", size)
                if type(length) is not int or length != size:
                    return None
            attempts = manifest_payload.get("attempts", 0)
            if type(attempts) is not int or attempts < 0:
                return None
            cached_payload = artifact_path.read_bytes()
            actual_checksum = self._hash_content(cached_payload, SOURCE_REGISTRY[source_key].checksum)
            if actual_checksum != checksum:
                return None
        except (OSError, ValueError, TypeError, RuntimeError):
            return None
        return DownloadArtifact(
            source_key=source_key,
            as_of=as_of,
            path=artifact_path,
            manifest_path=manifest_path if manifest_path.exists() else latest_pointer,
            checksum=checksum,
            bytes_downloaded=size,
            used_url=safe_url(str(manifest_payload.get("used_url", ""))),
            attempts=attempts,
            policy_decisions=(decision,),
            source_mode="source_cached_raw" if root == self.raw_root else "source_seed_imported",
            sha256=hashlib.sha256(cached_payload).hexdigest(),
        )

    def _load_cached_artifact(self, source_key: str, as_of: date) -> DownloadArtifact | None:
        cached = self._load_cached_artifact_from_root(self.raw_root, source_key, as_of)
        if cached is not None:
            return cached
        return self._load_cached_artifact_from_root(self.seed_raw_root, source_key, as_of)

    @staticmethod
    def _path_from_manifest(raw_path: object, *, partition: Path) -> Path:
        if not isinstance(raw_path, str) or not raw_path or raw_path != raw_path.strip():
            raise ValueError("Invalid cache path")
        normalized = raw_path.replace("\\", "/")
        windows = PureWindowsPath(normalized)
        if (
            ".." in windows.parts or "\x00" in normalized or normalized.startswith("//")
            or (windows.drive and (len(windows.drive) != 2 or not windows.root))
            or ":" in normalized.removeprefix(windows.drive)
        ):
            raise ValueError("Ambiguous cache path")
        path = Path(normalized)
        # Historical writers used absolute or repository-relative paths; bare names
        # are interpreted only within the dated source partition, never guessed.
        if not path.is_absolute() and len(path.parts) == 1:
            path = partition / path
        resolved = path.resolve()
        if not resolved.is_relative_to(partition):
            raise ValueError("Cache path escapes source partition")
        return resolved

    @staticmethod
    def _read_cache_manifest(path: Path) -> dict[str, object]:
        def unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
            result: dict[str, object] = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("Duplicate cache manifest field")
                result[key] = value
            return result

        payload = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)
        if not isinstance(payload, dict):
            raise ValueError("Cache manifest must be an object")
        return payload

    @staticmethod
    def _expected_bse_equity_markers(as_of: date) -> tuple[str, ...]:
        return (
            f"BhavCopy_BSE_CM_0_0_0_{as_of:%Y%m%d}_F_0000.CSV".lower(),
            f"EQ_ISINCODE_{as_of:%d%m%y}_T0.CSV".lower(),
            f"BSE_EQ_BHAVCOPY_{as_of:%d%m%Y}_T0.ZIP".lower(),
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
        validate_request_options(timeout_seconds, None)
        self._authorize_url(self._policy_source.get(), url, SourceTransport.HTTPX)
        with self._job_scope() as budget:
            # Only the explicit in-process MockTransport is enabled. No DNS lookup,
            # system proxy or provider connection can run on a normal client.
            if isinstance(client, HTTPX_CLIENT_TYPE):
                if not isinstance(client._transport, httpx.MockTransport):
                    raise failure("BLOCKED_EXTERNAL_EGRESS")
                # MockTransport clients may still have environment proxy mounts.
                if client._transport_for_url(httpx.URL(url)) is not client._transport:
                    raise failure("BLOCKED_EXTERNAL_EGRESS")
                timeout = min(timeout_seconds, budget.consume())
                with client.stream("GET", url, timeout=timeout, follow_redirects=False) as response:
                    check_status(response.status_code, response.headers)
                    if str(response.url) != str(httpx.URL(url)):
                        raise failure("REDIRECT_NOT_ALLOWED")
                    if response.headers.get("content-encoding", "identity").lower() != "identity":
                        raise failure("ENCODING_UNSUPPORTED")
                    length = response.headers.get("content-length")
                    if length is not None and (not length.isdigit() or int(length) > self.limits.body_bytes):
                        raise failure("BODY_LIMIT_EXCEEDED")
                    chunks = bytearray()
                    for chunk in response.iter_bytes():
                        budget.remaining()
                        if len(chunks) + len(chunk) > self.limits.body_bytes:
                            raise failure("BODY_LIMIT_EXCEEDED")
                        chunks.extend(chunk)
                    payload = bytes(chunks)
                    if length is not None and int(length) != len(payload):
                        raise failure("PARTIAL_PAYLOAD")
                    content_type, status = response.headers.get("content-type", ""), response.status_code
            else:
                # Private callers may explicitly supply a local fake client; the
                # production factory always constructs an HTTPX Client above.
                timeout = min(timeout_seconds, budget.consume())
                response = client.get(url, timeout=timeout)
                check_status(response.status_code, response.headers)
                payload, content_type, status = response.content, response.headers.get("content-type", ""), response.status_code
                if len(payload) > self.limits.body_bytes:
                    raise failure("BODY_LIMIT_EXCEEDED")
            budget.remaining()
            if not payload:
                raise failure("PAYLOAD_EMPTY")
            return FetchResult(payload, status, content_type, "httpx", 1, safe_url(url))

    def _request(self, client: httpx.Client, url: str, *, timeout_seconds: float = 60.0,
                 max_attempts: int = 5) -> FetchResult:
        self._authorize_url(self._policy_source.get(), url, SourceTransport.HTTPX)
        if type(max_attempts) is not int or max_attempts <= 0:
            raise failure("INVALID_ACQUISITION_LIMITS")
        with self._job_scope() as budget:
            for index in range(min(max_attempts, self.limits.max_attempts)):
                try:
                    return self._request_once(client, url, timeout_seconds=timeout_seconds)
                except SourcePolicyError:
                    raise
                except DownloadError as exc:
                    if exc.terminal or exc.reason_code != "HTTP_TRANSIENT":
                        raise
                    if index + 1 >= max_attempts:
                        raise
                except httpx.HTTPError as exc:
                    if self._is_tls_error(exc):
                        raise failure("TLS_INVALID") from exc
                    if not isinstance(exc, (httpx.TimeoutException, httpx.NetworkError)):
                        raise failure("INTERNAL_ERROR") from exc
                    if index + 1 >= max_attempts:
                        raise failure("HTTP_TRANSIENT", terminal=False) from exc
                budget.backoff()
            raise failure("ATTEMPT_BUDGET_EXCEEDED")

    def _bootstrap_nse_session(self, client: httpx.Client) -> None:
        urls = ("https://www.nseindia.com", "https://www.nseindia.com/market-data/live-equity-market",
                "https://www.nseindia.com/companies-listing/corporate-filings-actions")
        with self._job_scope():
            for url in urls:
                self._authorize_url(self._policy_source.get(), url, SourceTransport.HTTPX)
                try:
                    result = self._request(client, url, timeout_seconds=self.limits.request_seconds)
                    if b"access denied" in result.payload[:1024].lower() or b"captcha" in result.payload[:1024].lower():
                        raise failure("PAYLOAD_HTML_DENIAL")
                    return
                except SourcePolicyError:
                    raise
                except DownloadError as exc:
                    if exc.terminal:
                        raise
            raise failure("HTTP_TRANSIENT", terminal=False)

    def _request_via_urllib(self, url: str, headers: dict[str, str], *, timeout_seconds: float = 60.0) -> FetchResult:
        return self._offline_adapter(SourceTransport.URLLIB, url, headers, timeout_seconds)

    def _offline_adapter(self, transport: SourceTransport, url: str, headers: dict[str, str], timeout_seconds: float) -> FetchResult:
        validate_request_options(timeout_seconds, None)
        self._authorize_url(self._policy_source.get(), url, transport)
        adapter = self._offline_adapters.get(transport)
        if adapter is None:
            raise failure("BLOCKED_EXTERNAL_EGRESS")
        with self._job_scope() as budget:
            timeout = min(timeout_seconds, budget.consume())
            # Never forward session cookies/authorization to another transport.
            clean = {k: v for k, v in headers.items() if k.lower() not in {"cookie", "authorization", "proxy-authorization"}}
            result = adapter(url, clean, timeout)
            budget.remaining()
            check_status(result.status_code or 0, {})
            if result.final_url and result.final_url != safe_url(url):
                raise failure("REDIRECT_NOT_ALLOWED")
            if len(result.payload) > self.limits.body_bytes:
                raise failure("BODY_LIMIT_EXCEEDED")
            if not result.payload:
                raise failure("PAYLOAD_EMPTY")
            return replace(result, transport=transport.value.lower(), request_attempts=1, final_url=safe_url(url))

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

    def _request_via_curl(self, url: str, headers: dict[str, str], *, timeout_seconds: float = 60.0) -> FetchResult:
        return self._offline_adapter(SourceTransport.CURL, url, headers, timeout_seconds)

    def _request_with_workarounds(
        self, client: httpx.Client, url: str, request_headers: dict[str, str], *,
        timeout_seconds: float = 60.0, max_request_attempts: int = 5,
    ) -> FetchResult:
        with self._job_scope():
            return self._workarounds_in_job(client, url, request_headers,
                timeout_seconds=timeout_seconds, max_request_attempts=max_request_attempts)

    def _workarounds_in_job(
        self,
        client: httpx.Client,
        url: str,
        request_headers: dict[str, str],
        *,
        timeout_seconds: float = 60.0,
        max_request_attempts: int = 5,
    ) -> FetchResult:
        self._authorize_url(self._policy_source.get(), url, SourceTransport.HTTPX)
        try:
            return self._request(
                client,
                url,
                timeout_seconds=timeout_seconds,
                max_attempts=max_request_attempts,
            )
        except SourcePolicyError:
            raise
        except Exception as exc:  # noqa: BLE001
            if isinstance(exc, DownloadError) and exc.terminal:
                raise
            if not self._is_nse_url(url) or not self._is_retryable_nse_request_error(exc):
                raise
        fallback_headers = self._attach_cookie_header(request_headers, client)
        self._authorize_url(self._policy_source.get(), url, SourceTransport.URLLIB)
        try:
            return self._request_via_urllib(
                url=url,
                headers=fallback_headers,
                timeout_seconds=timeout_seconds,
            )
        except SourcePolicyError:
            raise
        except Exception as urllib_exc:  # noqa: BLE001
            if isinstance(urllib_exc, DownloadError) and urllib_exc.terminal:
                raise
            if not self._is_retryable_nse_request_error(urllib_exc) and not self._is_tls_error(urllib_exc):
                raise
        self._authorize_url(self._policy_source.get(), url, SourceTransport.CURL)
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
        url = "https://www.bseindia.com/markets/MarketInfo/BhavCopy.aspx?expandable=3"
        self._authorize_url("BSE_EQUITY_BHAVCOPY", url, SourceTransport.HTTPX)
        headers = self._profile_for_url(self._header_profiles()[0], url)
        with self._job_scope(), self._source_scope("BSE_EQUITY_BHAVCOPY"):
            with httpx.Client(headers=headers, follow_redirects=False, trust_env=False) as client:
                result = self._request(client, url)
            return self._extract_bse_equity_urls(result.payload.decode("utf-8", errors="strict"), as_of)

    def _discover_nse_fo_urls(self, as_of: date) -> list[str]:
        api_url = "https://www.nseindia.com/api/daily-reports?key=FO"
        self._authorize_url("NSE_FO_BHAVCOPY", api_url, SourceTransport.HTTPX)
        base_profile = self._header_profiles()[0]
        headers = self._profile_for_url(base_profile, api_url)
        try:
            with self._source_scope("NSE_FO_BHAVCOPY"), httpx.Client(headers=headers, follow_redirects=False, trust_env=False) as client:
                self._bootstrap_nse_session(client)
                response = self._request_with_workarounds(
                    client,
                    api_url,
                    request_headers=headers,
                    timeout_seconds=settings.source_probe_timeout_seconds,
                )
        except SourcePolicyError:
            raise
        except Exception:
            # Provider/resource failures must never disappear into discovery fallback.
            raise

        try:
            payload = json.loads(response.payload.decode("utf-8", errors="ignore"))
        except json.JSONDecodeError:
            return []
        if not isinstance(payload, dict):
            return []

        target_dates = {
            as_of.strftime("%d-%b-%Y"),
            as_of.strftime("%d-%b-%y"),
            as_of.isoformat(),
        }
        urls: list[str] = []
        for bucket in ("CurrentDay", "PreviousDay", "FutureDay"):
            entries = payload.get(bucket, [])
            if not isinstance(entries, list):
                continue
            for item in entries:
                if not isinstance(item, dict):
                    continue
                trading_date = str(item.get("tradingDate", ""))
                if trading_date not in target_dates:
                    continue
                file_name = str(item.get("fileActlName", ""))
                file_path = str(item.get("filePath", ""))
                display_name = str(item.get("displayName", ""))
                if not file_name or not file_path:
                    continue
                if "Bhavcopy" not in display_name and "Bhavcopy" not in file_name:
                    continue
                urls.append(urljoin(file_path, file_name))
        return list(dict.fromkeys(urls))

    def _candidate_urls(self, source_key: str, as_of: date) -> list[str]:
        if source_key not in SOURCE_REGISTRY:
            self._authorize(source_key, SourceOperation.FETCH, SourceTransport.HTTPX)
        self._authorize_url(source_key, self._render_url(source_key, as_of), SourceTransport.HTTPX)
        source = SOURCE_REGISTRY[source_key]
        urls: list[str] = []
        if source_key == "BSE_EQUITY_BHAVCOPY":
            urls.extend(self._discover_bse_equity_urls(as_of))
        if source_key == "NSE_FO_BHAVCOPY":
            urls.extend(self._discover_nse_fo_urls(as_of))
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
    def _validate_nse_fo_zip_payload(payload: bytes) -> None:
        try:
            with zipfile.ZipFile(io.BytesIO(payload)) as zf:
                names = [name for name in zf.namelist() if name.lower().endswith(".csv")]
                if not names:
                    raise DownloadError("NSE F&O bhavcopy zip contains no CSV files", stage="validation")
                lines = zf.read(sorted(names)[0]).decode("utf-8", errors="ignore").splitlines()
        except zipfile.BadZipFile as exc:
            raise DownloadError("NSE F&O bhavcopy zip payload is invalid", stage="validation") from exc

        if not lines:
            raise DownloadError("NSE F&O bhavcopy zip CSV is empty", stage="validation")
        DownloadManager._validate_csv_header(
            lines[0],
            ("FH_INSTRUMENT", "INSTRUMENT", "FH_SYMBOL", "SYMBOL"),
            source_key="NSE_FO_BHAVCOPY",
        )

    @staticmethod
    def _validate_payload(source_key: str, payload: bytes, *, as_of: date | None = None,
                          limits: AcquisitionLimits | None = None, content_type: str = "") -> PayloadValidation:
        return validate_payload(source_key, payload, as_of, limits or load_limits(), content_type)

    def _fetch_candidate(
        self,
        source_key: str,
        as_of: date,
        *,
        url: str,
        profile: dict[str, str],
        request_timeout_seconds: float = 60.0,
        max_request_attempts: int = 5,
    ) -> FetchResult:
        self._authorize_url(source_key, url, SourceTransport.HTTPX)
        request_headers = self._profile_for_url(profile, url)
        with self._job_scope(), self._source_scope(source_key), httpx.Client(headers=request_headers, follow_redirects=False, trust_env=False) as client:
            if self._is_nse_url(url):
                try:
                    self._bootstrap_nse_session(client)
                except SourcePolicyError:
                    raise
                except DownloadError as exc:
                    if exc.terminal:
                        raise
                except Exception:  # noqa: BLE001
                    pass
            result = self._request_with_workarounds(
                client,
                url,
                request_headers,
                timeout_seconds=request_timeout_seconds,
                max_request_attempts=max_request_attempts,
            )
        return result

    def _probe_in_job(
        self,
        source_key: str,
        as_of: date,
        *,
        limit: int | None = None,
        profiles: list[dict[str, str]] | None = None,
        request_timeout_seconds: float = 15.0,
        max_request_attempts: int = 5,
    ) -> list[SourceProbeResult]:
        if source_key not in SOURCE_REGISTRY:
            self._authorize(source_key, SourceOperation.FETCH, SourceTransport.HTTPX)
        self._authorize_url(source_key, self._render_url(source_key, as_of), SourceTransport.HTTPX)
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
            policy_decision: SourcePolicyDecision | None = None

            for profile in probe_profiles:
                attempts += 1
                last_profile_name = self._profile_name(profile)
                started = time.perf_counter()
                try:
                    policy_decision = self._authorize_url(source_key, url, SourceTransport.HTTPX)
                    result = self._fetch_candidate(
                        source_key,
                        as_of,
                        url=url,
                        profile=profile,
                        request_timeout_seconds=request_timeout_seconds,
                        max_request_attempts=max_request_attempts,
                    )
                    validation = self._validate_payload(source_key, result.payload, as_of=as_of,
                                                        limits=self.limits, content_type=result.content_type)
                    last_status_code = result.status_code
                    policy_decision = self._authorize_url(source_key, url, SourceTransport(result.transport.upper()))
                    last_content_type = result.content_type
                    last_bytes = len(result.payload)
                    last_preview = ""  # Bodies may contain provider/session secrets.
                    last_transport = result.transport
                    last_request_attempts = result.request_attempts
                    elapsed_seconds = time.perf_counter() - started
                    validated = validation is not None and validation.state == "PAYLOAD_STRUCTURALLY_VALID"
                    last_error = None
                    last_validation_error = None
                    last_failure_stage = None
                    break
                except SourcePolicyError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    if isinstance(exc, DownloadError) and exc.terminal:
                        raise
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
                    url=safe_url(url),
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
                    policy_decisions=() if policy_decision is None else (policy_decision,),
                    acquisition_state="PAYLOAD_STRUCTURALLY_VALID" if validated else "HTTP_RECEIVED",
                )
            )
        return results

    def probe_source_candidates(self, source_key: str, as_of: date, *, limit: int | None = None,
                                profiles: list[dict[str, str]] | None = None,
                                request_timeout_seconds: float = 15.0, max_request_attempts: int = 5) -> list[SourceProbeResult]:
        validate_request_options(request_timeout_seconds, max_request_attempts)
        with self._job_scope() as budget:
            try:
                return self._probe_in_job(source_key, as_of, limit=limit, profiles=profiles,
                                         request_timeout_seconds=request_timeout_seconds, max_request_attempts=max_request_attempts)
            except DownloadError as exc:
                exc.context.update(budget.context, source_key=source_key, requested_date=as_of.isoformat(),
                    purpose="probe", actual_attempts=budget.attempts, max_attempts=budget.limits.max_attempts)
                raise

    def download(self, source_key: str, as_of: date, *, request_timeout_seconds: float | None = None,
                 max_request_attempts: int | None = None, use_cache: bool = True,
                 consumer_purpose: SourceOperation | None = None, cache_only: bool = False) -> DownloadArtifact:
        validate_request_options(request_timeout_seconds, max_request_attempts)
        with self._job_scope() as budget:
            try:
                return self._download_in_job(source_key, as_of, request_timeout_seconds=request_timeout_seconds,
                    max_request_attempts=max_request_attempts, use_cache=use_cache,
                    consumer_purpose=consumer_purpose, cache_only=cache_only)
            except DownloadError as exc:
                exc.context.update(budget.context, source_key=source_key, requested_date=as_of.isoformat(),
                    purpose=consumer_purpose.value if consumer_purpose else "raw-acquisition",
                    actual_attempts=budget.attempts, max_attempts=budget.limits.max_attempts,
                    source_era=resolve_era(source_key, as_of).name if source_key in SOURCE_REGISTRY else "unknown")
                raise

    def _download_in_job(
        self,
        source_key: str,
        as_of: date,
        *,
        request_timeout_seconds: float | None = None,
        max_request_attempts: int | None = None,
        use_cache: bool = True,
        consumer_purpose: SourceOperation | None = None,
        cache_only: bool = False,
    ) -> DownloadArtifact:
        if source_key not in SOURCE_REGISTRY:
            self._authorize(source_key, SourceOperation.READ_CACHED, SourceTransport.CACHE)
        if use_cache:
            cache_decision = self._authorize(
                source_key, SourceOperation.READ_CACHED, SourceTransport.CACHE,
                consumer_purpose=consumer_purpose,
            )
            cached = self._load_cached_artifact(source_key, as_of)
            if cached is not None:
                DOWNLOAD_COUNTER.labels(source=source_key, status="cached").inc()
                return replace(cached, policy_decisions=(cache_decision, *cached.policy_decisions))
        if cache_only:
            raise failure("CACHE_MISS")
        primary_url = self._render_url(source_key, as_of)
        self._authorize_url(source_key, primary_url, SourceTransport.HTTPX, consumer_purpose=consumer_purpose)
        self._authorize_url(source_key, primary_url, SourceTransport.HTTPX, SourceOperation.STORE_RAW, consumer_purpose)
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
                        self._authorize_url(source_key, url, SourceTransport.HTTPX, consumer_purpose=consumer_purpose)
                        result = self._fetch_candidate(
                            source_key,
                            as_of,
                            url=url,
                            profile=profile,
                            request_timeout_seconds=self.limits.request_seconds if request_timeout_seconds is None else request_timeout_seconds,
                            max_request_attempts=self.limits.max_attempts if max_request_attempts is None else max_request_attempts,
                        )
                        validation = self._validate_payload(source_key, result.payload, as_of=as_of,
                                                            limits=self.limits, content_type=result.content_type)
                        payload = result.payload
                        used_url = url
                        if idx > 0:
                            FAILOVER_COUNTER.labels(source=source_key).inc()
                        break
                    except SourcePolicyError:
                        raise
                    except Exception as exc:  # noqa: BLE001
                        if isinstance(exc, DownloadError) and exc.terminal:
                            raise
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
                    message=f"{source_key} succeeded after failover in {attempts} attempts via {safe_url(used_url)}",
                    source="download_manager",
                    created_at=datetime.now(UTC),
                )
            )
        with self._candidate_lock:
            fetch_decision = self._authorize_url(
                source_key, used_url, SourceTransport(result.transport.upper()), consumer_purpose=consumer_purpose,
            )
            store_decision = self._authorize_url(
                source_key, used_url, SourceTransport(result.transport.upper()), SourceOperation.STORE_RAW, consumer_purpose,
            )
            active_budget = self._job.get()
            assert active_budget is not None
            active_budget.remaining()
            DOWNLOAD_COUNTER.labels(source=source_key, status="captured").inc()

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
                "used_url": safe_url(used_url),
                "attempts": attempts,
                "downloaded_at": datetime.now(UTC).isoformat(),
                "policy_decisions": [d.model_dump(mode="json") for d in (fetch_decision, store_decision)],
                "acquisition_evidence": {
                    "schema_version": "acquisition-evidence/v1", "sha256": hashlib.sha256(payload).hexdigest(),
                    "state": "HTTP_RECEIVED" if validation is None else validation.state,
                    "parser_schema": "mock-unverified" if validation is None else validation.schema,
                    "source_era": resolve_era(source_key, as_of).name,
                    "original_url": safe_url(used_url), "final_url": result.final_url or safe_url(used_url),
                    "transport": result.transport, "http_status": result.status_code,
                    "content_type": result.content_type, "actual_attempts": active_budget.attempts,
                    "source_mode": "source_unverified", "external_egress": "BLOCKED_EXTERNAL_EGRESS",
                    "execution_mode": "OFFLINE_SYNTHETIC_TEST_ONLY",
                },
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
                used_url=safe_url(used_url),
                attempts=attempts,
                policy_decisions=(fetch_decision, store_decision),
                source_mode="source_unverified", sha256=hashlib.sha256(payload).hexdigest(),
                acquisition_state="HTTP_RECEIVED" if validation is None else validation.state,
            )

    def fetch_bse_stockreach_graph(
        self,
        scrip_code: str,
        from_date: date,
        to_date: date,
    ) -> dict[str, object]:
        # This helper is not a registered data source; never borrow another feed's rights.
        self._authorize("BSE_STOCKREACH_GRAPH", SourceOperation.FETCH, SourceTransport.HTTPX, "api.bseindia.com")
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
                with httpx.Client(headers=headers, follow_redirects=False, trust_env=False) as client:
                    result = self._request(client, url)
                    self._validate_payload("BSE_CORPORATE_ACTIONS", result.payload)
                parsed = json.loads(result.payload.decode("utf-8", errors="ignore"))
                if not isinstance(parsed, dict):
                    raise DownloadError("Unexpected StockReachGraph payload type")
                return parsed
            except SourcePolicyError:
                raise
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                continue

        raise DownloadError(f"Unable to fetch BSE StockReachGraph for {scrip_code}: {last_error}")
