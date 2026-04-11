from __future__ import annotations

from datetime import date, timedelta

import pytest

from omegadata.track_a.download_manager import DownloadManager

pytestmark = [pytest.mark.realdata]


def _recent_days(limit: int = 10) -> list[date]:
    today = date.today()
    return [today - timedelta(days=i) for i in range(1, limit + 1)]


def test_real_gdelt_download() -> None:
    manager = DownloadManager()
    artifact = manager.download("GDELT", date.today())
    assert artifact.bytes_downloaded > 0


def test_real_nse_equity_download_recent_date() -> None:
    manager = DownloadManager()
    last_error: Exception | None = None
    for d in _recent_days(12):
        try:
            artifact = manager.download("NSE_EQUITY_BHAVCOPY", d)
            assert artifact.bytes_downloaded > 0
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            continue
    pytest.fail(f"No NSE equity bhavcopy available for recent days: {last_error}")


def test_real_nse_corporate_actions_endpoint() -> None:
    manager = DownloadManager()
    last_error: Exception | None = None
    artifact = None
    for _ in range(3):
        try:
            artifact = manager.download("NSE_CORPORATE_ACTIONS", date.today())
            break
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            continue

    if artifact is None:
        pytest.fail(f"NSE corporate actions unavailable after retries: {last_error}")

    assert artifact.bytes_downloaded > 0
