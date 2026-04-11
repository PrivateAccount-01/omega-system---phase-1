# OmegaData

OmegaData is the production data layer for Indian equity market data with strict specification-driven behavior for corporate action handling, confidence scoring, point-in-time universes, and cross-source validation.

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

5. Run API server:

```bash
uvicorn omegadata.api.main:app --reload
```

6. Apply database migrations:

```bash
alembic upgrade head
```

7. Start local infrastructure stack:

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
