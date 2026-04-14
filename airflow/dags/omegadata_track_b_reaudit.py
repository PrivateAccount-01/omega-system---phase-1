from __future__ import annotations

from datetime import UTC, datetime
from importlib import import_module

DAG = import_module("airflow").DAG
PythonOperator = import_module("airflow.operators.python").PythonOperator


def run_weekly_reaudit() -> None:
    from omegadata.config import settings
    from omegadata.pipelines.sequential_pipeline import OmegaDataSequentialPipeline

    pipeline = OmegaDataSequentialPipeline()
    pipeline.run_track_b(as_of=datetime.now(UTC).date(), market_isin=settings.market_proxy_isin or None)


with DAG(
    dag_id="omegadata_track_b_weekly_reaudit",
    start_date=datetime(2024, 1, 1),
    schedule="0 3 * * 6",
    catchup=False,
    tags=["omegadata", "track-b", "qa"],
) as dag:
    weekly_reaudit = PythonOperator(
        task_id="weekly_reaudit",
        python_callable=run_weekly_reaudit,
    )
