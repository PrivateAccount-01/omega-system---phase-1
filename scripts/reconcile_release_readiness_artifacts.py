from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "config/release_readiness_policy.json"

READINESS_FILES = {
    "equity_core": REPO_ROOT / "artifacts/verification/release_readiness_equity_core.json",
    "equity_plus_sidefeeds": REPO_ROOT / "artifacts/verification/release_readiness_equity_plus_sidefeeds.json",
    "full_derivatives": REPO_ROOT / "artifacts/verification/release_readiness_full_derivatives.json",
}

FRESHNESS_ARTIFACTS = {
    "source_probe_fresh": REPO_ROOT / "artifacts/verification/source_probe_report.json",
    "pipeline_fresh": REPO_ROOT / "artifacts/verification/pipeline_execution_result.json",
    "tolerance_report_fresh": REPO_ROOT / "artifacts/verification/cross_source_tolerance_report.json",
    "matching_report_fresh": REPO_ROOT / "artifacts/verification/corporate_action_matching_report.json",
}


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _artifact_age_hours(path: Path) -> float | None:
    payload = _read_json(path)
    generated_at = payload.get("generated_at")
    if not isinstance(generated_at, str):
        return None
    try:
        generated = datetime.fromisoformat(generated_at)
    except ValueError:
        return None
    return (datetime.now(UTC) - generated).total_seconds() / 3600.0


def main() -> None:
    policy = _read_json(POLICY_PATH)
    thresholds = {
        "source_probe_fresh": int(policy.get("probe_max_age_hours", 24)),
        "pipeline_fresh": int(policy.get("pipeline_max_age_hours", 24)),
        "tolerance_report_fresh": int(policy.get("tolerance_report_max_age_hours", 168)),
        "matching_report_fresh": int(policy.get("matching_report_max_age_hours", 168)),
    }

    for profile, readiness_path in READINESS_FILES.items():
        readiness = _read_json(readiness_path)
        for check in readiness.get("checks", []):
            if not isinstance(check, dict):
                continue
            name = str(check.get("name"))
            artifact_path = FRESHNESS_ARTIFACTS.get(name)
            if artifact_path is None or not artifact_path.exists():
                continue
            age_hours = _artifact_age_hours(artifact_path)
            if age_hours is None:
                continue
            check["passed"] = age_hours <= thresholds[name]
            check["details"] = f"artifact_age_hours={age_hours:.2f}"
        readiness["generated_at"] = datetime.now(UTC).isoformat()
        readiness["ready"] = all(bool(check.get("passed")) for check in readiness.get("checks", []) if isinstance(check, dict))
        readiness_path.write_text(json.dumps(readiness, indent=2), encoding="utf-8")

        release_id = readiness.get("release_id")
        if not isinstance(release_id, str):
            continue
        quality_path = REPO_ROOT / "artifacts/releases" / release_id / "quality_report.json"
        if quality_path.exists():
            quality = _read_json(quality_path)
            quality["generated_at"] = datetime.now(UTC).isoformat()
            quality["release_readiness_snapshot"] = readiness
            quality_path.write_text(json.dumps(quality, indent=2), encoding="utf-8")

        if profile == "full_derivatives":
            (REPO_ROOT / "artifacts/verification/release_readiness.json").write_text(
                json.dumps(readiness, indent=2),
                encoding="utf-8",
            )

    print("Reconciled release readiness and quality artifacts")


if __name__ == "__main__":
    main()
