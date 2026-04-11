from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


def _read_json(path: Path) -> dict:
    raw = path.read_bytes()
    for encoding in ("utf-8", "utf-16", "utf-16-le", "utf-16-be"):
        try:
            return json.loads(raw.decode(encoding))
        except Exception:
            continue
    raise ValueError(f"Unable to decode JSON file: {path}")


def _read_text(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8", "utf-16", "utf-16-le", "utf-16-be"):
        try:
            return raw.decode(encoding)
        except Exception:
            continue
    raise ValueError(f"Unable to decode text file: {path}")


def main() -> None:
    root = Path("artifacts/verification")
    pipeline = _read_json(root / "pipeline_execution_result.json")
    idempotency = _read_json(root / "idempotency_check.json")
    coverage = _read_json(root / "coverage_trackb.json")
    api_stress = _read_json(root / "api_stress_results.json")
    realdata_text = _read_text(root / "realdata_test_results.txt")
    unit_text = _read_text(root / "unit_test_results.txt")

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "pipeline_summary": pipeline.get("summary", {}),
        "pipeline_failed_days": len(pipeline.get("errors", [])),
        "pipeline_failure_examples": pipeline.get("errors", [])[:3],
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
        "realdata_tests": realdata_text,
        "unit_tests": unit_text,
    }

    out_path = root / "extreme_test_report.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(out_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
