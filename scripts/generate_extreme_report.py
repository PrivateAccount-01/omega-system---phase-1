from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _read_json(path: Path) -> dict:
    raw = path.read_bytes()
    for encoding in ("utf-8", "utf-16", "utf-16-le", "utf-16-be"):
        try:
            return json.loads(raw.decode(encoding))
        except Exception:
            continue
    raise ValueError(f"Unable to decode JSON file: {path}")


def _read_json_optional(path: Path) -> dict | None:
    if not path.exists():
        return None
    return _read_json(path)


def _read_text(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8", "utf-16", "utf-16-le", "utf-16-be"):
        try:
            return raw.decode(encoding)
        except Exception:
            continue
    raise ValueError(f"Unable to decode text file: {path}")


def main() -> None:
    root = REPO_ROOT / "artifacts/verification"
    pipeline = _read_json_optional(root / "pipeline_execution_result.json")
    idempotency = _read_json(root / "idempotency_check.json")
    coverage = _read_json(root / "coverage_trackb.json")
    api_stress = _read_json(root / "api_stress_results.json")
    discontinuity_spike = _read_json_optional(root / "discontinuity_spike_report.json")
    release_readiness = _read_json_optional(root / "release_readiness.json")
    realdata_text = _read_text(root / "realdata_test_results.txt")
    unit_text = _read_text(root / "unit_test_results.txt")

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "pipeline_summary": None if pipeline is None else pipeline.get("summary", {}),
        "pipeline_failed_days": None if pipeline is None else len(pipeline.get("errors", [])),
        "pipeline_failure_examples": [] if pipeline is None else pipeline.get("errors", [])[:3],
        "pipeline_artifact_status": "missing" if pipeline is None else "present",
        "idempotency": {
            "delta_first": idempotency.get("delta_first", {}),
            "delta_second": idempotency.get("delta_second", {}),
            "run1_validations": idempotency.get("run1", {}).get("validations"),
            "run2_validations": idempotency.get("run2", {}).get("validations"),
        },
        "trackb_coverage": {
            "percent": coverage.get("totals", {}).get("percent_covered"),
            "covered_lines": coverage.get("totals", {}).get("covered_lines"),
            "num_statements": coverage.get("totals", {}).get("num_statements"),
        },
        "api_stress": api_stress,
        "release_readiness": None if release_readiness is None else {
            "ready": release_readiness.get("ready"),
            "failed_checks": [
                check for check in release_readiness.get("checks", [])
                if not bool(check.get("passed", False))
            ],
        },
        "discontinuity_reaudit": None if discontinuity_spike is None else {
            "source_existing_total_event_count": discontinuity_spike.get("source_summary", {}).get("existing_total_event_count"),
            "source_existing_duplicate_event_count": discontinuity_spike.get("source_summary", {}).get("existing_duplicate_event_count"),
            "persisted_event_count_after_reaudit": discontinuity_spike.get("persisted_event_count"),
            "top_spike_date": discontinuity_spike.get("top_spike_date"),
            "top_spike_market_return": discontinuity_spike.get("top_spike_market_return"),
            "analysis": discontinuity_spike.get("analysis"),
        },
        "realdata_tests": realdata_text,
        "unit_tests": unit_text,
    }

    out_path = root / "extreme_test_report.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(out_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
