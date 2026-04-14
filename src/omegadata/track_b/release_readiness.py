from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

from sqlalchemy.orm import Session

from omegadata.config import settings
from omegadata.db.models import ManualReviewQueue, ReprocessJob
from omegadata.track_b.review_policy import load_review_policies


@dataclass(frozen=True)
class ReadinessCheck:
    name: str
    passed: bool
    details: str


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return cast(dict[str, Any], payload)


def _probe_summary_score(payload: dict[str, Any]) -> tuple[int, int]:
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        return (0, 0)
    required = (
        "bse_primary_validated",
        "healthy_fallback_count",
        "failed_fallback_count",
    )
    present = sum(1 for key in required if key in summary)
    extra = len(summary)
    return (present, extra)


def _load_best_probe_artifact(repo_root: Path) -> tuple[dict[str, Any] | None, str | None]:
    candidates = [
        repo_root / "artifacts/verification/source_probe_report.json",
        repo_root / "artifacts/verification/source_probe_report_deterministic.json",
        repo_root / "artifacts/verification/source_probe_report_full.json",
    ]
    ranked: list[tuple[tuple[int, int, float], dict[str, Any], str]] = []
    for path in candidates:
        payload = _read_json(path)
        if payload is None:
            continue
        generated_at = payload.get("generated_at")
        try:
            generated_ts = datetime.fromisoformat(str(generated_at)).timestamp()
        except (TypeError, ValueError):
            generated_ts = 0.0
        summary_score = _probe_summary_score(payload)
        ranked.append(((summary_score[0], summary_score[1], generated_ts), payload, path.relative_to(repo_root).as_posix()))
    if not ranked:
        return None, None
    ranked.sort(key=lambda item: item[0], reverse=True)
    _, payload, path_str = ranked[0]
    return payload, path_str


def _load_policy() -> dict[str, Any]:
    path = (_repo_root() / settings.release_readiness_policy_path).resolve()
    if not path.exists():
        return {
            "max_open_blocking_reviews": 0,
            "max_overdue_blocking_reviews": 0,
            "max_pending_reprocess_jobs": 0,
            "probe_max_age_hours": 24,
            "tolerance_report_max_age_hours": 168,
            "matching_report_max_age_hours": 168,
            "require_calendar_loaded": True,
            "require_primary_probe_healthy": True,
            "minimum_healthy_fallbacks": 1,
            "minimum_official_cases": 10,
            "minimum_official_transformational_cases": 3,
            "minimum_manual_transformational_cases": 14,
        }
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


class ReleaseReadinessService:
    def evaluate(self, session: Session) -> dict[str, object]:
        policy = _load_policy()
        checks: list[ReadinessCheck] = []

        review_policies = load_review_policies()
        open_blocking = 0
        overdue_blocking = 0
        for review in session.query(ManualReviewQueue).all():
            category_policy = review_policies.for_category(review.category)
            if not category_policy.blocks_publication:
                continue
            payload = dict(review.payload or {})
            if not review.resolved:
                open_blocking += 1
            if bool(payload.get("sla_breached")):
                overdue_blocking += 1
        checks.append(
            ReadinessCheck(
                name="blocking_reviews",
                passed=open_blocking <= int(policy["max_open_blocking_reviews"]),
                details=f"open_blocking_reviews={open_blocking}",
            )
        )
        checks.append(
            ReadinessCheck(
                name="overdue_blocking_reviews",
                passed=overdue_blocking <= int(policy["max_overdue_blocking_reviews"]),
                details=f"overdue_blocking_reviews={overdue_blocking}",
            )
        )

        pending_jobs = session.query(ReprocessJob).filter(ReprocessJob.status.in_(("QUEUED", "RUNNING"))).count()
        checks.append(
            ReadinessCheck(
                name="pending_reprocess_jobs",
                passed=pending_jobs <= int(policy["max_pending_reprocess_jobs"]),
                details=f"pending_reprocess_jobs={pending_jobs}",
            )
        )

        repo_root = _repo_root()
        probe, probe_path = _load_best_probe_artifact(repo_root)
        tolerance = _read_json(repo_root / "artifacts/verification/cross_source_tolerance_report.json")
        matching = _read_json(repo_root / "artifacts/verification/corporate_action_matching_report.json")
        official_corpus = _read_json(repo_root / "tests/fixtures/official_source/adjustment_reference_corpus.json")
        manual_corpus = _read_json(repo_root / "tests/fixtures/synthetic_manual/adjustment_reference_hand_computed.json")

        checks.extend(
            [
                self._artifact_check(
                    name="source_probe_fresh",
                    artifact=probe,
                    max_age_hours=int(policy["probe_max_age_hours"]),
                ),
                self._artifact_check(
                    name="tolerance_report_fresh",
                    artifact=tolerance,
                    max_age_hours=int(policy["tolerance_report_max_age_hours"]),
                ),
                self._artifact_check(
                    name="matching_report_fresh",
                    artifact=matching,
                    max_age_hours=int(policy["matching_report_max_age_hours"]),
                ),
            ]
        )

        if probe is None:
            checks.append(ReadinessCheck("probe_health", False, "source_probe_report.json missing"))
        else:
            summary = probe.get("summary", {})
            calendar_loaded = probe.get("calendar_config_state") == "loaded"
            probe_path_details = f"probe_artifact_path={probe_path}"
            checks.append(
                ReadinessCheck(
                    name="calendar_loaded",
                    passed=(not bool(policy["require_calendar_loaded"])) or calendar_loaded,
                    details=f"{probe_path_details}, calendar_config_state={probe.get('calendar_config_state')}",
                )
            )
            checks.append(
                ReadinessCheck(
                    name="probe_primary_healthy",
                    passed=(not bool(policy["require_primary_probe_healthy"]))
                    or bool(summary.get("bse_primary_validated", False)),
                    details=f"{probe_path_details}, bse_primary_validated={summary.get('bse_primary_validated')}",
                )
            )
            checks.append(
                ReadinessCheck(
                    name="probe_fallback_health",
                    passed=int(summary.get("healthy_fallback_count", 0)) >= int(policy["minimum_healthy_fallbacks"]),
                    details=(
                        f"{probe_path_details}, "
                        f"healthy_fallback_count={summary.get('healthy_fallback_count', 0)}, "
                        f"failed_fallback_count={summary.get('failed_fallback_count', 0)}"
                    ),
                )
            )

        if tolerance is not None:
            checks.append(
                ReadinessCheck(
                    name="tolerance_status",
                    passed=tolerance.get("status") == "ok",
                    details=f"status={tolerance.get('status')}",
                )
            )
        if matching is not None:
            metrics = matching.get("metrics", {})
            checks.append(
                ReadinessCheck(
                    name="matching_benchmark_status",
                    passed=matching.get("status") == "ok" and bool(metrics.get("benchmark_passed", False)),
                    details=(
                        f"status={matching.get('status')}, "
                        f"precision={metrics.get('precision')}, recall={metrics.get('recall')}"
                    ),
                )
            )
        if official_corpus is not None:
            checks.append(
                ReadinessCheck(
                    name="official_adjustment_corpus",
                    passed=int(official_corpus.get("transformational_case_count", 0))
                    >= int(policy["minimum_official_transformational_cases"])
                    and int(official_corpus.get("case_count", 0)) >= int(policy["minimum_official_cases"]),
                    details=(
                        f"official_case_count={official_corpus.get('case_count', 0)}, "
                        f"official_transformational_case_count={official_corpus.get('transformational_case_count', 0)}"
                    ),
                )
            )
        if manual_corpus is not None:
            checks.append(
                ReadinessCheck(
                    name="manual_transformational_corpus",
                    passed=int(manual_corpus.get("case_count", 0))
                    >= int(policy["minimum_manual_transformational_cases"]),
                    details=f"manual_case_count={manual_corpus.get('case_count', 0)}",
                )
            )

        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "ready": all(check.passed for check in checks),
            "checks": [
                {"name": check.name, "passed": check.passed, "details": check.details}
                for check in checks
            ],
        }

    @staticmethod
    def _artifact_check(*, name: str, artifact: dict[str, object] | None, max_age_hours: int) -> ReadinessCheck:
        if artifact is None:
            return ReadinessCheck(name, False, "artifact missing")
        generated_at = artifact.get("generated_at")
        if not isinstance(generated_at, str):
            return ReadinessCheck(name, False, "artifact missing generated_at")
        generated_dt = datetime.fromisoformat(generated_at)
        max_age = timedelta(hours=max_age_hours)
        age = datetime.now(UTC) - generated_dt
        return ReadinessCheck(
            name=name,
            passed=age <= max_age,
            details=f"artifact_age_hours={age.total_seconds() / 3600:.2f}",
        )
