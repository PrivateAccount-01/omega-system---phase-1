# pyright: reportMissingImports=false

from __future__ import annotations

from datetime import datetime
from importlib import import_module

DAG = import_module("airflow").DAG
PythonOperator = import_module("airflow.operators.python").PythonOperator


def run_monthly() -> None:
    from omegadata.pipelines.monthly_quality_pipeline import run_monthly_quality_report

    result = run_monthly_quality_report(datetime.utcnow().date())
    print(f"Monthly quality report generated: {result.path}")


with DAG(
    dag_id="omegadata_monthly_quality_report",
    start_date=datetime(2024, 1, 1),
    schedule="0 2 1 * *",
    catchup=False,
    tags=["omegadata", "quality", "monthly"],
) as dag:
    monthly_quality = PythonOperator(
        task_id="monthly_quality_report",
        python_callable=run_monthly,
    )
