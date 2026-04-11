from __future__ import annotations

from datetime import datetime, timezone

from omegadata.track_a.collection_schedule import (
    due_corporate_action_sources,
    require_confirmation_window,
    require_corporate_action_window,
    should_run_corporate_action_confirmation,
)


def test_due_corporate_action_windows_match_ist_schedule() -> None:
    nse_run = datetime(2026, 4, 10, 1, 30, tzinfo=timezone.utc)
    bse_run = datetime(2026, 4, 10, 2, 0, tzinfo=timezone.utc)

    assert due_corporate_action_sources(nse_run) == ["NSE_CORPORATE_ACTIONS"]
    assert due_corporate_action_sources(bse_run) == ["BSE_CORPORATE_ACTIONS"]


def test_confirmation_window_enforced() -> None:
    valid_run = datetime(2026, 4, 10, 14, 30, tzinfo=timezone.utc)
    invalid_run = datetime(2026, 4, 10, 5, 0, tzinfo=timezone.utc)

    assert should_run_corporate_action_confirmation(valid_run) is True
    require_confirmation_window(valid_run)

    try:
        require_corporate_action_window("NSE_CORPORATE_ACTIONS", invalid_run)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected invalid collection window to raise")

    try:
        require_confirmation_window(invalid_run)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected invalid confirmation window to raise")
