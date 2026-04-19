from __future__ import annotations

import subprocess
import sys
from datetime import UTC, datetime
from importlib import import_module
from pathlib import Path

DAG = import_module("airflow").DAG
PythonOperator = import_module("airflow.operators.python").PythonOperator

REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON = sys.executable


def _run_script(*args: str) -> None:
    subprocess.run([PYTHON, *args], cwd=REPO_ROOT, check=True)


def run_source_probe() -> None:
    _run_script(
        "scripts/generate_source_probe_report.py",
        "--profile-mode",
        "deterministic",
        "--workflow",
        "scheduled_verification",
    )


def run_release_readiness() -> None:
    from omegadata.config import settings

    _run_script(
        "scripts/build_release_readiness_report.py",
        "--db-url",
        settings.verification_db_url,
    )


def run_release_bundle() -> None:
    from omegadata.config import settings

    _run_script(
        "scripts/build_release_bundle.py",
        "--as-of",
        datetime.now(UTC).date().isoformat(),
        "--profile",
        "equity_plus_sidefeeds",
        "--db-url",
        settings.verification_db_url,
    )


def run_pipeline_integration() -> None:
    from omegadata.config import settings

    _run_script(
        "scripts/run_full_pipeline.py",
        "--days",
        "1",
        "--calendar-mode",
        "trading",
        "--db-url",
        settings.verification_db_url,
    )


def run_discontinuity_reaudit() -> None:
    _run_script("scripts/build_discontinuity_spike_report.py")


def run_tolerance_report() -> None:
    from omegadata.config import settings

    _run_script(
        "scripts/build_cross_source_tolerance_report.py",
        "--db-url",
        settings.verification_db_url,
    )


with DAG(
    dag_id="omegadata_verification_daily",
    start_date=datetime(2024, 1, 1, tzinfo=UTC),
    schedule="30 4 * * 1-5",
    catchup=False,
    tags=["omegadata", "verification", "daily"],
) as daily_verification_dag:
    source_probe = PythonOperator(task_id="source_probe", python_callable=run_source_probe)
    pipeline_integration = PythonOperator(task_id="pipeline_integration", python_callable=run_pipeline_integration)
    release_readiness = PythonOperator(task_id="release_readiness", python_callable=run_release_readiness)
    release_bundle = PythonOperator(task_id="release_bundle", python_callable=run_release_bundle)

    source_probe >> pipeline_integration >> release_readiness >> release_bundle


with DAG(
    dag_id="omegadata_verification_weekly",
    start_date=datetime(2024, 1, 1, tzinfo=UTC),
    schedule="0 5 * * 6",
    catchup=False,
    tags=["omegadata", "verification", "weekly"],
) as weekly_verification_dag:
    discontinuity_reaudit = PythonOperator(
        task_id="discontinuity_reaudit",
        python_callable=run_discontinuity_reaudit,
    )
    tolerance_report = PythonOperator(
        task_id="tolerance_report",
        python_callable=run_tolerance_report,
    )

    discontinuity_reaudit >> tolerance_report
