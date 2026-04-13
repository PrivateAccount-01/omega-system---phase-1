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

Release readiness is the canonical go/no-go surface for the repo’s operational trust posture.

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

## API Surface

Primary endpoints:

- `GET /health`
- `GET /metrics`
- `GET /slo/status`
- `GET /terminal`
- `GET /prices/{isin}`
- `GET /audit/prices/{isin}`
- `GET /universe/{index_name}`
- `GET /reviews/open`
- `POST /reviews/{review_id}/resolve`
- `POST /reviews/{review_id}/reprocess-complete`
- `GET /publication/status/{isin}`
- `GET /release/readiness`
- `GET /implementation/audit`
- `GET /implementation/test-results`

Internal endpoints should be protected with the configured API key and should not be treated as internet-facing by default.

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
python scripts/build_cross_source_tolerance_report.py
python scripts/build_corporate_action_matching_report.py
python scripts/check_trading_calendar_coverage.py
python scripts/build_release_readiness_report.py
python scripts/generate_implementation_audit.py
```

### Full Pipeline Smoke

```bash
python scripts/run_full_pipeline.py --days 10 --market-isin <ISIN>
```

## Current Operational Truth

The repo now includes enough instrumentation to answer these questions with artifacts rather than assumptions:

- Is the calendar loaded and current?
- Is the primary BSE bhavcopy path healthy?
- Are supported fallbacks merely covered, or actually healthy?
- Are tolerance thresholds calibrated and fresh?
- Is the corporate-action matcher benchmark passing?
- Are blocking reviews or reprocess jobs still open?
- Is release readiness currently green?

That is a much stronger position than “the tests passed once.”

## Honest Limits

OmegaData is materially stronger than a prototype, but it is still pre-production hardening.

Important honest boundaries:

- release readiness can still be red if the current DB contains unresolved blocking reviews
- official-source-backed transformational adjustment evidence is better than before but still limited by the bundled raw-source window
- reprocess orchestration is now evidence-backed and stateful, but it is still internal orchestration rather than a full external workflow engine
- live-source stability must continue to be monitored over time, not inferred forever from one green artifact run

That honesty is deliberate. The target is a trustworthy system, not a flattering README.
