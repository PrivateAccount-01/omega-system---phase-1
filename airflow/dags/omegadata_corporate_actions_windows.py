from __future__ import annotations

from datetime import datetime, timezone

from airflow import DAG
from airflow.operators.python import PythonOperator

from omegadata.pipelines.sequential_pipeline import OmegaDataSequentialPipeline


def run_scheduled_collection() -> None:
    pipeline = OmegaDataSequentialPipeline()
    pipeline.run_scheduled_corporate_action_collection(datetime.now(timezone.utc))


def run_scheduled_confirmation() -> None:
    pipeline = OmegaDataSequentialPipeline()
    pipeline.run_scheduled_track_b_confirmation(datetime.now(timezone.utc))


with DAG(
    dag_id="omegadata_nse_corporate_actions_windows",
    start_date=datetime(2024, 1, 1),
    schedule="30 1,13 * * 1-5",
    catchup=False,
    tags=["omegadata", "corporate-actions", "track-b"],
) as nse_dag:
    collect_due_sources = PythonOperator(
        task_id="collect_due_sources",
        python_callable=run_scheduled_collection,
    )


with DAG(
    dag_id="omegadata_bse_corporate_actions_windows",
    start_date=datetime(2024, 1, 1),
    schedule="0 2,14 * * 1-5",
    catchup=False,
    tags=["omegadata", "corporate-actions", "track-b"],
) as bse_dag:
    collect_due_sources_bse = PythonOperator(
        task_id="collect_due_sources_bse",
        python_callable=run_scheduled_collection,
    )


with DAG(
    dag_id="omegadata_corporate_actions_confirmation",
    start_date=datetime(2024, 1, 1),
    schedule="30 14 * * 1-5",
    catchup=False,
    tags=["omegadata", "corporate-actions", "track-b"],
) as confirmation_dag:
    run_confirmation = PythonOperator(
        task_id="run_confirmation",
        python_callable=run_scheduled_confirmation,
    )
