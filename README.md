# OmegaData

OmegaData is a pre-production financial data platform for Indian equity market data with strict specification-driven behavior for corporate action handling, confidence scoring, point-in-time universes, and cross-source validation.

Default transactional backend is PostgreSQL and schema lifecycle is managed through Alembic migrations.

## Build Principles

- Track A: infrastructure and operational pipeline components.
- Track B: deterministic financial data correctness components.
- Real data only for strategy-quality integration checks.
- No hidden logic: all critical transformations are auditable.

## Quick Start

1. Create a Python 3.11+ environment.
2. Install dependencies:

```bash
pip install -e .[dev]
```

3. Run unit tests:

```bash
pytest tests/unit
```

4. Run real-data integration tests (network required):

```bash
pytest -m realdata tests/integration
```

5. Generate a live-source probe artifact for operational verification:

```bash
python scripts/generate_source_probe_report.py
```

6. Run API server:

```bash
uvicorn omegadata.api.main:app --reload
```

7. Apply database migrations:

```bash
alembic upgrade head
```

8. Start local infrastructure stack:

```bash
docker compose up -d
```

## Structure

- `src/omegadata/track_a`: ingestion, orchestration, storage, infra wiring.
- `src/omegadata/track_b`: ISIN master, CA system, adjustment engine, discontinuity, universe, confidence, validation.
- `src/omegadata/pipelines`: sequential integration pipeline.
- `airflow/dags`: scheduler definitions.
- `infra/clickhouse`: DDL for analytics warehouse.
- `alembic`: PostgreSQL schema migrations.
- `infra/monitoring`: Prometheus, Alertmanager, and Grafana provisioning.

## Maturity

- This repo is in pre-production hardening, not claimed production-grade trust infrastructure.
- Unit and integration tests are meaningful, but live-source robustness must be proven by recurring external probe artifacts and operational review.
- Internal verification endpoints are intended for controlled environments and should be protected behind API access.

## Operations

- Prometheus metrics endpoint: `GET /metrics`
- SLO status endpoint: `GET /slo/status`
- Bloomberg-style terminal UI: `GET /terminal`
- Implementation audit endpoint: `GET /implementation/audit`
- Test evidence endpoint: `GET /implementation/test-results`
- Monthly quality report DAG: `omegadata_monthly_quality_report`
- Manual monthly report generation:

```bash
python scripts/run_monthly_quality_report.py --as-of 2026-04-07
```

## Review Handling

- `CORPORATE_ACTION_FALSE_NEGATIVE_RISK` is a non-blocking triage queue, not a passive metric.
- Reviewers should inspect the nearby candidate within one business day, decide whether it is the same economic event, and either close it as `FALSE_POSITIVE` or escalate it into a blocking corporate-action review category with notes.
- The review payload carries `triage_instructions` from governed policy so operators can see the expected handling steps directly in the queue item.

## Calendar Maintenance

- Source probing and trading-day selection fail closed outside the configured `coverage_years` in [trading_holidays_india.json](/mnt/e/omega system - phase 1/config/trading_holidays_india.json).
- Before a new calendar year begins, update both the holiday dates and `coverage_years` for each supported exchange; otherwise verification intentionally raises instead of degrading to weekend-only behavior.
- NSE and BSE holiday lists are stored separately on purpose, even when the current equity-market schedule is identical, so exchange-specific divergences can be recorded explicitly.
