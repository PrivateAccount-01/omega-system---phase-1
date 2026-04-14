from __future__ import annotations

from datetime import UTC, datetime

from airflow.operators.python import PythonOperator

from airflow import DAG
from omegadata.track_a.orchestration import IngestionOrchestrator


def run_daily_equity_ingest() -> None:
    orchestrator = IngestionOrchestrator()
    orchestrator.ingest_raw_source("NSE_EQUITY_BHAVCOPY", datetime.now(UTC).date())


def run_nse_ca_collection() -> None:
    orchestrator = IngestionOrchestrator()
    orchestrator.ingest_raw_source("NSE_CORPORATE_ACTIONS", datetime.now(UTC).date())


def run_bse_ca_collection() -> None:
    orchestrator = IngestionOrchestrator()
    orchestrator.ingest_raw_source("BSE_CORPORATE_ACTIONS", datetime.now(UTC).date())


with DAG(
    dag_id="omegadata_track_a_pipeline",
    start_date=datetime(2024, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["omegadata", "track-a"],
) as dag:
    daily_equity = PythonOperator(task_id="daily_equity_ingest", python_callable=run_daily_equity_ingest)

    nse_ca_morning = PythonOperator(task_id="nse_ca_morning", python_callable=run_nse_ca_collection)
    bse_ca_morning = PythonOperator(task_id="bse_ca_morning", python_callable=run_bse_ca_collection)

    daily_equity >> nse_ca_morning >> bse_ca_morning
