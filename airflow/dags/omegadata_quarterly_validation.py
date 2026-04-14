from __future__ import annotations

import json
from datetime import UTC, datetime
from importlib import import_module
from pathlib import Path

DAG = import_module("airflow").DAG
PythonOperator = import_module("airflow.operators.python").PythonOperator


def run_quarterly_validation() -> None:
    from omegadata.config import settings
    from scripts.run_quarterly_secondary_validation import run_validation_pack_file

    out_dir = Path(settings.report_root)
    out_dir.mkdir(parents=True, exist_ok=True)
    pack_path = Path(settings.quarterly_validation_pack)
    if not pack_path.exists():
        raise FileNotFoundError(
            f"Quarterly validation pack not found at {pack_path}. Provide real inputs before running the DAG."
        )

    report = run_validation_pack_file(pack_path)
    report_path = out_dir / f"quarterly_validation_{datetime.now(UTC):%Y%m%d}.json"
    report_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )


with DAG(
    dag_id="omegadata_quarterly_secondary_validation",
    start_date=datetime(2024, 1, 1),
    schedule="0 4 1 */3 *",
    catchup=False,
    tags=["omegadata", "validation", "quarterly"],
) as dag:
    quarterly_validation = PythonOperator(
        task_id="quarterly_validation",
        python_callable=run_quarterly_validation,
    )
