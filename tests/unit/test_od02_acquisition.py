"""SYNTHETIC_TEST_ONLY acquisition fixtures; no provider traffic or official truth claim."""

from __future__ import annotations

import hashlib
import io
import json
import socket
import zipfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import date, timedelta
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest

from omegadata.track_a import download_manager as dm
from omegadata.track_a.acquisition import RequestBudget, load_limits, validate_payload
from omegadata.track_a.download_manager import DownloadError, DownloadManager
from omegadata.track_a.source_rights import SourcePolicyError, SourceTransport

DAY = date(2026, 4, 10)
KEY = "NSE_EQUITY_BHAVCOPY"


def archive(text=None, *, day=DAY, legacy=False, names=None):
    """Known repository mappings, never an authenticated official archive."""
    if text is None:
        text = (
            "SYMBOL,SERIES,OPEN,HIGH,LOW,CLOSE,TOTTRDQTY,ISIN,TIMESTAMP\n"
            f"SYNTHETIC_TEST_ONLY,EQ,10,12,9,11,0,TEST00000001,{day:%d-%b-%Y}\n"
            if legacy
            else "TradDt,BizDt,ISIN,TckrSymb,SctySrs,OpnPric,HghPric,LwPric,ClsPric,TtlTradgVol\n"
            f"{day.isoformat()},{day.isoformat()},TEST00000001,SYNTHETIC_TEST_ONLY,EQ,10,12,9,11,0\n"
        )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        default = (
            f"cm{day:%d%b%Y}bhav.csv"
            if legacy
            else f"BhavCopy_NSE_CM_0_0_0_{day:%Y%m%d}_F_0000.csv"
        )
        for name in names or [default]:
            member = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            member.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(member, text)
    return output.getvalue()


@pytest.mark.parametrize(
    "payload,reason",
    [
        (b"<html>Access Denied</html>", "PAYLOAD_HTML_DENIAL"),
        (b"PK\x03\x04truncated", "ARCHIVE_INVALID"),
        (archive(day=date(2026, 4, 9)), "TRADE_DATE_MISMATCH"),
        (archive("wrong,header\n1,2\n"), "SCHEMA_UNKNOWN"),
        (archive(names=["../escape.csv"]), "ZIP_ENTRY_UNSAFE"),
        (archive(names=[f"{n}.csv" for n in range(20)]), "ARCHIVE_TOO_LARGE"),
    ],
)
def test_t01_t04_t07_invalid_nse_never_validated(payload, reason):
    with pytest.raises(DownloadError) as exc:
        DownloadManager._validate_payload(KEY, payload, as_of=DAY)
    assert getattr(exc.value, "reason_code", None) == reason


@pytest.mark.parametrize("legacy,day", [(True, date(2019, 4, 10)), (False, DAY)])
def test_t05_t06_valid_synthetic_era(legacy, day):
    payload = archive(day=day, legacy=legacy)
    DownloadManager._validate_payload(KEY, payload, as_of=day)


@pytest.mark.parametrize("key", ["NSE_CORPORATE_ACTIONS", "BSE_CORPORATE_ACTIONS", "INDIA_VIX"])
def test_t09_json_denial_not_success(key):
    with pytest.raises(DownloadError) as exc:
        DownloadManager._validate_payload(
            key, b'{"message":"missing index or login required"}', as_of=DAY
        )
    assert getattr(exc.value, "reason_code", None) == "PAYLOAD_HTML_DENIAL"


@pytest.mark.parametrize(
    "status,reason",
    [
        (401, "HTTP_ACCESS_DENIED"),
        (403, "HTTP_ACCESS_DENIED"),
        (451, "HTTP_ACCESS_DENIED"),
        (429, "HTTP_RATE_LIMITED"),
        (404, "HTTP_NOT_FOUND"),
    ],
)
def test_t10_t13_terminal_status_no_later_candidate(
    status, reason, synthetic_source_policy_provider, tmp_path, monkeypatch
):
    manager = DownloadManager(policy_provider=synthetic_source_policy_provider)
    manager.raw_root = tmp_path / "raw"
    calls = []
    real_client = httpx.Client

    def respond(request):
        calls.append(str(request.url))
        return httpx.Response(
            status, headers={"retry-after": "120"}, content=b"SYNTHETIC_TEST_ONLY"
        )

    monkeypatch.setattr(
        dm.httpx, "Client", lambda **kw: real_client(transport=httpx.MockTransport(respond), **kw)
    )
    monkeypatch.setattr(dm.time, "sleep", lambda *_: None)
    monkeypatch.setattr(
        manager,
        "_candidate_urls",
        lambda *_: ["https://example.invalid/one", "https://example.invalid/two"],
    )
    with pytest.raises(DownloadError) as exc:
        manager.download("MOSPI", DAY, use_cache=False)
    assert getattr(exc.value, "reason_code", None) == reason
    assert len(calls) == 1 and not manager.raw_root.exists()


def test_t14_t15_redirect_never_contacts_second_host(synthetic_source_policy_provider, monkeypatch):
    manager = DownloadManager(policy_provider=synthetic_source_policy_provider)
    calls = []
    real_client = httpx.Client

    def respond(request):
        calls.append(str(request.url))
        if len(calls) == 1:
            return httpx.Response(302, headers={"location": "https://foreign.invalid/secret"})
        return httpx.Response(200, content=b"SYNTHETIC_TEST_ONLY")

    monkeypatch.setattr(
        dm.httpx, "Client", lambda **kw: real_client(transport=httpx.MockTransport(respond), **kw)
    )
    with pytest.raises(DownloadError) as exc:
        manager._fetch_candidate("MOSPI", DAY, url="https://example.invalid/data", profile={})
    assert getattr(exc.value, "reason_code", None) == "REDIRECT_NOT_ALLOWED"
    assert calls == ["https://example.invalid/data"]


def test_t17_default_external_egress_disabled(synthetic_source_policy_provider, monkeypatch):
    manager = DownloadManager(policy_provider=synthetic_source_policy_provider)
    contact = Mock(side_effect=AssertionError("No real transport may run"))
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", contact)
    with (
        httpx.Client(trust_env=False) as client,
        manager._source_scope(KEY),
        pytest.raises(DownloadError) as exc,
    ):
        manager._request_once(client, "https://example.invalid/file")
    assert getattr(exc.value, "reason_code", None) == "BLOCKED_EXTERNAL_EGRESS"
    contact.assert_not_called()


@pytest.fixture()
def offline(synthetic_source_policy_provider, tmp_path, monkeypatch):
    manager = DownloadManager(
        policy_provider=synthetic_source_policy_provider, acquisition_sleep=lambda _: None
    )
    manager.raw_root, manager.seed_raw_root = tmp_path / "raw", tmp_path / "seed"
    calls = []
    real_client = httpx.Client

    def install(responder):
        def handler(request):
            calls.append(str(request.url))
            return responder(request)

        monkeypatch.setattr(
            dm.httpx,
            "Client",
            lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw),
        )

    monkeypatch.setattr(
        manager,
        "_candidate_urls",
        lambda *_: ["https://example.invalid/one.zip", "https://example.invalid/two.zip"],
    )
    return manager, calls, install


@pytest.mark.parametrize(
    "change,reason",
    [
        (lambda s: s.replace("HghPric", "OpnPric"), "SCHEMA_UNKNOWN"),
        (lambda s: s.replace(",12,9,11,0", ",8,9,11,0"), "PARTIAL_PAYLOAD"),
        (lambda s: s.replace(",10,12,9,11,0", ",NaN,12,9,11,0"), "PARTIAL_PAYLOAD"),
        (lambda s: s.replace(",10,12,9,11,0", ",-1,12,9,11,0"), "PARTIAL_PAYLOAD"),
        (lambda s: s.replace(",11,0", ",11,0.5"), "PARTIAL_PAYLOAD"),
        (lambda s: s + s.splitlines()[1] + "\n", "PARTIAL_PAYLOAD"),
        (lambda s: s.replace(",EQ,10", ",EQ,extra,10"), "PARTIAL_PAYLOAD"),
        (lambda s: s.splitlines()[0] + "\n", "PAYLOAD_EMPTY"),
        (lambda s: s.replace("2026-04-10", "2026-04-09"), "TRADE_DATE_MISMATCH"),
    ],
)
def test_t07_numeric_date_row_and_header_corruption(change, reason):
    with zipfile.ZipFile(io.BytesIO(archive())) as zf:
        text = zf.read(zf.namelist()[0]).decode()
    with pytest.raises(DownloadError, match=reason):
        validate_payload(KEY, archive(change(text)), DAY, load_limits())


def test_t04_t19_expansion_encoding_and_declared_caps():
    limits = load_limits()
    for body, overrides, reason in [
        (archive("x" * 100000), {"compression_ratio": 2}, "ARCHIVE_TOO_LARGE"),
        (archive(), {"archive_bytes": 10}, "ARCHIVE_TOO_LARGE"),
        (archive(), {"body_bytes": 10}, "BODY_LIMIT_EXCEEDED"),
        (archive(b"\xff\xfe"), {}, "ENCODING_UNSUPPORTED"),
    ]:
        with pytest.raises(DownloadError, match=reason):
            validate_payload(KEY, body, DAY, replace(limits, **overrides))


@pytest.mark.parametrize("name", ["/absolute.csv", "C:/escape.csv", "nested.zip", "..\\escape.csv"])
def test_t04_archive_unsafe_members(name):
    with pytest.raises(DownloadError, match="ZIP_ENTRY_UNSAFE"):
        validate_payload(KEY, archive(names=[name]), DAY, load_limits())


@pytest.mark.parametrize("mime", ["application/json", "image/png", "text/csv"])
def test_t07_content_type_mismatch(mime):
    with pytest.raises(DownloadError, match="SCHEMA_UNKNOWN"):
        validate_payload(KEY, archive(), DAY, load_limits(), mime)


@pytest.mark.parametrize("zipped", [False, True])
def test_t08_bse_synthetic_modern_and_wrong_date(zipped):
    with zipfile.ZipFile(io.BytesIO(archive())) as zf:
        csv_body = zf.read(zf.namelist()[0])
    body = (
        archive(csv_body, names=[f"BhavCopy_BSE_CM_0_0_0_{DAY:%Y%m%d}_F_0000.csv"])
        if zipped
        else csv_body
    )
    result = validate_payload("BSE_EQUITY_BHAVCOPY", body, DAY, load_limits())
    assert result.state == "PAYLOAD_STRUCTURALLY_VALID" and result.rows == 1
    with pytest.raises(DownloadError, match="TRADE_DATE_MISMATCH"):
        validate_payload("BSE_EQUITY_BHAVCOPY", body, date(2026, 4, 9), load_limits())


@pytest.mark.parametrize(
    "body",
    [b"<html>login</html>", b'{"x":1,"x":2}', b'{"ERROR":"missing index"}', b"[]", b"{broken"],
)
def test_t09_json_strict_errors(body):
    with pytest.raises(DownloadError):
        validate_payload("NSE_CORPORATE_ACTIONS", body, DAY, load_limits())


@pytest.mark.parametrize("body", [b'{"data":[{"value":1}]}', b'[{"value":1}]'])
def test_t09_json_not_financially_verified(body):
    result = validate_payload("NSE_CORPORATE_ACTIONS", body, DAY, load_limits())
    assert result.state == "HTTP_RECEIVED"


def test_t11_retry_after_and_typed_public_context(offline):
    manager, calls, install = offline
    install(lambda _: httpx.Response(429, headers={"retry-after": "120"}))
    with pytest.raises(DownloadError) as exc:
        manager.download(KEY, DAY, use_cache=False)
    assert exc.value.retry_after == "120" and exc.value.terminal
    assert exc.value.context["source_key"] == KEY
    assert exc.value.context["requested_date"] == DAY.isoformat()
    assert exc.value.context["actual_attempts"] == 1
    assert exc.value.context["transport"] == "HTTPX"
    assert len(calls) == 1


@pytest.mark.parametrize("mode", ["download", "probe", "bootstrap", "discovery"])
def test_t10_terminal_denial_entire_call_graph(offline, mode):
    manager, calls, install = offline
    install(lambda _: httpx.Response(403))
    with pytest.raises(DownloadError, match="HTTP_ACCESS_DENIED"):
        if mode == "download":
            manager.download(KEY, DAY, use_cache=False)
        elif mode == "probe":
            manager.probe_source_candidates(KEY, DAY)
        elif mode == "bootstrap":
            manager._fetch_candidate(KEY, DAY, url="https://www.nseindia.com/data", profile={})
        else:
            manager._discover_bse_equity_urls(DAY)
    assert len(calls) == 1 and not manager.raw_root.exists()


def test_t13_transient_retries_bounded_and_recovers(offline):
    manager, calls, install = offline
    sleeps = []
    manager._acquisition_sleep = sleeps.append
    install(
        lambda _: httpx.Response(503) if len(calls) < 3 else httpx.Response(200, content=archive())
    )
    artifact = manager.download(KEY, DAY, use_cache=False)
    assert len(calls) == 3 and sleeps == [0.25, 0.5]
    manifest = json.loads(artifact.manifest_path.read_text())
    assert manifest["acquisition_evidence"]["actual_attempts"] == 3


def test_t13_attempt_cap_stops_candidates_and_profiles(offline):
    manager, calls, install = offline
    manager.limits = replace(load_limits(), max_attempts=3)
    install(lambda _: httpx.Response(503))
    with pytest.raises(DownloadError, match="ATTEMPT_BUDGET_EXCEEDED"):
        manager.download(KEY, DAY, use_cache=False)
    assert len(calls) == 3 and not manager.raw_root.exists()


@pytest.mark.parametrize(
    "destination",
    [
        "https://example.invalid/other",
        "https://foreign.invalid/other",
        "http://example.invalid/other",
        "https://169.254.169.254/latest",
    ],
)
def test_t14_t15_all_redirect_destinations_refused(offline, destination):
    manager, calls, install = offline
    install(lambda _: httpx.Response(302, headers={"location": destination}))
    with pytest.raises(DownloadError, match="REDIRECT_NOT_ALLOWED"):
        manager.download(KEY, DAY, use_cache=False)
    assert len(calls) == 1


@pytest.mark.parametrize(
    "url",
    [
        "http://example.invalid/file",
        "https://example.invalid:444/file",
        "https://user:password@example.invalid/file",
        "https:///file",
        "https://127.0.0.1/file",
        "https://169.254.169.254/file",
        "https://[::1]/file",
    ],
)
def test_t16_t17_unsafe_destination_before_transport(offline, url):
    manager, calls, install = offline
    install(lambda _: httpx.Response(200, content=archive()))
    with pytest.raises(SourcePolicyError):
        manager._fetch_candidate(KEY, DAY, url=url, profile={})
    assert not calls


def test_t17_rebinding_and_env_proxy_never_resolved(synthetic_source_policy_provider, monkeypatch):
    manager = DownloadManager(policy_provider=synthetic_source_policy_provider)
    resolver = Mock(
        side_effect=[
            [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))],
            [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))],
        ]
    )
    monkeypatch.setattr(socket, "getaddrinfo", resolver)
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:1")
    with (
        httpx.Client(trust_env=False) as client,
        manager._source_scope(KEY),
        pytest.raises(DownloadError, match="BLOCKED_EXTERNAL_EGRESS"),
    ):
        manager._request_once(client, "https://example.invalid/file")
    resolver.assert_not_called()


def test_t18_cross_transport_budget_no_cookie_leak(synthetic_source_policy_provider):
    from omegadata.track_a.download_manager import FetchResult

    seen = []

    def urllib(url, headers, timeout):
        seen.append(("urllib", headers, timeout))
        raise httpx.ConnectError("SYNTHETIC_TEST_ONLY transient network error")

    def curl(url, headers, timeout):
        seen.append(("curl", headers, timeout))
        return FetchResult(archive(), 200, "application/zip", "curl", 1)

    manager = DownloadManager(
        policy_provider=synthetic_source_policy_provider,
        acquisition_limits=replace(load_limits(), max_attempts=3),
        offline_adapters={SourceTransport.URLLIB: urllib, SourceTransport.CURL: curl},
        acquisition_sleep=lambda _: None,
    )
    fake = Mock()
    fake.cookies = {"private-session": "SYNTHETIC_TEST_ONLY"}
    fake.get.side_effect = httpx.ConnectError("SYNTHETIC_TEST_ONLY network error")
    with manager._source_scope(KEY), manager._job_scope() as budget:
        result = manager._request_with_workarounds(
            fake,
            "https://www.nseindia.com/file",
            {"Authorization": "SYNTHETIC_TEST_ONLY"},
            max_request_attempts=1,
        )
        assert budget.attempts == 3 and result.transport == "curl"
    assert [entry[0] for entry in seen] == ["urllib", "curl"]
    assert all(
        not any(k.lower() in {"cookie", "authorization"} for k in entry[1]) for entry in seen
    )


@pytest.mark.parametrize("adapter", ["urllib", "curl"])
def test_t18_default_alternate_transports_disabled(synthetic_source_policy_provider, adapter):
    manager = DownloadManager(policy_provider=synthetic_source_policy_provider)
    with manager._source_scope(KEY), pytest.raises(DownloadError, match="BLOCKED_EXTERNAL_EGRESS"):
        getattr(manager, "_request_via_" + adapter)("https://example.invalid/file", {})


def test_t19_deadline_includes_backoff(offline):
    manager, calls, install = offline
    clock = [0.0]
    manager._acquisition_clock = lambda: clock[0]
    manager._acquisition_sleep = lambda delay: clock.__setitem__(0, clock[0] + delay)
    manager.limits = replace(load_limits(), total_seconds=0.2)
    install(lambda _: httpx.Response(503))
    with pytest.raises(DownloadError, match="TOTAL_DEADLINE_EXCEEDED"):
        manager.download(KEY, DAY, use_cache=False)
    assert len(calls) == 1 and not manager.raw_root.exists()


@pytest.mark.parametrize(
    "headers,body,reason",
    [
        ({"content-length": "1000000000"}, b"x", "BODY_LIMIT_EXCEEDED"),
        ({"content-length": "1"}, b"xx", "PARTIAL_PAYLOAD"),
        ({"content-encoding": "gzip"}, b"x", "ENCODING_UNSUPPORTED"),
        ({}, b"", "PAYLOAD_EMPTY"),
    ],
)
def test_t19_transport_limits_before_write(offline, headers, body, reason):
    manager, calls, install = offline
    install(lambda _: httpx.Response(200, headers=headers, content=body))
    with pytest.raises(DownloadError, match=reason):
        manager.download(KEY, DAY, use_cache=False)
    assert len(calls) == 1 and not manager.raw_root.exists()


def test_t19_stream_growth_bounded(offline):
    manager, calls, install = offline
    consumed = []

    class Stream(httpx.SyncByteStream):
        def __iter__(self):
            for n in range(100):
                consumed.append(n)
                yield b"12345678"

    manager.limits = replace(load_limits(), body_bytes=16)
    install(lambda _: httpx.Response(200, stream=Stream()))
    with pytest.raises(DownloadError, match="BODY_LIMIT_EXCEEDED"):
        manager.download(KEY, DAY, use_cache=False)
    assert consumed == [0, 1, 2] and not manager.raw_root.exists()


def test_t20_revoked_after_mock_fetch_no_storage(offline, synthetic_source_policy_provider):
    from omegadata.track_a.source_rights import SourcePolicyRegister

    manager, calls, install = offline
    state = [synthetic_source_policy_provider()]
    manager._policy_provider = lambda: state[0]

    def responder(_):
        state[0] = SourcePolicyRegister(schema_version="source-policy/v1", policies=())
        return httpx.Response(200, content=archive())

    install(responder)
    with pytest.raises(SourcePolicyError):
        manager.download(KEY, DAY, use_cache=False)
    assert len(calls) == 1 and not manager.raw_root.exists()


def test_t21_cache_only_never_fetches(offline, monkeypatch):
    manager, calls, install = offline
    fetch = Mock(side_effect=AssertionError("CACHE_ONLY cannot fetch"))
    monkeypatch.setattr(manager, "_fetch_candidate", fetch)
    with pytest.raises(DownloadError, match="CACHE_MISS"):
        manager.download(KEY, DAY, cache_only=True)
    fetch.assert_not_called()
    assert not calls and not manager.raw_root.exists()


def test_t22_valid_fetch_cache_hash_and_secret_free_evidence(offline):
    manager, calls, install = offline
    body = archive()
    install(
        lambda _: httpx.Response(200, headers={"content-type": "application/zip"}, content=body)
    )
    artifact = manager.download(KEY, DAY, use_cache=False)
    cached = manager.download(KEY, DAY, cache_only=True)
    assert artifact.path.read_bytes() == body == cached.path.read_bytes()
    assert artifact.sha256 == cached.sha256 == hashlib.sha256(body).hexdigest()
    assert artifact.source_mode == "source_unverified" and cached.source_mode == "source_cached_raw"
    assert artifact.acquisition_state == "PAYLOAD_STRUCTURALLY_VALID" and len(calls) == 1
    evidence = json.loads(artifact.manifest_path.read_text())["acquisition_evidence"]
    assert (
        evidence["source_mode"] == "source_unverified"
        and evidence["external_egress"] == "BLOCKED_EXTERNAL_EGRESS"
    )
    assert evidence["parser_schema"] == "equity-udiff/v1" and evidence["sha256"] == artifact.sha256


def test_t23_concurrent_dates_repeated_candidate_staging(offline, monkeypatch):
    manager, calls, install = offline
    monkeypatch.setattr(
        manager,
        "_candidate_urls",
        lambda _, day: [f"https://example.invalid/{day.isoformat()}.zip"],
    )
    install(
        lambda request: httpx.Response(
            200, content=archive(day=date.fromisoformat(request.url.path[1:-4]))
        )
    )

    def fetch(index):
        day = DAY + timedelta(days=index % 3)
        item = manager.download(KEY, day, use_cache=False)
        return item.path, item.path.read_bytes(), json.loads(item.manifest_path.read_text()), day

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(fetch, range(8)))
    assert len({r[0] for r in results}) == 3
    assert all(
        body == archive(day=day) and record["as_of"] == day.isoformat()
        for _, body, record, day in results
    )
    assert all(path.is_relative_to(manager.raw_root) for path, _, _, _ in results)


def probe_module():
    path = Path(__file__).resolve().parents[2] / "scripts/generate_source_probe_report.py"
    spec = spec_from_file_location("od02_probe", path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "status,reason",
    [
        (403, "HTTP_ACCESS_DENIED"),
        (429, "HTTP_RATE_LIMITED"),
        (302, "REDIRECT_NOT_ALLOWED"),
        (401, "HTTP_ACCESS_DENIED"),
        (451, "HTTP_ACCESS_DENIED"),
    ],
)
def test_t24_probe_bootstrap_terminal_and_redirect_budget(
    synthetic_source_policy_provider, monkeypatch, status, reason
):
    from omegadata.track_a.source_rights import authorize_source

    module = probe_module()
    monkeypatch.setattr(
        module,
        "authorize_source",
        lambda request: authorize_source(request, synthetic_source_policy_provider),
    )
    calls = []

    def runner(command, **kw):
        calls.append(command)
        Path(command[command.index("-D") + 1]).write_text(
            f"HTTP/1.1 {status} SYNTHETIC_TEST_ONLY\nRetry-After: 120\nLocation: https://foreign.invalid/\n"
        )
        Path(command[command.index("-o") + 1]).write_bytes(b"SYNTHETIC_TEST_ONLY")
        return SimpleNamespace(returncode=0)

    with pytest.raises(DownloadError, match=reason):
        module._curl_probe(
            source_key=KEY,
            url="https://example.invalid/file",
            timeout_seconds=1,
            bootstrap_nse=True,
            offline_runner=runner,
        )
    assert len(calls) == 1
    assert all(flag not in calls[0] for flag in ["-L", "--location", "--retry", "--insecure"])


def test_t24_probe_strict_validation_and_shared_budget(
    synthetic_source_policy_provider, monkeypatch
):
    from omegadata.track_a.source_rights import authorize_source

    module = probe_module()
    monkeypatch.setattr(
        module,
        "authorize_source",
        lambda request: authorize_source(request, synthetic_source_policy_provider),
    )
    body = [archive()]

    def runner(command, **kw):
        Path(command[command.index("-D") + 1]).write_text(
            "HTTP/1.1 200 OK\nContent-Type: application/zip\n"
        )
        Path(command[command.index("-o") + 1]).write_bytes(body[0])
        return SimpleNamespace(returncode=0)

    budget = RequestBudget(replace(load_limits(), max_attempts=2))
    result = module._probe_entry(
        source_key=KEY,
        as_of=DAY,
        url="https://example.invalid/file",
        role="primary",
        timeout_seconds=1,
        kind="zip",
        budget=budget,
        offline_runner=runner,
    )
    assert result["validated"] and result["request_attempts"] == 1 and result["body_preview"] == ""
    body[0] = b"<html>login</html>"
    with pytest.raises(DownloadError, match="PAYLOAD_HTML_DENIAL"):
        module._probe_entry(
            source_key=KEY,
            as_of=DAY,
            url="https://example.invalid/file",
            role="fallback",
            timeout_seconds=1,
            kind="zip",
            budget=budget,
            offline_runner=runner,
        )
    with pytest.raises(DownloadError, match="ATTEMPT_BUDGET_EXCEEDED"):
        module._curl_probe(
            source_key=KEY,
            url="https://example.invalid/file",
            timeout_seconds=1,
            budget=budget,
            offline_runner=runner,
        )


@pytest.mark.parametrize(
    "change",
    [
        {"max_attempts": 0},
        {"max_attempts": True},
        {"total_seconds": float("nan")},
        {"max_redirects": 1},
        {"backoff_seconds": (-1,)},
        {"body_bytes": -1},
    ],
)
def test_t19_configuration_fails_closed(change):
    with pytest.raises(ValueError):
        replace(load_limits(), **change)


def test_t19_missing_and_malformed_configuration(tmp_path):
    path = tmp_path / "absent.json"
    with pytest.raises(DownloadError, match="INVALID_ACQUISITION_LIMITS"):
        load_limits(path)
    path.write_text('{"max_attempts":1,"max_attempts":2}')
    with pytest.raises(DownloadError, match="INVALID_ACQUISITION_LIMITS"):
        load_limits(path)


def test_t16_tls_invalid_is_terminal_no_fallback(offline):
    manager, calls, install = offline
    install(
        lambda _: (_ for _ in ()).throw(
            httpx.ConnectError("CERTIFICATE_VERIFY_FAILED SYNTHETIC_TEST_ONLY")
        )
    )
    with pytest.raises(DownloadError, match="TLS_INVALID"):
        manager.download(KEY, DAY, use_cache=False)
    assert len(calls) == 1 and not manager.raw_root.exists()


@pytest.mark.parametrize(
    "options",
    [
        {"max_request_attempts": 0},
        {"max_request_attempts": -1},
        {"max_request_attempts": True},
        {"request_timeout_seconds": 0},
        {"request_timeout_seconds": -1},
        {"request_timeout_seconds": float("nan")},
    ],
)
def test_t19_public_invalid_overrides_refuse_before_transport(offline, options):
    manager, calls, install = offline
    install(lambda _: httpx.Response(200, content=archive()))
    with pytest.raises(DownloadError, match="INVALID_ACQUISITION_LIMITS"):
        manager.download(KEY, DAY, use_cache=False, **options)
    assert not calls and not manager.raw_root.exists()


def test_t22_urls_sanitized_and_seed_mode_distinct(offline, monkeypatch):
    manager, calls, install = offline
    install(lambda _: httpx.Response(200, content=archive()))
    monkeypatch.setattr(
        manager,
        "_candidate_urls",
        lambda *_: ["https://example.invalid/file.zip?token=SYNTHETIC_SECRET"],
    )
    artifact = manager.download(KEY, DAY, use_cache=False)
    assert artifact.used_url == "https://example.invalid/file.zip"
    assert "SYNTHETIC_SECRET" not in artifact.manifest_path.read_text()
    # Seed import uses a separate test-only tree, preserving the same exact bytes.
    import shutil

    shutil.copytree(manager.raw_root, manager.seed_raw_root)
    for manifest in manager.seed_raw_root.rglob("*.json"):
        payload = json.loads(manifest.read_text())
        payload["artifact_path"] = str(
            manager.seed_raw_root / Path(payload["artifact_path"]).relative_to(manager.raw_root)
        )
        manifest.write_text(json.dumps(payload))
    manager.raw_root = manager.raw_root.parent / "empty"
    cached = manager.download(KEY, DAY, cache_only=True)
    assert cached.source_mode == "source_seed_imported" and cached.sha256 == artifact.sha256
    assert len(calls) == 1
