from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from omegadata.config import settings
from omegadata.db.models import ManualReviewQueue, ReleaseRecord, ReprocessJob
from omegadata.domain import ReleaseProfile
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
            "pipeline_max_age_hours": 24,
            "tolerance_report_max_age_hours": 168,
            "matching_report_max_age_hours": 168,
            "require_pipeline_success": True,
            "max_failed_pipeline_days": 0,
            "require_calendar_loaded": True,
            "require_primary_probe_healthy": True,
            "require_nse_equity_probe_healthy": True,
            "minimum_healthy_fallbacks": 2,
            "minimum_official_cases": 10,
            "minimum_official_transformational_cases": 3,
            "minimum_manual_transformational_cases": 14,
            "release_max_age_hours": 24,
            "require_signature_verification": True,
            "profiles": {
                "equity_core": {
                    "required_datasets": ["adjusted_equity_bars", "pit_universe_snapshot"],
                    "require_warehouse_sync": True,
                    "require_non_empty_datasets": ["adjusted_equity_bars", "pit_universe_snapshot"],
                },
                "equity_plus_sidefeeds": {
                    "required_datasets": [
                        "adjusted_equity_bars",
                        "pit_universe_snapshot",
                        "fii_dii_daily",
                        "india_vix",
                        "benchmark_series",
                        "sector_series",
                    ],
                    "require_warehouse_sync": True,
                    "require_non_empty_datasets": [
                        "adjusted_equity_bars",
                        "pit_universe_snapshot",
                        "fii_dii_daily",
                        "india_vix",
                        "benchmark_series",
                        "sector_series",
                    ],
                },
                "full_derivatives": {
                    "required_datasets": [
                        "adjusted_equity_bars",
                        "pit_universe_snapshot",
                        "fii_dii_daily",
                        "india_vix",
                        "benchmark_series",
                        "sector_series",
                        "futures_contract_master",
                        "futures_eod",
                        "continuous_futures",
                        "options_contract_master",
                        "options_eod",
                    ],
                    "require_warehouse_sync": True,
                    "require_non_empty_datasets": [
                        "adjusted_equity_bars",
                        "pit_universe_snapshot",
                        "fii_dii_daily",
                        "india_vix",
                        "benchmark_series",
                        "sector_series",
                        "futures_contract_master",
                        "futures_eod",
                        "continuous_futures",
                        "options_contract_master",
                        "options_eod",
                    ],
                },
            },
        }
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


class ReleaseReadinessService:
    def evaluate(
        self,
        session: Session,
        *,
        profile: ReleaseProfile | None = None,
        release_id: str | None = None,
    ) -> dict[str, object]:
        policy = _load_policy()
        checks: list[ReadinessCheck] = []
        release_profile = profile or ReleaseProfile(settings.release_default_profile)
        release_record = self._resolve_release_record(session, profile=release_profile, release_id=release_id)
        checks.extend(
            self._release_checks(
                session,
                release_record=release_record,
                profile=release_profile,
                policy=policy,
            )
        )

        review_policies = load_review_policies()
        open_release_blocking = 0
        overdue_release_blocking = 0
        open_record_scoped_blocking = 0
        overdue_record_scoped_blocking = 0
        for review in session.query(ManualReviewQueue).all():
            category_policy = review_policies.for_category(review.category)
            if not category_policy.blocks_publication:
                continue
            payload = dict(review.payload or {})
            is_release_blocking = category_policy.scope.value != "RECORD"
            if not review.resolved:
                if is_release_blocking:
                    open_release_blocking += 1
                else:
                    open_record_scoped_blocking += 1
            if bool(payload.get("sla_breached")):
                if is_release_blocking:
                    overdue_release_blocking += 1
                else:
                    overdue_record_scoped_blocking += 1
        checks.append(
            ReadinessCheck(
                name="blocking_reviews",
                passed=open_release_blocking <= int(policy["max_open_blocking_reviews"]),
                details=(
                    f"open_release_blocking_reviews={open_release_blocking}, "
                    f"open_record_scoped_blocking_reviews={open_record_scoped_blocking}"
                ),
            )
        )
        checks.append(
            ReadinessCheck(
                name="overdue_blocking_reviews",
                passed=overdue_release_blocking <= int(policy["max_overdue_blocking_reviews"]),
                details=(
                    f"overdue_release_blocking_reviews={overdue_release_blocking}, "
                    f"overdue_record_scoped_blocking_reviews={overdue_record_scoped_blocking}"
                ),
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
        pipeline = _read_json(repo_root / "artifacts/verification/pipeline_execution_result.json")
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
                    name="pipeline_fresh",
                    artifact=pipeline,
                    max_age_hours=int(policy["pipeline_max_age_hours"]),
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
            checks.append(
                ReadinessCheck(
                    name="probe_nse_equity_healthy",
                    passed=(not bool(policy["require_nse_equity_probe_healthy"]))
                    or bool(summary.get("nse_equity_primary_validated", False)),
                    details=(
                        f"{probe_path_details}, "
                        f"nse_equity_primary_validated={summary.get('nse_equity_primary_validated')}"
                    ),
                )
            )

        if pipeline is None:
            checks.append(ReadinessCheck("pipeline_success", False, "pipeline_execution_result.json missing"))
        else:
            summary = cast(dict[str, Any], pipeline.get("summary", {}))
            failed_days = int(summary.get("failed_days", 0))
            successful_days = int(summary.get("successful_days", 0))
            checks.append(
                ReadinessCheck(
                    name="pipeline_success",
                    passed=(not bool(policy["require_pipeline_success"]))
                    or (successful_days > 0 and failed_days <= int(policy["max_failed_pipeline_days"])),
                    details=(
                        f"successful_days={successful_days}, "
                        f"failed_days={failed_days}"
                    ),
                )
            )

        if tolerance is not None:
            checks.append(
                ReadinessCheck(
                    name="tolerance_status",
                    passed=tolerance.get("status") == "ok" and bool(tolerance.get("benchmark_passed", False)),
                    details=(
                        f"status={tolerance.get('status')}, "
                        f"benchmark_passed={tolerance.get('benchmark_passed')}"
                    ),
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
            "release_profile": release_profile.value,
            "release_id": None if release_record is None else release_record.release_id,
            "ready": all(check.passed for check in checks),
            "checks": [
                {"name": check.name, "passed": check.passed, "details": check.details}
                for check in checks
            ],
        }

    def _resolve_release_record(
        self,
        session: Session,
        *,
        profile: ReleaseProfile,
        release_id: str | None,
    ) -> ReleaseRecord | None:
        if release_id:
            return session.scalar(select(ReleaseRecord).where(ReleaseRecord.release_id == release_id))
        return session.scalar(
            select(ReleaseRecord)
            .where(ReleaseRecord.release_profile == profile)
            .order_by(ReleaseRecord.generated_at.desc())
        )

    def _release_checks(
        self,
        session: Session,
        *,
        release_record: ReleaseRecord | None,
        profile: ReleaseProfile,
        policy: dict[str, Any],
    ) -> list[ReadinessCheck]:
        checks: list[ReadinessCheck] = []
        profiles = cast(dict[str, Any], policy.get("profiles", {}))
        profile_policy = cast(dict[str, Any], profiles.get(profile.value, {}))
        if release_record is None:
            return [ReadinessCheck("release_record_present", False, f"no release found for profile {profile.value}")]

        checks.append(
            ReadinessCheck(
                name="release_record_present",
                passed=True,
                details=f"release_id={release_record.release_id}",
            )
        )

        repo_root = _repo_root()
        manifest_path = repo_root / release_record.manifest_path
        signature_path = None if release_record.signature_path is None else repo_root / release_record.signature_path
        quality_path = repo_root / release_record.quality_report_path
        lineage_path = repo_root / release_record.lineage_report_path
        checks.append(
            ReadinessCheck(
                name="release_artifacts_present",
                passed=manifest_path.exists() and quality_path.exists() and lineage_path.exists(),
                details=(
                    f"manifest_exists={manifest_path.exists()}, "
                    f"quality_exists={quality_path.exists()}, "
                    f"lineage_exists={lineage_path.exists()}"
                ),
            )
        )
        checks.append(
            ReadinessCheck(
                name="release_signature_present",
                passed=signature_path is not None and signature_path.exists(),
                details=f"signature_exists={False if signature_path is None else signature_path.exists()}",
            )
        )
        checks.append(
            self._artifact_check(
                name="release_manifest_fresh",
                artifact=_read_json(manifest_path),
                max_age_hours=int(policy["release_max_age_hours"]),
            )
        )

        if bool(policy.get("require_signature_verification", False)) and signature_path is not None and signature_path.exists():
            from omegadata.track_b.release_manager import ReleaseManager

            verified, details = ReleaseManager().verify_signature(manifest_path, signature_path)
            checks.append(ReadinessCheck("release_signature_verified", verified, details))

        manifest = _read_json(manifest_path) or {}
        dataset_entries = cast(list[dict[str, Any]], manifest.get("dataset_entries", []))
        datasets = {str(entry.get("dataset_name", "")): entry for entry in dataset_entries}
        required_datasets = [str(item) for item in profile_policy.get("required_datasets", [])]
        missing = [name for name in required_datasets if name not in datasets]
        checks.append(
            ReadinessCheck(
                name="release_required_datasets_present",
                passed=not missing,
                details=f"missing_datasets={missing}",
            )
        )
        non_empty_datasets = [str(item) for item in profile_policy.get("require_non_empty_datasets", [])]
        empty = [name for name in non_empty_datasets if int(datasets.get(name, {}).get("row_count", 0)) <= 0]
        checks.append(
            ReadinessCheck(
                name="release_required_datasets_non_empty",
                passed=not empty,
                details=f"empty_datasets={empty}",
            )
        )

        require_warehouse_sync = bool(profile_policy.get("require_warehouse_sync", False))
        checks.append(
            ReadinessCheck(
                name="warehouse_sync_status",
                passed=(not require_warehouse_sync) or release_record.warehouse_sync_status == "SYNCED",
                details=f"warehouse_sync_status={release_record.warehouse_sync_status}",
            )
        )

        matrix = release_record.consumer_matrix or {}
        checks.append(
            ReadinessCheck(
                name="consumer_matrix_present",
                passed=bool(matrix.get("allowed_consumer_classes")) and bool(matrix.get("allowed_signal_families")),
                details=f"consumer_classes={len(cast(list[object], matrix.get('allowed_consumer_classes', [])))}, signal_families={len(cast(list[object], matrix.get('allowed_signal_families', [])))}",
            )
        )

        if "adjusted_equity_bars" in datasets:
            checks.append(self._adjusted_ohlcv_check(repo_root, datasets["adjusted_equity_bars"]))
        return checks

    @staticmethod
    def _adjusted_ohlcv_check(repo_root: Path, dataset_entry: dict[str, Any]) -> ReadinessCheck:
        storage_path = repo_root / str(dataset_entry.get("storage_path", ""))
        if not storage_path.exists():
            return ReadinessCheck("adjusted_ohlcv_complete", False, f"dataset_missing={storage_path.as_posix()}")
        frame = pd.read_parquet(storage_path)
        if frame.empty:
            return ReadinessCheck("adjusted_ohlcv_complete", False, "adjusted_equity_bars empty")
        required_cols = [
            "adjusted_open_price",
            "adjusted_high_price",
            "adjusted_low_price",
            "adjusted_close_price",
            "adjusted_volume",
        ]
        missing_cols = [column for column in required_cols if column not in frame.columns]
        if missing_cols:
            return ReadinessCheck("adjusted_ohlcv_complete", False, f"missing_columns={missing_cols}")
        null_counts = {column: int(frame[column].isna().sum()) for column in required_cols}
        passed = all(count == 0 for count in null_counts.values())
        return ReadinessCheck(
            "adjusted_ohlcv_complete",
            passed,
            ", ".join(f"{column}_nulls={count}" for column, count in null_counts.items()),
        )

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
