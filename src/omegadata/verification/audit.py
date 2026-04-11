from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class AuditItem:
    track: str
    component: str
    requirement: str
    status: str
    evidence: list[str]
    gaps: list[str]
    severity: str


CheckFn = Callable[[], list[str]]


def _existing_paths(paths: list[str]) -> list[str]:
    return [path for path in paths if (PROJECT_ROOT / path).exists()]


def _missing_paths(paths: list[str]) -> list[str]:
    return [path for path in paths if not (PROJECT_ROOT / path).exists()]


def _read_json(path: str) -> dict[str, object] | None:
    candidate = PROJECT_ROOT / path
    if not candidate.exists():
        return None
    return dict(json.loads(candidate.read_text(encoding="utf-8")))


def _reference_corpus_gaps() -> list[str]:
    corpus = _read_json("tests/fixtures/adjustment_reference_corpus.json")
    if corpus is None:
        return ["adjustment reference corpus fixture is missing"]

    cases = corpus.get("cases", [])
    if not isinstance(cases, list):
        return ["adjustment reference corpus cases payload is malformed"]

    declared_count = corpus.get("case_count")
    actual_count = len(cases)
    gaps: list[str] = []
    if declared_count != actual_count:
        gaps.append(
            f"reference corpus declares {declared_count} cases but contains {actual_count}"
        )
    if actual_count < 10:
        gaps.append(f"reference corpus has only {actual_count} official cases; expected at least 10")
    if any("label" not in case for case in cases if isinstance(case, dict)):
        gaps.append("reference corpus contains unlabeled cases")
    return gaps


def _pit_backfill_gaps() -> list[str]:
    report = _read_json("artifacts/verification/pit_universe_backfill_report.json")
    if report is None:
        return ["pit universe backfill report is missing"]

    validations = report.get("snapshot_validations", [])
    if not isinstance(validations, list) or not validations:
        return ["pit universe backfill report has no snapshot validations"]
    failed = [
        item for item in validations if isinstance(item, dict) and item.get("matched") is not True
    ]
    if failed:
        return [f"{len(failed)} PIT snapshot validations are not matched"]
    return []


def _build_item(
    *,
    track: str,
    component: str,
    requirement: str,
    evidence: list[str],
    checks: tuple[CheckFn, ...] = (),
) -> AuditItem:
    gaps = [f"missing evidence: {path}" for path in _missing_paths(evidence)]
    for check in checks:
        gaps.extend(check())

    status = "implemented" if not gaps else "partial"
    severity = "none" if not gaps else "medium"
    return AuditItem(
        track=track,
        component=component,
        requirement=requirement,
        status=status,
        evidence=_existing_paths(evidence),
        gaps=gaps,
        severity=severity,
    )


def build_audit_items() -> list[AuditItem]:
    return [
        _build_item(
            track="A",
            component="Data Source Registry",
            requirement="Multi-source registry with eras, URL patterns, checksums, partitioning metadata",
            evidence=["src/omegadata/track_a/source_registry.py"],
        ),
        _build_item(
            track="A",
            component="Download Manager",
            requirement="Retry/backoff, checksum verification, anti-bot handling, immutable raw artifact capture, official failover",
            evidence=[
                "src/omegadata/track_a/download_manager.py",
                "tests/integration/test_real_data_sources.py",
            ],
        ),
        _build_item(
            track="A",
            component="Orchestration",
            requirement="Airflow orchestration for daily and monthly jobs",
            evidence=[
                "airflow/dags/omegadata_pipeline.py",
                "airflow/dags/omegadata_monthly_quality.py",
            ],
        ),
        _build_item(
            track="A",
            component="API and Storage",
            requirement="FastAPI service and Parquet persistence",
            evidence=[
                "src/omegadata/api/main.py",
                "src/omegadata/track_a/storage.py",
            ],
        ),
        _build_item(
            track="A",
            component="Streaming and Caching",
            requirement="Kafka and Redis wiring",
            evidence=[
                "src/omegadata/track_a/kafka_bus.py",
                "src/omegadata/track_a/redis_cache.py",
            ],
        ),
        _build_item(
            track="A",
            component="24/7 Event Impact Pipeline",
            requirement="Bloomberg-style event taxonomy, impact scoring, decay, Redis output contract",
            evidence=[
                "src/omegadata/track_a/news_pipeline.py",
                "tests/unit/test_news_pipeline.py",
            ],
        ),
        _build_item(
            track="A",
            component="Ops and Monitoring",
            requirement="SLO dashboards, metrics, alert routing, monthly quality reports",
            evidence=[
                "src/omegadata/track_a/monitoring.py",
                "src/omegadata/track_a/slo.py",
                "src/omegadata/track_a/quality_reporting.py",
                "infra/monitoring/grafana/dashboards/omegadata_slo.json",
            ],
        ),
        _build_item(
            track="B",
            component="Component 1 ISIN Master",
            requirement="ISIN validation, temporal mapping, symbol change protocol, delisting records",
            evidence=[
                "src/omegadata/track_b/isin_master.py",
                "tests/unit/test_isin_master.py",
            ],
        ),
        _build_item(
            track="B",
            component="Component 2 Corporate Actions",
            requirement="Closed taxonomy, dual-source staging and confirmation, required field validation, immutable corrections",
            evidence=[
                "src/omegadata/track_b/corporate_actions.py",
                "src/omegadata/track_b/corporate_action_parser.py",
                "tests/unit/test_corporate_actions.py",
                "src/omegadata/track_a/collection_schedule.py",
                "airflow/dags/omegadata_corporate_actions_windows.py",
            ],
        ),
        _build_item(
            track="B",
            component="Component 3 Adjustment Engine",
            requirement="Backward adjustment, chain audit trail, Decimal precision, bonus/split/rights/demerger formulas",
            evidence=[
                "src/omegadata/track_b/adjustment_engine.py",
                "tests/unit/test_adjustment_engine.py",
                "tests/unit/test_adjustment_reference_corpus.py",
                "tests/fixtures/adjustment_reference_corpus.json",
                "scripts/build_adjustment_reference_corpus.py",
            ],
            checks=(_reference_corpus_gaps,),
        ),
        _build_item(
            track="B",
            component="Component 4 Discontinuity Detector",
            requirement="Idiosyncratic return detection with explicit market proxy and exclusion dates",
            evidence=[
                "src/omegadata/track_b/discontinuity.py",
                "tests/unit/test_discontinuity.py",
                "tests/unit/test_discontinuity_sector_fallback.py",
                "airflow/dags/omegadata_track_b_reaudit.py",
            ],
        ),
        _build_item(
            track="B",
            component="Component 5 PIT Universe",
            requirement="Knowledge/effective date semantics, reconstruction handling, delisting-aware queries",
            evidence=[
                "src/omegadata/track_b/universe_manager.py",
                "tests/unit/test_universe_manager.py",
                "tests/fixtures/pit_universe_seed_pack.json",
                "scripts/build_pit_universe_seed_pack.py",
                "scripts/backfill_pit_universe.py",
                "artifacts/verification/pit_universe_backfill_report.json",
            ],
            checks=(_pit_backfill_gaps,),
        ),
        _build_item(
            track="B",
            component="Component 6 Confidence",
            requirement="Deterministic deductions and hard API thresholds",
            evidence=[
                "src/omegadata/track_b/confidence.py",
                "src/omegadata/api/main.py",
                "tests/unit/test_confidence_and_validation.py",
            ],
        ),
        _build_item(
            track="B",
            component="Component 7 Cross-Source Validation",
            requirement="NSE/BSE validations, tolerance tiers, systematic disagreement escalation, audit logging",
            evidence=[
                "src/omegadata/track_b/cross_source_validation.py",
                "tests/unit/test_confidence_and_validation.py",
                "tests/unit/test_external_validation_jobs.py",
                "scripts/run_quarterly_secondary_validation.py",
                "airflow/dags/omegadata_quarterly_validation.py",
            ],
        ),
        _build_item(
            track="B",
            component="Reference Corpus",
            requirement="Official-source-backed corporate action reference corpus from bundled NSE artifacts",
            evidence=[
                "tests/unit/test_adjustment_engine.py",
                "tests/unit/test_adjustment_reference_corpus.py",
                "tests/fixtures/adjustment_reference_corpus.json",
                "scripts/build_adjustment_reference_corpus.py",
            ],
            checks=(_reference_corpus_gaps,),
        ),
    ]


def build_audit_summary() -> dict[str, object]:
    items = build_audit_items()
    counts = {"implemented": 0, "partial": 0, "missing": 0}
    severities = {"critical": 0, "high": 0, "medium": 0, "low": 0, "none": 0}

    for item in items:
        counts[item.status] = counts.get(item.status, 0) + 1
        severities[item.severity] = severities.get(item.severity, 0) + 1

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "counts": counts,
        "severity_counts": severities,
        "items": [asdict(item) for item in items],
    }
