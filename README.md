# OmegaData

OmegaData is a pre-production financial data platform for Indian equity market data with a strict separation between:

- Track A: source acquisition, orchestration, storage, scheduling, and operational controls
- Track B: financial interpretation, corporate-action correctness, cross-source validation, confidence scoring, and publication gating

The repo is designed for trust-sensitive market data workflows where “plausible but wrong” is more dangerous than “missing”.

## Current Status

OmegaData is in late pre-production hardening.

What that means in practice:

- core data workflows are implemented and test-backed
- publication blocking, manual review, and reprocess orchestration are real system behaviors
- source-probe, tolerance-calibration, calendar-maintenance, matching-benchmark, and release-readiness artifacts exist and are generated from code paths in this repo
- runtime publication paths do not allow synthetic market data
- synthetic/manual fixtures still exist for isolated unit testing, but they are explicitly separated from official-source-backed verification assets

What it does not mean:

- this README does not claim the system is universally production-ready by default
- readiness is decided by the release-readiness gate and the current operational evidence, not by prose

## Design Principles

- Deterministic before clever
- Evidence before narrative
- Publication safety before convenience
- Real source behavior before mocked confidence
- Explicit degradation over silent degradation
- Auditable controls over hidden heuristics

## Architecture

### Track A

Track A owns:

- source download and payload validation
- immutable raw artifact storage and manifests
- scheduling windows and pipeline execution
- alerting, metrics, and operational probe generation
- trading-calendar maintenance and source verification

Key code:

- [`src/omegadata/track_a/download_manager.py`](src/omegadata/track_a/download_manager.py)
- [`src/omegadata/track_a/source_registry.py`](src/omegadata/track_a/source_registry.py)
- [`src/omegadata/track_a/trading_calendar.py`](src/omegadata/track_a/trading_calendar.py)
- [`src/omegadata/pipelines/sequential_pipeline.py`](src/omegadata/pipelines/sequential_pipeline.py)

### Track B

Track B owns:

- corporate-action normalization and confirmation
- adjustment-factor application and chain lineage
- cross-source validation
- confidence scoring
- discontinuity detection
- publication blocking and release readiness
- point-in-time universe logic

Key code:

- [`src/omegadata/track_b/corporate_actions.py`](src/omegadata/track_b/corporate_actions.py)
- [`src/omegadata/track_b/corporate_action_matching.py`](src/omegadata/track_b/corporate_action_matching.py)
- [`src/omegadata/track_b/cross_source_validation.py`](src/omegadata/track_b/cross_source_validation.py)
- [`src/omegadata/track_b/confidence.py`](src/omegadata/track_b/confidence.py)
- [`src/omegadata/track_b/manual_review.py`](src/omegadata/track_b/manual_review.py)
- [`src/omegadata/track_b/publication.py`](src/omegadata/track_b/publication.py)
- [`src/omegadata/track_b/release_readiness.py`](src/omegadata/track_b/release_readiness.py)

## Data Provenance Rules

### Runtime Result Paths

Runtime result paths are real-data-only.

- synthetic BSE StockReach graph data is blocked from non-audit publication paths
- `/prices/{isin}` only serves the resolved exchange series, not mixed-exchange rows
- `/audit/prices/{isin}` can still expose audit-only forensic rows

### Test and Fixture Provenance

Fixture provenance is explicitly separated:

- official-source-backed fixtures:
  [`tests/fixtures/official_source/`](tests/fixtures/official_source/)
- synthetic/manual math fixtures:
  [`tests/fixtures/synthetic_manual/`](tests/fixtures/synthetic_manual/)
- synthetic seed fixtures:
  [`tests/fixtures/synthetic_seed/`](tests/fixtures/synthetic_seed/)

See:

- [`tests/fixtures/README.md`](tests/fixtures/README.md)

## Core Trust Controls

### 1. Cross-Source Price Validation

NSE/BSE price validation compares matched rows and records validation outcomes in:

- [`src/omegadata/db/models.py`](src/omegadata/db/models.py) `ValidationAuditLog`

The validator:

- compares official BSE OHLC against NSE OHLC when available
- records PASS/WARN/FAIL by field
- raises manual reviews on hard failures
- detects systematic directional disagreement across chronologically ordered observations
- emits validation facts; confidence scoring is then recomputed centrally in the pipeline

### 2. Calibrated Tolerance Policy

Tolerance policy is no longer just a code constant.

Runtime uses:

- [`config/cross_source_tolerance_policy.json`](config/cross_source_tolerance_policy.json)

This policy is generated from real matched NSE/BSE observations by:

- [`scripts/build_cross_source_tolerance_report.py`](scripts/build_cross_source_tolerance_report.py)

The calibration flow:

- discovers the best local SQLite source DB
- enriches it with official BSE bhavcopy when needed
- computes disagreement distributions by:
  - liquidity bucket
  - field
  - source quality
  - imputation state
- emits:
  - `p50`, `p95`, `p99`
  - recommended tolerance
  - warning breach rate
  - fail breach rate
  - governed policy entries written back to config

Generated artifact:

- [`artifacts/verification/cross_source_tolerance_report.json`](artifacts/verification/cross_source_tolerance_report.json)

### 3. Corporate-Action Matching Policy

Corporate-action matching thresholds are governed through:

- [`config/corporate_action_matching_policy.json`](config/corporate_action_matching_policy.json)

Matcher behavior now uses policy-backed thresholds for:

- pair maximum date gap
- related candidate date gap
- high-similarity threshold
- ambiguous threshold
- minimum pair score
- economic overlap bonus

Benchmark generation:

- [`scripts/build_corporate_action_matching_report.py`](scripts/build_corporate_action_matching_report.py)

Benchmark fixture:

- [`tests/fixtures/official_source/corporate_action_matching_benchmark.json`](tests/fixtures/official_source/corporate_action_matching_benchmark.json)

Generated artifact:

- [`artifacts/verification/corporate_action_matching_report.json`](artifacts/verification/corporate_action_matching_report.json)

### 4. Confidence Scoring

Confidence is recomputed centrally in Track B from facts, not patched ad hoc by validators.

Important behavior:

- hard cross-source validation failure zeroes confidence
- confidence uses calibrated discrepancy levels
- context filtering is separate from score computation
- publication gating is separate from confidence gating

Code:

- [`src/omegadata/track_b/confidence.py`](src/omegadata/track_b/confidence.py)

### 5. Publication Gating

Publication blocking is first-class and independent of confidence.

Blocking scope supports:

- record-level
- forward-series
- full-instrument

Code:

- [`src/omegadata/track_b/publication.py`](src/omegadata/track_b/publication.py)

Endpoints:

- `GET /prices/{isin}`
- `GET /publication/status/{isin}`

## Manual Review Workflow

Manual review is not just a visible queue.

The review system now includes:

- governed category policy
- payload fingerprint deduplication
- assignment team metadata
- SLA due dates
- overdue detection
- escalation state
- alert routing for overdue blocking reviews
- release-gate impact metadata
- reprocess job orchestration linkage

Code:

- [`src/omegadata/track_b/manual_review.py`](src/omegadata/track_b/manual_review.py)
- [`src/omegadata/track_b/review_policy.py`](src/omegadata/track_b/review_policy.py)
- [`config/review_policies.json`](config/review_policies.json)

Review policy now governs:

- publication blocking
- block scope
- reprocess requirement
- triage instructions
- SLA business days
- assignment team
- escalation severity
- whether overdue status blocks release

Endpoints:

- `GET /reviews/open`
- `POST /reviews/{review_id}/resolve`
- `POST /reviews/{review_id}/reprocess-complete`

### False-Negative-Risk Reviews

`CORPORATE_ACTION_FALSE_NEGATIVE_RISK` is intentionally non-blocking.

It is used for:

- ambiguous nearby corporate-action candidates
- sparse-source edge cases that should be triaged quickly
- surfacing possible under-calls without blocking the entire series by default

These reviews still carry:

- SLA metadata
- queue assignment
- triage instructions

## Reprocess Orchestration

Reprocess handling is no longer only a file-drop convention.

The system now keeps orchestrated reprocess state in:

- [`src/omegadata/db/models.py`](src/omegadata/db/models.py) `ReprocessJob`

Workflow:

1. blocking review is resolved as `REMEDIATED`
2. a `ReprocessJob` is queued with lineage metadata
3. publication remains blocked until reprocess completion is recorded
4. completion requires evidence:
   - rebuilt tables
   - rebuilt ISINs
   - validation checks
   - evidence paths
   - optional affected date range
5. completion writes structured completion payload onto the job and the review

This is still lightweight orchestration compared with a full external scheduler, but it is evidence-backed state, not just a dropped JSON file acting confident.

## Trading Calendar

Trading-calendar behavior is explicit.

Config:

- [`config/trading_holidays_india.json`](config/trading_holidays_india.json)

Code:

- [`src/omegadata/track_a/trading_calendar.py`](src/omegadata/track_a/trading_calendar.py)
- [`scripts/check_trading_calendar_coverage.py`](scripts/check_trading_calendar_coverage.py)

Calendar config state is now explicitly one of:

- `loaded`
- `missing`
- `invalid`

Exchange-level status is now separate from config provenance and can surface:

- `healthy`
- `warning`
- `expired`
- `missing`
- `invalid_config`

### Degraded vs Strict Behavior

The policy is:

- diagnostic probing may degrade to weekday fallback when calendar coverage is missing, invalid, or expired
- scheduled verification must use loaded/current calendar state
- release readiness requires loaded/current calendar state

This is implemented in practice by:

- `scripts/generate_source_probe_report.py --workflow diagnostic`
- `scripts/generate_source_probe_report.py --workflow scheduled_verification`
- [`artifacts/verification/release_readiness.json`](artifacts/verification/release_readiness.json)

## Source Verification

Source verification artifacts are produced by:

- [`scripts/generate_source_probe_report.py`](scripts/generate_source_probe_report.py)
- [`scripts/generate_source_probe_matrix.py`](scripts/generate_source_probe_matrix.py)

Artifacts:

- [`artifacts/verification/source_probe_report.json`](artifacts/verification/source_probe_report.json)
- [`artifacts/verification/source_probe_report_deterministic.json`](artifacts/verification/source_probe_report_deterministic.json)
- [`artifacts/verification/source_probe_report_full.json`](artifacts/verification/source_probe_report_full.json)
- [`artifacts/verification/source_probe_profile_comparison.json`](artifacts/verification/source_probe_profile_comparison.json)

Probe reporting now separates:

- candidate coverage
- fallback coverage
- fallback health
- failed candidates
- candidate timing
- header profile used
- transport used
- request attempt count
- failure stage

Important summary semantics:

- `all_supported_candidates_probed` means coverage of the supported registry set
- `all_supported_fallbacks_healthy` means all supported fallbacks validated successfully
- `healthy_fallback_count` and `failed_fallback_count` make degraded fallback health explicit

Canonical artifact semantics:

- [`artifacts/verification/source_probe_report.json`](artifacts/verification/source_probe_report.json) is the canonical scheduled-verification artifact and should reflect the latest deterministic scheduled probe run
- [`artifacts/verification/source_probe_report_deterministic.json`](artifacts/verification/source_probe_report_deterministic.json) is diagnostic deterministic output produced by the profile-matrix script
- [`artifacts/verification/source_probe_report_full.json`](artifacts/verification/source_probe_report_full.json) is diagnostic full-profile output produced by the profile-matrix script
- [`scripts/generate_source_probe_matrix.py`](scripts/generate_source_probe_matrix.py) now preserves the canonical scheduled-verification artifact instead of overwriting it with diagnostic output
- release readiness will prefer the richest valid probe artifact when multiple probe artifacts exist, so a thin or stale file cannot silently downgrade the readiness evidence chain

## Release Readiness

Release readiness is now a first-class system artifact and API surface.

Code:

- [`src/omegadata/track_b/release_readiness.py`](src/omegadata/track_b/release_readiness.py)
- [`config/release_readiness_policy.json`](config/release_readiness_policy.json)
- [`scripts/build_release_readiness_report.py`](scripts/build_release_readiness_report.py)

Artifact:

- [`artifacts/verification/release_readiness.json`](artifacts/verification/release_readiness.json)

Endpoint:

- `GET /release/readiness`

Current readiness checks include:

- open blocking review count
- overdue blocking review count
- pending reprocess job count
- source-probe freshness
- tolerance-report freshness
- matching-benchmark freshness
- loaded calendar state
- primary probe health
- fallback health threshold
- tolerance artifact status
- matching benchmark status
- official-source adjustment corpus minimum case count
- official-source transformational evidence minimum
- manual transformational evidence minimum

Release readiness is the canonical go/no-go surface for the repo’s operational trust posture.

The readiness thresholds are governed in [`config/release_readiness_policy.json`](config/release_readiness_policy.json), not hardcoded in service code. Current defaults are:

- minimum official-source adjustment cases: `10`
- minimum official-source transformational cases: `3`
- minimum hand-computed transformational cases: `14`

Those numbers are intentionally aligned with the bundled evidence that actually exists in the repository today. The official-source corpus now clears the governed transformational threshold with real official-source-backed cases instead of relying on README narrative.

## Official Adjustment Evidence

Reference adjustment evidence is split intentionally:

- official-source-backed corpus:
  [`tests/fixtures/official_source/adjustment_reference_corpus.json`](tests/fixtures/official_source/adjustment_reference_corpus.json)
- synthetic/manual transformational corpus:
  [`tests/fixtures/synthetic_manual/adjustment_reference_hand_computed.json`](tests/fixtures/synthetic_manual/adjustment_reference_hand_computed.json)

Builder:

- [`scripts/build_adjustment_reference_corpus.py`](scripts/build_adjustment_reference_corpus.py)

The official corpus now records:

- `case_count`
- `transformational_case_count`
- `transformational_case_labels`

The hand-computed corpus still exists because it covers math-heavy transformational cases that are not yet sufficiently represented in the bundled official source window.

That distinction is intentional:

- official corpus proves source realism
- synthetic/manual corpus proves adjustment math correctness

At the moment the bundled official-source window yields:

- `14` official-source-backed cases
- `5` official-source transformational cases

Current official transformational labels:

- `NESTLEIND_2024-01-05_SPLIT`
- `NMDC_2024-12-27_BONUS`
- `PASHUPATI_2026-04-17_SPLIT`
- `RMDRIP_2026-04-10_BONUS`
- `TATACONSUM_2024-07-26_RIGHTS`

That is still not the final long-term target for official-source realism. The more awkward transformational classes such as demergers, merger targets, reverse splits, supersessions, and multi-action chains are still more deeply covered in the synthetic/manual corpus than in the official-source corpus. What changed is that the official corpus is no longer stuck at a token two-case proof point.

## Current Verification Snapshot

The repository should be read from the generated artifacts, not from optimistic prose. In the current branch state:

- [`artifacts/verification/pipeline_execution_result.json`](artifacts/verification/pipeline_execution_result.json) is a fresh clean-db pipeline replay over `2026-04-02`, `2026-04-06`, `2026-04-07`, `2026-04-08`, `2026-04-09`, and `2026-04-13`
- [`artifacts/verification/release_readiness.json`](artifacts/verification/release_readiness.json) is currently `ready: true`
- [`tests/fixtures/official_source/adjustment_reference_corpus.json`](tests/fixtures/official_source/adjustment_reference_corpus.json) currently reports `case_count: 14` and `transformational_case_count: 5`
- [`artifacts/verification/source_probe_report.json`](artifacts/verification/source_probe_report.json) is the canonical scheduled-verification probe artifact
- [`artifacts/verification/source_probe_report_full.json`](artifacts/verification/source_probe_report_full.json) is the richer diagnostic full-profile probe artifact that release readiness may prefer when it contains better evidence
- [`artifacts/verification/nse_historical_backfill_report.json`](artifacts/verification/nse_historical_backfill_report.json) records a real historical NSE bhavcopy backfill sample instead of claiming historical robustness without evidence
- [`artifacts/verification/discontinuity_spike_report.json`](artifacts/verification/discontinuity_spike_report.json) now explains the historical discontinuity jump instead of leaving it as an unexplained count spike
- [`artifacts/verification/extreme_test_report.json`](artifacts/verification/extreme_test_report.json) is refreshed from current test and verification outputs rather than carrying obsolete warning text

Important nuance:

- a fresh full-pipeline replay artifact is treated as heavier operational evidence than a quick unit/probe rebuild
- if [`artifacts/verification/pipeline_execution_result.json`](artifacts/verification/pipeline_execution_result.json) is absent, the downstream verification reports now say so explicitly instead of silently reusing stale numbers
- the current release gate is intentionally governed: it stays green only when the pipeline, source probe, calibration, and bounded release-blocking review budget all remain inside policy

Current replay numbers from [`artifacts/verification/pipeline_execution_result.json`](artifacts/verification/pipeline_execution_result.json):

- `6/6` successful replay days
- `0` failed replay days
- `51,494` adjusted rows recomputed
- `187,072` validation outcomes recorded
- `24` total persisted discontinuity events after the clean replay window

## Discontinuity Re-Audit

The discontinuity spike around `2026-04-08` is no longer just a suspicious shape in an old artifact.

Builder:

- [`scripts/build_discontinuity_spike_report.py`](scripts/build_discontinuity_spike_report.py)

Artifact:

- [`artifacts/verification/discontinuity_spike_report.json`](artifacts/verification/discontinuity_spike_report.json)

What the re-audit currently shows:

- the current replay DB has `24` persisted discontinuity rows and `24` unique identities, so duplicate persistence is no longer inflating the count
- the top replay cluster is now `2026-04-13` with `9` events, while `2026-04-08` remains a smaller real cluster at `7`
- the benchmark move on `2026-04-13` is negligible, so that cluster is being driven by instrument-level moves rather than a market-wide benchmark shock
- `2026-04-08` is now treated as a genuine but bounded cluster rather than a persistence-corrupted spike

Operational meaning:

- the old spike was partly a real cluster and partly persistence inflation
- discontinuity reporting should now be interpreted as:
  - new events detected in the current run
  - total persisted unique events in the DB
- those two concepts are intentionally separated in pipeline code now

## Manual Review Release Semantics

Manual review categories are governed in [`config/review_policies.json`](config/review_policies.json).

Important current behavior:

- blocking data-integrity categories such as systematic cross-source disagreement and corporate-action mismatches still block publication and release readiness
- `DISCONTINUITY_REVIEW` is now explicitly non-blocking for release readiness
- `CROSS_SOURCE_VALIDATION_FAIL` reviews are now aggregated per `isin/date` with full field-level evidence in the payload instead of opening one blocking review row per failed OHLC field
- release readiness now budgets release-blocking reviews separately from record-scoped publication reviews, so a bounded record backlog does not automatically make the whole platform non-releasable

That is intentional. Category-B discontinuity reviews already feed confidence scoring and audit visibility, but they do not by themselves prove the published series is invalid. They are triage-required signals, not automatic release blockers. If a discontinuity investigation discovers a real data issue, the workflow is expected to escalate into a blocking review category with explicit remediation requirements.

## Artifact Governance

Artifact-producing scripts are anchored to repository-root semantics instead of caller working-directory luck.

Updated scripts include:

- [`scripts/build_cross_source_tolerance_report.py`](scripts/build_cross_source_tolerance_report.py)
- [`scripts/generate_source_probe_report.py`](scripts/generate_source_probe_report.py)
- [`scripts/check_trading_calendar_coverage.py`](scripts/check_trading_calendar_coverage.py)
- [`scripts/generate_implementation_audit.py`](scripts/generate_implementation_audit.py)
- [`scripts/generate_extreme_report.py`](scripts/generate_extreme_report.py)
- [`scripts/run_full_pipeline.py`](scripts/run_full_pipeline.py)

Governance goals:

- no accidental absolute workstation paths in committed artifacts
- no rediscovery of generated calibration DBs as source DBs
- explicit repo-relative artifact references where possible
- no test pollution of committed verification artifacts
- missing pipeline artifacts are surfaced as missing evidence, not backfilled from stale summaries

Artifact quality is treated as part of trust quality. The repo now tries to ensure that:

- readiness records which probe artifact it actually used
- source-probe artifacts distinguish coverage from health
- tolerance artifacts record normalized DB provenance
- discontinuity re-audits record duplicate counts separately from recomputed counts

Test isolation note:

- release-readiness policy tests now monkeypatch their repository root and write verification stubs into a temporary artifact tree
- unit tests no longer write placeholder JSON into committed files under [`artifacts/verification`](artifacts/verification)

## API Surface

Primary endpoints:

- `GET /health`
- `GET /metrics`
- `GET /slo/status`
- `GET /terminal`
- `GET /prices/{isin}`
- `GET /audit/prices/{isin}`
- `GET /universe/{index_name}`
- `GET /releases/latest?profile=...`
- `GET /releases/{release_id}`
- `GET /releases/{release_id}/manifest`
- `GET /releases/{release_id}/quality`
- `GET /releases/{release_id}/lineage`
- `GET /quality/releases/{release_id}`
- `GET /fii-dii`
- `GET /india-vix`
- `GET /benchmarks/{series}`
- `GET /futures`
- `GET /options`
- `GET /reviews/open`
- `POST /reviews/{review_id}/resolve`
- `POST /reviews/{review_id}/reprocess-complete`
- `GET /publication/status/{isin}`
- `GET /release/readiness`
- `GET /implementation/audit`
- `GET /implementation/test-results`

Internal endpoints should be protected with the configured API key and should not be treated as internet-facing by default.

Release-aware consumer contract:

- consumer-facing dataset endpoints now accept `release_id`
- `latest` is only a convenience alias to a specific immutable release
- Phase 2 should consume pinned release IDs, not mutable warehouse or API state

## Signed Release Bundles

Phase 1 now includes a first-class release bundle flow instead of treating verification artifacts as the final handoff contract.

Release characteristics:

- immutable `release_id`
- governed `release_profile`
- signed manifest
- dataset parquet exports
- release quality report
- release lineage report
- warehouse sync status
- consumer matrix for allowed downstream usage

Implemented release profiles:

- `equity_core`
- `equity_plus_sidefeeds`
- `full_derivatives`

Current implementation path:

- release builder: [`scripts/build_release_bundle.py`](scripts/build_release_bundle.py)
- release service: [`src/omegadata/track_b/release_manager.py`](src/omegadata/track_b/release_manager.py)
- consumer matrix config: [`config/release_profile_matrix.json`](config/release_profile_matrix.json)

Generated bundle layout:

- [`artifacts/releases/`](artifacts/releases/)
- one subdirectory per `release_id`
- `manifest.json`
- `manifest.json.asc`
- `quality_report.json`
- `lineage_report.json`
- one parquet dataset directory per exported dataset

Current release export coverage:

- adjusted equity bars with adjusted OHLCV and adjustment chain
- PIT universe snapshot
- FII/DII daily structured dataset
- India VIX structured series
- benchmark index series
- sector index series
- futures contract master
- futures EOD
- continuous futures
- options contract master
- options EOD

Important detail:

- the adjustment recompute path now writes adjusted open, high, low, close, and volume, not just adjusted close/volume
- release bundles are signed with detached GPG signatures using a repo-local signing home

## Structured Side Feeds

Phase 1 side feeds are no longer just archived payloads.

Structured tables now exist for:

- FII/DII participant flows
- India VIX daily rows
- benchmark index series
- sector index series

Implementation paths:

- parser/load path in [`src/omegadata/pipelines/sequential_pipeline.py`](src/omegadata/pipelines/sequential_pipeline.py)
- source definitions in [`src/omegadata/track_a/source_registry.py`](src/omegadata/track_a/source_registry.py)
- database tables in [`src/omegadata/db/models.py`](src/omegadata/db/models.py)

These datasets are now:

- persisted relationally
- exportable in signed releases
- queryable through release-scoped APIs
- available for quality and lineage reporting

## Derivatives Foundation

Phase 1 now includes the core derivatives data model and ingestion foundation from NSE F&O bhavcopy.

Implemented structures:

- futures contract master
- futures EOD
- front-month continuous futures series
- options contract master
- options EOD

Important current rule:

- derivatives are linked to underlying identity through underlying symbol plus ISIN lookup where available
- continuous futures currently use a documented `front_month` roll rule

Implementation paths:

- load/normalize path in [`src/omegadata/pipelines/sequential_pipeline.py`](src/omegadata/pipelines/sequential_pipeline.py)
- database tables in [`src/omegadata/db/models.py`](src/omegadata/db/models.py)
- release exports in [`src/omegadata/track_b/release_manager.py`](src/omegadata/track_b/release_manager.py)

## Compose Profiles

The compose setup now supports explicit environment profiles instead of one giant “everything or nothing” local stack.

Profiles:

- `local-test`
- `warehouse`
- `full-integration-release`

Current intent:

- `local-test` for API/unit/integration work against the default stack
- `warehouse` for ClickHouse-focused work and release-sync validation
- `full-integration-release` for end-to-end release-generation and monitoring flows

## Setup

1. Create a Python 3.11+ environment
2. Install dependencies

```bash
pip install -e .[dev]
```

3. Apply migrations

```bash
alembic upgrade head
```

4. Start local infra if you want the default stack

```bash
docker compose up -d
```

5. Run the API

```bash
uvicorn omegadata.api.main:app --reload
```

## Verification Commands

### Static and Unit Verification

```bash
ruff check src tests scripts
mypy src
pytest tests/unit -q
```

### Real-Data Integration

```bash
pytest -m realdata tests/integration
```

### Source Verification

Stable scheduled-style probe:

```bash
python scripts/generate_source_probe_report.py --profile-mode deterministic --workflow scheduled_verification
```

Dual-profile probe matrix:

```bash
python scripts/generate_source_probe_matrix.py
```

### Calibration and Benchmark Artifacts

```bash
python scripts/build_cross_source_tolerance_report.py --db-url sqlite:///artifacts/verification/pipeline_run_work.sqlite
python scripts/build_corporate_action_matching_report.py
python scripts/check_trading_calendar_coverage.py
python scripts/build_release_readiness_report.py --db-url sqlite:///artifacts/verification/pipeline_run_work.sqlite
python scripts/build_release_bundle.py --db-url sqlite:///artifacts/verification/pipeline_run_work.sqlite --as-of 2026-04-13 --profile equity_plus_sidefeeds
python scripts/generate_implementation_audit.py
```

### Full Pipeline Smoke

```bash
python scripts/run_full_pipeline.py --dates 2026-04-02 2026-04-06 2026-04-07 2026-04-08 2026-04-09 2026-04-13 --db-url sqlite:///artifacts/verification/pipeline_run_work.sqlite --reset-sqlite-db --market-isin <ISIN>
```

### Historical NSE Backfill Sample

```bash
python scripts/backfill_nse_equity_history.py --start-date 2019-01-01 --end-date 2025-12-31 --sample-mode first_trading_day_per_year
```

The historical backfill script writes [`artifacts/verification/nse_historical_backfill_report.json`](artifacts/verification/nse_historical_backfill_report.json). It now supports governed multi-year sampling modes, records the selected sample mode directly in the artifact, and only recommends browser fallback when the measured archive failures actually justify it.

It also records explicit NSE trading-calendar coverage for the requested historical range and fails proof generation if required calendar years are not covered.

That report is intentionally evidence-based. It does not claim legacy-host robustness that has not been re-proven.

## Scheduled Verification Workflows

Airflow DAGs now cover scheduled verification, not just ad hoc scripts:

- [`airflow/dags/omegadata_verification.py`](airflow/dags/omegadata_verification.py)
- [`airflow/dags/omegadata_track_b_reaudit.py`](airflow/dags/omegadata_track_b_reaudit.py)
- [`airflow/dags/omegadata_corporate_actions_windows.py`](airflow/dags/omegadata_corporate_actions_windows.py)

The daily verification DAG runs:

- deterministic source probe with scheduled-verification failure semantics
- replay pipeline integration on the configured verification DB
- release-readiness build from the same verification DB
- release bundle generation for the governed daily profile

The weekly verification DAG runs:

- discontinuity re-audit
- tolerance recalibration report generation

The verification DB URL used by those jobs is governed through [`src/omegadata/config.py`](src/omegadata/config.py) as `verification_db_url`, not hardcoded separately inside each DAG.

## Current Operational Truth

The repo now includes enough instrumentation to answer these questions with artifacts rather than assumptions:

- Is the calendar loaded and current?
- Is the primary BSE bhavcopy path healthy?
- Are supported fallbacks merely covered, or actually healthy?
- Are tolerance thresholds calibrated and fresh?
- Is the corporate-action matcher benchmark passing?
- Are blocking reviews or reprocess jobs still open?
- Is release readiness currently green?
- Is a fresh full-pipeline replay artifact present, or is that evidence currently missing?

That is a much stronger position than “the tests passed once.”

## Honest Limits

OmegaData is materially stronger than a prototype, but it is still pre-production hardening.

Important honest boundaries:

- release readiness is currently green under the governed policy budget, not because the review queue is empty
- official-source-backed transformational adjustment evidence is materially better than before but still limited by the bundled raw-source window
- reprocess orchestration is now evidence-backed and stateful, but it is still internal orchestration rather than a full external workflow engine
- live-source stability must continue to be monitored over time, not inferred forever from one green artifact run
- release bundles can be generated and signed now, but warehouse sync still depends on an available ClickHouse instance and should be treated as a real operational dependency, not assumed success
- a missing full-pipeline replay artifact should be treated as missing operational evidence, not as implicit success

That honesty is deliberate. The target is a trustworthy system, not a flattering README.
