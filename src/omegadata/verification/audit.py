from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class AuditItem:
    track: str
    component: str
    requirement: str
    status: str
    evidence: list[str]
    gaps: list[str]
    severity: str


def build_audit_items() -> list[AuditItem]:
    return [
        AuditItem(
            track="A",
            component="Data Source Registry",
            requirement="Multi-source registry with eras, URL patterns, checksums, partitioning metadata",
            status="implemented",
            evidence=[
                "src/omegadata/track_a/source_registry.py",
            ],
            gaps=[],
            severity="none",
        ),
        AuditItem(
            track="A",
            component="Download Manager",
            requirement="Retry/backoff, checksum verification, anti-bot handling, official failover",
            status="implemented",
            evidence=[
                "src/omegadata/track_a/download_manager.py",
                "tests/integration/test_real_data_sources.py",
            ],
            gaps=[],
            severity="none",
        ),
        AuditItem(
            track="A",
            component="Orchestration",
            requirement="Airflow orchestration for daily and monthly jobs",
            status="implemented",
            evidence=[
                "airflow/dags/omegadata_pipeline.py",
                "airflow/dags/omegadata_monthly_quality.py",
            ],
            gaps=[],
            severity="none",
        ),
        AuditItem(
            track="A",
            component="API and Storage",
            requirement="FastAPI service and Parquet persistence",
            status="implemented",
            evidence=[
                "src/omegadata/api/main.py",
                "src/omegadata/track_a/storage.py",
            ],
            gaps=[],
            severity="none",
        ),
        AuditItem(
            track="A",
            component="Streaming and Caching",
            requirement="Kafka and Redis wiring",
            status="implemented",
            evidence=[
                "src/omegadata/track_a/kafka_bus.py",
                "src/omegadata/track_a/redis_cache.py",
            ],
            gaps=[],
            severity="none",
        ),
        AuditItem(
            track="A",
            component="24/7 Event Impact Pipeline",
            requirement="Bloomberg-style event taxonomy, impact scoring, decay, Redis output contract",
            status="implemented",
            evidence=[
                "src/omegadata/track_a/news_pipeline.py",
                "tests/unit/test_news_pipeline.py",
            ],
            gaps=[],
            severity="none",
        ),
        AuditItem(
            track="A",
            component="Ops and Monitoring",
            requirement="SLO dashboards, metrics, alert routing, monthly quality reports",
            status="implemented",
            evidence=[
                "src/omegadata/track_a/monitoring.py",
                "src/omegadata/track_a/slo.py",
                "src/omegadata/track_a/quality_reporting.py",
                "infra/monitoring/grafana/dashboards/omegadata_slo.json",
            ],
            gaps=[],
            severity="none",
        ),
        AuditItem(
            track="B",
            component="Component 1 ISIN Master",
            requirement="ISIN validation, temporal mapping, symbol change protocol, delisting records",
            status="implemented",
            evidence=[
                "src/omegadata/track_b/isin_master.py",
                "tests/unit/test_isin_master.py",
            ],
            gaps=[],
            severity="none",
        ),
        AuditItem(
            track="B",
            component="Component 2 Corporate Actions",
            requirement="Closed taxonomy, dual-source staging and confirmation, required field validation, immutable corrections",
            status="implemented",
            evidence=[
                "src/omegadata/track_b/corporate_actions.py",
                "tests/unit/test_corporate_actions.py",
                "src/omegadata/track_a/collection_schedule.py",
                "airflow/dags/omegadata_corporate_actions_windows.py",
            ],
            gaps=[],
            severity="none",
        ),
        AuditItem(
            track="B",
            component="Component 3 Adjustment Engine",
            requirement="Backward adjustment, chain audit trail, Decimal precision, bonus/split/rights/demerger formulas",
            status="implemented",
            evidence=[
                "src/omegadata/track_b/adjustment_engine.py",
                "tests/unit/test_adjustment_engine.py",
                "tests/unit/test_adjustment_reference_corpus.py",
                "tests/fixtures/adjustment_reference_corpus.json",
                "scripts/build_adjustment_reference_corpus.py",
            ],
            gaps=[],
            severity="none",
        ),
        AuditItem(
            track="B",
            component="Component 4 Discontinuity Detector",
            requirement="Idiosyncratic return detection with beta fallback hierarchy and exclusion dates",
            status="implemented",
            evidence=[
                "src/omegadata/track_b/discontinuity.py",
                "tests/unit/test_discontinuity.py",
                "tests/unit/test_discontinuity_sector_fallback.py",
                "airflow/dags/omegadata_track_b_reaudit.py",
            ],
            gaps=[],
            severity="none",
        ),
        AuditItem(
            track="B",
            component="Component 5 PIT Universe",
            requirement="Knowledge/effective date semantics, reconstruction handling, delisting-aware queries",
            status="implemented",
            evidence=[
                "src/omegadata/track_b/universe_manager.py",
                "tests/unit/test_universe_manager.py",
                "tests/fixtures/pit_universe_seed_pack.json",
                "scripts/build_pit_universe_seed_pack.py",
                "scripts/backfill_pit_universe.py",
                "artifacts/verification/pit_universe_backfill_report.json",
            ],
            gaps=[],
            severity="none",
        ),
        AuditItem(
            track="B",
            component="Component 6 Confidence",
            requirement="Deterministic deductions and hard API thresholds",
            status="implemented",
            evidence=[
                "src/omegadata/track_b/confidence.py",
                "src/omegadata/api/main.py",
                "tests/unit/test_confidence_and_validation.py",
            ],
            gaps=[],
            severity="none",
        ),
        AuditItem(
            track="B",
            component="Component 7 Cross-Source Validation",
            requirement="NSE/BSE validations, tolerance tiers, systematic disagreement escalation, audit logging",
            status="implemented",
            evidence=[
                "src/omegadata/track_b/cross_source_validation.py",
                "tests/unit/test_confidence_and_validation.py",
                "tests/unit/test_external_validation_jobs.py",
                "scripts/run_quarterly_secondary_validation.py",
                "airflow/dags/omegadata_quarterly_validation.py",
            ],
            gaps=[],
            severity="none",
        ),
        AuditItem(
            track="B",
            component="Reference Corpus",
            requirement="12 hand-computed corporate action reference cases from NSE history",
            status="implemented",
            evidence=[
                "tests/unit/test_adjustment_engine.py",
                "tests/unit/test_adjustment_reference_corpus.py",
                "tests/fixtures/adjustment_reference_corpus.json",
                "scripts/build_adjustment_reference_corpus.py",
            ],
            gaps=[],
            severity="none",
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
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": counts,
        "severity_counts": severities,
        "items": [asdict(item) for item in items],
    }
