"""Bounded canonical probe edit; no source probe is executed by this script."""
from pathlib import Path

path = Path("scripts/generate_source_probe_report.py")
text = path.read_bytes().decode("utf-8")
start = text.index("def _curl_probe(")
end = text.index("def _validate_json(", start)
new = '''def _curl_probe(
    *, source_key: str, url: str, timeout_seconds: float,
    bootstrap_nse: bool = False, offline_runner=None, budget: RequestBudget | None = None,
) -> tuple[int | None, str, bytes, str | None]:
    """Only explicit offline runner injection is supported; no provider subprocess."""
    limits = load_limits()
    budget = budget or RequestBudget(limits)
    def preflight(target: str) -> None:
        authorize_source(PolicyRequest(
            source_key=source_key, operation=SourceOperation.FETCH,
            decision_at=datetime.now(UTC), requested_transport=SourceTransport.CURL,
            requested_host=policy_url_host(target),
        ))
    targets = ["https://www.nseindia.com/", url] if bootstrap_nse else [url]
    for target in targets:
        preflight(target)
    if offline_runner is None:
        raise failure("BLOCKED_EXTERNAL_EGRESS")
    budget.remaining()
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        result_body = b""
        status, content_type = None, ""
        for index, target in enumerate(targets):
            preflight(target)
            timeout = min(timeout_seconds, budget.consume())
            body_path, header_path = root / f"{index}.body", root / f"{index}.headers"
            command = ["curl", "--proto", "=https", "--max-redirs", "0", "--proxy", "",
                "--noproxy", "*", "--max-filesize", str(limits.body_bytes),
                "--max-time", str(timeout), "--connect-timeout", str(timeout),
                "-sS", "-D", str(header_path), "-o", str(body_path), "-A", USER_AGENT, target]
            result = offline_runner(command, check=False, capture_output=True, timeout=timeout + 1)
            budget.remaining()
            if result.returncode != 0:
                raise failure("HTTP_TRANSIENT", terminal=False)
            headers = {}
            status = None
            if not header_path.is_file():
                raise failure("PARTIAL_PAYLOAD")
            if header_path.stat().st_size > 65536:
                raise failure("BODY_LIMIT_EXCEEDED")
            for line in header_path.read_text(encoding="utf-8", errors="strict").splitlines():
                if line.startswith("HTTP/"):
                    status = int(line.split()[1])
                elif ":" in line:
                    name, value = line.split(":", 1)
                    headers[name.lower().strip()] = value.strip()
            check_status(status or 0, headers)
            if not body_path.is_file() or body_path.stat().st_size > limits.body_bytes:
                raise failure("BODY_LIMIT_EXCEEDED")
            with body_path.open("rb") as handle:
                result_body = handle.read(limits.body_bytes + 1)
            if not result_body or len(result_body) > limits.body_bytes:
                raise failure("PAYLOAD_EMPTY" if not result_body else "BODY_LIMIT_EXCEEDED")
            length = headers.get("content-length")
            if length is not None and (not length.isdigit() or int(length) != len(result_body)):
                raise failure("PARTIAL_PAYLOAD")
            if b"access denied" in result_body[:1024].lower() or b"captcha" in result_body[:1024].lower():
                raise failure("PAYLOAD_HTML_DENIAL")
            content_type = headers.get("content-type", "")
        return status, content_type, result_body, None


'''
text = text[:start] + new + text[end:]
text = text.replace("from omegadata.track_a.source_rights import (", "from omegadata.track_a.acquisition import RequestBudget, check_status, failure, load_limits, validate_payload\n\nfrom omegadata.track_a.source_rights import (")
path.write_bytes(text.encode("utf-8"))
