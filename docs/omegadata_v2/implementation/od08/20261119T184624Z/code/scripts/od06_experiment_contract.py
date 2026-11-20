"""Pure fail-closed experiment result contract; never a financial Gatekeeper."""

from typing import Any


def experiment_stage_accepted(
    job: str,
    exit_code: int,
    worker_result: dict[str, Any] | None,
    crash_record: dict[str, Any] | None = None,
) -> bool:
    if job == "dbcrash":
        return bool(
            exit_code == 247
            and crash_record is not None
            and crash_record.get("native_returncode") == -9
            and crash_record.get("controlled_signal") == "SIGKILL"
            and crash_record.get("stage") == "AFTER_INSERT_BEFORE_COMMIT"
            and crash_record.get("guest_barrier", {}).get("stage") == "UNCOMMITTED_INSERT"
        )
    if job not in {"dbinit", "dbrecover", "dbcompete-a", "dbcompete-b", "dbfinal"}:
        return False
    if exit_code != 0 or worker_result is None or worker_result.get("exit_code") != 0:
        return False
    expected = (
        {"COMMITTED", "REFUSED_COMPETING_SUCCESSOR"} if job.startswith("dbcompete") else {"PASS"}
    )
    return worker_result.get("status") in expected
