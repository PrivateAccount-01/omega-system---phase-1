"""One-time, bounded OD-02 method edits; preserve all unrelated OD-01R bytes."""
from pathlib import Path
import re

path = Path("src/omegadata/track_a/download_manager.py")
text = path.read_bytes().decode("utf-8")

def method(name, code):
    global text
    start = text.index("    def " + name + "(")
    found = re.search(r"\n    (?:def |@)", text[start + 1:])
    end = len(text) if found is None else start + 1 + found.start() + 1
    text = text[:start] + code.strip("\n") + "\n\n" + text[end:]

method("_request_once", '''
    def _request_once(self, client: httpx.Client, url: str, *, timeout_seconds: float = 60.0) -> FetchResult:
        self._authorize_url(self._policy_source.get(), url, SourceTransport.HTTPX)
        with self._job_scope() as budget:
            # Only the explicit in-process MockTransport is enabled. No DNS lookup,
            # system proxy or provider connection can run on a normal client.
            if isinstance(client, httpx.Client):
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
''')
method("_request", '''
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
''')
method("_bootstrap_nse_session", '''
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
''')
method("_request_via_urllib", '''
    def _request_via_urllib(self, url: str, headers: dict[str, str], *, timeout_seconds: float = 60.0) -> FetchResult:
        return self._offline_adapter(SourceTransport.URLLIB, url, headers, timeout_seconds)

    def _offline_adapter(self, transport: SourceTransport, url: str, headers: dict[str, str], timeout_seconds: float) -> FetchResult:
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
''')
method("_request_via_curl", '''
    def _request_via_curl(self, url: str, headers: dict[str, str], *, timeout_seconds: float = 60.0) -> FetchResult:
        return self._offline_adapter(SourceTransport.CURL, url, headers, timeout_seconds)
''')
method("_discover_bse_equity_urls", '''
    def _discover_bse_equity_urls(self, as_of: date) -> list[str]:
        url = "https://www.bseindia.com/markets/MarketInfo/BhavCopy.aspx?expandable=3"
        self._authorize_url("BSE_EQUITY_BHAVCOPY", url, SourceTransport.HTTPX)
        headers = self._profile_for_url(self._header_profiles()[0], url)
        with self._job_scope(), self._source_scope("BSE_EQUITY_BHAVCOPY"):
            with httpx.Client(headers=headers, follow_redirects=False, trust_env=False) as client:
                result = self._request(client, url)
            return self._extract_bse_links_from_html(result.payload.decode("utf-8", errors="strict"), url) if False else self._extract_bse_equity_urls(result.payload.decode("utf-8", errors="strict"), as_of)
''')
method("_validate_payload", '''
    def _validate_payload(source_key: str, payload: bytes, *, as_of: date | None = None) -> None:
        validate_payload(source_key, payload, as_of, load_limits())
''')
# The previously static validator retains its existing @staticmethod decorator.
text = text.replace("follow_redirects=True", "follow_redirects=False, trust_env=False")
path.write_bytes(text.encode("utf-8"))
