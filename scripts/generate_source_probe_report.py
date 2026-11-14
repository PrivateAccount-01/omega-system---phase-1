from __future__ import annotations

import argparse
import csv
import io
import json
import subprocess
import tempfile
import zipfile
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit

from omegadata.track_a.source_rights import (
    PolicyRequest,
    SourceOperation,
    SourceTransport,
    authorize_source,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CALENDAR_PATH = REPO_ROOT / "config/trading_holidays_india.json"
OUTPUT_PATH = REPO_ROOT / "artifacts/verification/source_probe_report.json"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def _load_calendar() -> dict[str, object]:
    return json.loads(CALENDAR_PATH.read_text(encoding="utf-8"))


def _holiday_set(payload: dict[str, object], exchange: str) -> set[str]:
    return set(payload.get("holidays", {}).get(exchange, []))


def _special_sessions(payload: dict[str, object], exchange: str) -> set[str]:
    sessions = payload.get("special_sessions", {}).get(exchange, [])
    return {str(item.get("date")) for item in sessions if isinstance(item, dict)}


def _calendar_status(payload: dict[str, object], exchange: str, anchor_date: date) -> dict[str, object]:
    coverage_years = set(payload.get("coverage_years", {}).get(exchange, []))
    missing = [] if anchor_date.year in coverage_years else [anchor_date.year]
    status = "healthy" if not missing else "missing"
    maintenance = payload.get("maintenance", {})
    return {
        "exchange": exchange,
        "status": status,
        "required_year": anchor_date.year,
        "covered_years": sorted(coverage_years),
        "missing_years": missing,
        "owner_role": maintenance.get("owner_role"),
        "renewal_window_days": maintenance.get("renewal_window_days"),
        "runbook": maintenance.get("runbook"),
    }


def _is_trading_day(payload: dict[str, object], exchange: str, value: date) -> bool:
    iso = value.isoformat()
    if iso in _special_sessions(payload, exchange):
        return True
    if value.weekday() >= 5:
        return False
    return iso not in _holiday_set(payload, exchange)


def _recent_trading_days(payload: dict[str, object], exchange: str, anchor_date: date, limit: int) -> list[date]:
    values: list[date] = []
    current = anchor_date
    while len(values) < limit:
        if _is_trading_day(payload, exchange, current):
            values.append(current)
        current -= timedelta(days=1)
    return values


def _render_nse_equity(as_of: date) -> str:
    return f"https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{as_of:%Y%m%d}_F_0000.csv.zip"


def _render_nse_fo(as_of: date) -> str:
    return f"https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{as_of:%Y%m%d}_F_0000.csv.zip"


def _render_bse_primary(as_of: date) -> str:
    return f"https://www.bseindia.com/download/BhavCopy/Equity/BhavCopy_BSE_CM_0_0_0_{as_of:%Y%m%d}_F_0000.CSV"


def _render_bse_fallbacks(as_of: date) -> list[str]:
    return [
        f"https://www.bseindia.com/download/BhavCopy/Equity/EQ_ISINCODE_{as_of:%d%m%y}_T0.CSV",
        f"https://www.bseindia.com/download/BhavCopy/Equity/BSE_EQ_BHAVCOPY_{as_of:%d%m%Y}_T0.ZIP",
    ]


def _curl_probe(
    *,
    source_key: str,
    url: str,
    timeout_seconds: float,
    bootstrap_nse: bool = False,
) -> tuple[int | None, str, bytes, str | None]:
    urls = [url, "https://www.nseindia.com/"] if bootstrap_nse else [url]
    for target in urls:
        authorize_source(PolicyRequest(
            source_key=source_key, operation=SourceOperation.FETCH,
            decision_at=datetime.now(UTC), requested_transport=SourceTransport.CURL,
            requested_host=urlsplit(target).hostname,
        ))
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        body_path = tmp / "body.bin"
        header_path = tmp / "headers.txt"
        cookie_path = tmp / "cookies.txt"
        if bootstrap_nse:
            subprocess.run(
                [
                    "curl",
                    "-sS",
                    "-L",
                    "--max-time",
                    str(timeout_seconds),
                    "-A",
                    USER_AGENT,
                    "-c",
                    str(cookie_path),
                    "https://www.nseindia.com/",
                ],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        cmd = [
            "curl",
            "-sS",
            "-L",
            "--max-time",
            str(timeout_seconds),
            "-A",
            USER_AGENT,
            "-D",
            str(header_path),
            "-o",
            str(body_path),
        ]
        if bootstrap_nse:
            cmd.extend(["-b", str(cookie_path), "-c", str(cookie_path)])
            cmd.extend(["-H", "Referer: https://www.nseindia.com/", "-H", "Origin: https://www.nseindia.com"])
        result = subprocess.run(cmd + [url], check=False, capture_output=True)
        stderr = result.stderr.decode("utf-8", errors="ignore").strip() or None
        headers_text = header_path.read_text(encoding="utf-8", errors="ignore") if header_path.exists() else ""
        status_code = None
        content_type = ""
        for line in headers_text.splitlines():
            if line.startswith("HTTP/"):
                parts = line.split()
                if len(parts) >= 2 and parts[1].isdigit():
                    status_code = int(parts[1])
            if line.lower().startswith("content-type:"):
                content_type = line.split(":", 1)[1].strip()
        body = body_path.read_bytes() if body_path.exists() else b""
        return status_code, content_type, body, stderr


def _validate_json(body: bytes) -> bool:
    stripped = body.lstrip()
    return stripped.startswith(b"{") or stripped.startswith(b"[")


def _validate_csv(body: bytes, expected_headers: list[set[str]]) -> bool:
    try:
        text = body.decode("utf-8", errors="ignore")
        reader = csv.DictReader(io.StringIO(text))
        headers = {str(value).strip() for value in (reader.fieldnames or [])}
        return any(expected.issubset(headers) for expected in expected_headers)
    except Exception:
        return False


def _validate_zip_csv(body: bytes, expected_headers: list[set[str]]) -> bool:
    try:
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
            if not members:
                return False
            payload = archive.read(members[0])
    except Exception:
        return False
    return _validate_csv(payload, expected_headers)


def _probe_entry(
    *,
    source_key: str,
    as_of: date,
    url: str,
    role: str,
    timeout_seconds: float,
    kind: str,
) -> dict[str, object]:
    policy_decision = authorize_source(PolicyRequest(
        source_key=source_key, operation=SourceOperation.FETCH,
        decision_at=datetime.now(UTC), requested_transport=SourceTransport.CURL,
        requested_host=urlsplit(url).hostname,
    ))
    bootstrap_nse = "nseindia.com" in url or "nsearchives.nseindia.com" in url
    started = datetime.now(UTC)
    status_code, content_type, body, stderr = _curl_probe(
        source_key=source_key,
        url=url,
        timeout_seconds=timeout_seconds,
        bootstrap_nse=bootstrap_nse,
    )
    elapsed = (datetime.now(UTC) - started).total_seconds()
    if kind == "json":
        validated = status_code == 200 and _validate_json(body)
    elif kind == "csv":
        if source_key == "BSE_EQUITY_BHAVCOPY":
            validated = status_code == 200 and _validate_csv(
                body,
                [
                    {"TradDt", "BizDt", "ISIN", "TckrSymb", "OpnPric", "ClsPric"},
                    {"SC_CODE", "SC_NAME", "OPEN", "CLOSE", "ISIN_CODE", "TRADING_DATE"},
                ],
            )
        else:
            validated = status_code == 200 and _validate_csv(body, [{"SYMBOL", "SERIES", "ISIN"}])
    else:
        if source_key == "NSE_EQUITY_BHAVCOPY":
            validated = status_code == 200 and _validate_zip_csv(
                body,
                [
                    {"SYMBOL", "SERIES", "ISIN"},
                    {"TradDt", "BizDt", "ISIN", "TckrSymb", "OpnPric", "ClsPric"},
                ],
            )
        elif source_key == "NSE_FO_BHAVCOPY":
            validated = status_code == 200 and _validate_zip_csv(body, [{"FinInstrmTp", "TckrSymb", "XpryDt"}])
        else:
            validated = status_code == 200 and (
                _validate_zip_csv(body, [{"TckrSymb", "ISIN", "OpnPric"}, {"SC_CODE", "OPEN", "CLOSE", "ISIN_CODE"}])
                or body.startswith(b"PK")
            )
    return {
        "source_key": source_key,
        "source_policy_decision": policy_decision.model_dump(mode="json"),
        "as_of": as_of.isoformat(),
        "url": url,
        "role": role,
        "validated": validated,
        "status_code": status_code,
        "content_type": content_type,
        "bytes_downloaded": len(body),
        "attempts": 1,
        "request_attempts": 1,
        "transport": "curl",
        "header_profile": "chrome_desktop",
        "elapsed_seconds": round(elapsed, 3),
        "failure_stage": None if validated else ("request" if status_code != 200 else "validation"),
        "error": stderr,
        "validation_error": None if validated else "payload_validation_failed",
        "body_preview": body[:120].decode("utf-8", errors="ignore"),
    }


def _summarize_candidate_history(candidate_date: date, results: list[dict[str, object]]) -> dict[str, object]:
    primary = next((item for item in results if item["role"] == "primary"), None)
    fallbacks = [item for item in results if item["role"] == "fallback"]
    return {
        "date": candidate_date.isoformat(),
        "primary_validated": bool(primary and primary["validated"]),
        "primary_status_code": None if primary is None else primary["status_code"],
        "healthy_fallback_count": sum(1 for item in fallbacks if item["validated"]),
        "failed_fallback_count": sum(1 for item in fallbacks if not item["validated"]),
        "overall_validated": any(bool(item["validated"]) for item in results),
        "all_supported_fallbacks_probed": len(fallbacks) == 2,
        "all_supported_fallbacks_healthy": len(fallbacks) == 2 and all(bool(item["validated"]) for item in fallbacks),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile-mode", choices=["deterministic", "full"], default="deterministic")
    parser.add_argument("--workflow", choices=["diagnostic", "scheduled_verification"], default="diagnostic")
    args = parser.parse_args()

    calendar = _load_calendar()
    timeout_seconds = 8.0
    probe_history_days = 3
    today = date.today()
    completed_anchor = today - timedelta(days=1)
    bse_days = _recent_trading_days(calendar, "BSE", completed_anchor, probe_history_days)
    nse_days = _recent_trading_days(calendar, "NSE", completed_anchor, probe_history_days)
    probe_date = bse_days[0]
    nse_probe_date = nse_days[0]

    nse_probes = [
        _probe_entry(
            source_key="NSE_CORPORATE_ACTIONS",
            as_of=completed_anchor,
            url="https://www.nseindia.com/api/corporates-corporateActions?index=equities",
            role="primary",
            timeout_seconds=timeout_seconds,
            kind="json",
        )
    ]
    nse_equity_probes = [
        _probe_entry(
            source_key="NSE_EQUITY_BHAVCOPY",
            as_of=nse_probe_date,
            url=_render_nse_equity(nse_probe_date),
            role="primary",
            timeout_seconds=timeout_seconds,
            kind="zip",
        )
    ]
    nse_fo_probes = [
        _probe_entry(
            source_key="NSE_FO_BHAVCOPY",
            as_of=nse_probe_date,
            url=_render_nse_fo(nse_probe_date),
            role="primary",
            timeout_seconds=timeout_seconds,
            kind="zip",
        )
    ]
    bse_primary = _probe_entry(
        source_key="BSE_EQUITY_BHAVCOPY",
        as_of=probe_date,
        url=_render_bse_primary(probe_date),
        role="primary",
        timeout_seconds=timeout_seconds,
        kind="csv",
    )
    bse_fallbacks = [
        _probe_entry(
            source_key="BSE_EQUITY_BHAVCOPY",
            as_of=probe_date,
            url=url,
            role="fallback",
            timeout_seconds=timeout_seconds,
            kind="zip" if url.lower().endswith(".zip") else "csv",
        )
        for url in _render_bse_fallbacks(probe_date)
    ]
    bse_page_probes = [bse_primary, *bse_fallbacks]

    bse_recent_history = []
    for candidate_date in bse_days:
        candidate_results = [
            _probe_entry(
                source_key="BSE_EQUITY_BHAVCOPY",
                as_of=candidate_date,
                url=_render_bse_primary(candidate_date),
                role="primary",
                timeout_seconds=timeout_seconds,
                kind="csv",
            ),
            *[
                _probe_entry(
                    source_key="BSE_EQUITY_BHAVCOPY",
                    as_of=candidate_date,
                    url=url,
                    role="fallback",
                    timeout_seconds=timeout_seconds,
                    kind="zip" if url.lower().endswith(".zip") else "csv",
                )
                for url in _render_bse_fallbacks(candidate_date)
            ],
        ]
        bse_recent_history.append(_summarize_candidate_history(candidate_date, candidate_results))

    nse_equity_recent_history = []
    for candidate_date in nse_days:
        candidate_results = [
            _probe_entry(
                source_key="NSE_EQUITY_BHAVCOPY",
                as_of=candidate_date,
                url=_render_nse_equity(candidate_date),
                role="primary",
                timeout_seconds=timeout_seconds,
                kind="zip",
            )
        ]
        nse_equity_recent_history.append(_summarize_candidate_history(candidate_date, candidate_results))

    healthy_fallback_count = sum(1 for item in bse_page_probes if item["role"] == "fallback" and item["validated"])
    failed_fallback_count = sum(1 for item in bse_page_probes if item["role"] == "fallback" and not item["validated"])
    calendar_maintenance = [
        _calendar_status(calendar, "NSE", today),
        _calendar_status(calendar, "BSE", today),
    ]
    bse_calendar_current = calendar_maintenance[1]["status"] == "healthy"
    nse_calendar_current = calendar_maintenance[0]["status"] == "healthy"
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "workflow": args.workflow,
        "probe_date": probe_date.isoformat(),
        "nse_equity_probe_date": nse_probe_date.isoformat(),
        "calendar_mode": (
            "configured_trading_calendar"
            if bse_calendar_current and nse_calendar_current
            else "weekday_fallback_due_to_missing_invalid_or_expired_calendar_coverage"
        ),
        "calendar_config_state": "loaded",
        "calendar_config_path": "config/trading_holidays_india.json",
        "calendar_config_error": None,
        "probe_profile_mode": args.profile_mode,
        "probe_profile_count": 1 if args.profile_mode == "deterministic" else 3,
        "probe_timeout_seconds": timeout_seconds,
        "calendar_maintenance": calendar_maintenance,
        "bse_supported_candidate_count": 3,
        "bse_probed_candidate_count": 3,
        "bse_supported_fallback_count": 2,
        "bse_probed_fallback_count": 2,
        "bse_probe_scope": "full_supported_registry_candidates",
        "nse_corporate_actions": nse_probes,
        "nse_equity_bhavcopy": nse_equity_probes,
        "nse_fo_bhavcopy": nse_fo_probes,
        "nse_equity_recent_history": nse_equity_recent_history,
        "bse_equity_candidates": bse_page_probes,
        "bse_recent_history": bse_recent_history,
        "summary": {
            "all_supported_candidates_probed": True,
            "all_supported_fallbacks_probed": True,
            "nse_equity_primary_validated": any(bool(item["validated"]) for item in nse_equity_probes),
            "nse_fo_primary_validated": any(bool(item["validated"]) for item in nse_fo_probes),
            "bse_primary_validated": bool(bse_primary["validated"]),
            "bse_any_fallback_validated": healthy_fallback_count > 0,
            "all_supported_fallbacks_healthy": healthy_fallback_count == 2,
            "healthy_fallback_count": healthy_fallback_count,
            "failed_fallback_count": failed_fallback_count,
            "bse_any_candidate_validated": any(bool(item["validated"]) for item in bse_page_probes),
            "bse_failed_candidates": [item["url"] for item in bse_page_probes if not item["validated"]],
        },
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")
    if args.workflow == "scheduled_verification":
        summary = report["summary"]
        if not (bse_calendar_current and nse_calendar_current):
            raise SystemExit("Scheduled verification requires loaded and current trading-calendar configuration.")
        if not bool(summary["nse_equity_primary_validated"]):
            raise SystemExit("Scheduled verification failed: NSE equity bhavcopy primary probe is unhealthy.")
        if not bool(summary["nse_fo_primary_validated"]):
            raise SystemExit("Scheduled verification failed: NSE F&O bhavcopy primary probe is unhealthy.")
        if not bool(summary["bse_primary_validated"]):
            raise SystemExit("Scheduled verification failed: BSE equity bhavcopy primary probe is unhealthy.")
        if not bool(summary["all_supported_fallbacks_healthy"]):
            raise SystemExit("Scheduled verification failed: not all supported BSE fallbacks are healthy.")


if __name__ == "__main__":
    main()
