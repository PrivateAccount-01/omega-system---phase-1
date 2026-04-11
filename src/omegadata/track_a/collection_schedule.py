from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


IST = ZoneInfo("Asia/Kolkata")


@dataclass(frozen=True)
class CollectionWindow:
    name: str
    source_key: str
    scheduled_time_ist: time


CORPORATE_ACTION_WINDOWS: tuple[CollectionWindow, ...] = (
    CollectionWindow(
        name="nse_corporate_actions_morning",
        source_key="NSE_CORPORATE_ACTIONS",
        scheduled_time_ist=time(hour=7, minute=0),
    ),
    CollectionWindow(
        name="bse_corporate_actions_morning",
        source_key="BSE_CORPORATE_ACTIONS",
        scheduled_time_ist=time(hour=7, minute=30),
    ),
    CollectionWindow(
        name="nse_corporate_actions_evening",
        source_key="NSE_CORPORATE_ACTIONS",
        scheduled_time_ist=time(hour=19, minute=0),
    ),
    CollectionWindow(
        name="bse_corporate_actions_evening",
        source_key="BSE_CORPORATE_ACTIONS",
        scheduled_time_ist=time(hour=19, minute=30),
    ),
)

MATCH_CONFIRMATION_TIME = time(hour=20, minute=0)


def _ensure_aware_utc(run_at: datetime) -> datetime:
    if run_at.tzinfo is None:
        return run_at.replace(tzinfo=timezone.utc)
    return run_at.astimezone(timezone.utc)


def _target_for(run_at: datetime, scheduled_time_ist: time) -> datetime:
    run_at_ist = _ensure_aware_utc(run_at).astimezone(IST)
    return datetime.combine(
        run_at_ist.date(),
        scheduled_time_ist,
        tzinfo=IST,
    )


def _within_grace(run_at: datetime, target: datetime, grace_minutes: int) -> bool:
    delta = abs((_ensure_aware_utc(run_at) - target.astimezone(timezone.utc)).total_seconds())
    return delta <= grace_minutes * 60


def due_corporate_action_sources(
    run_at: datetime,
    grace_minutes: int = 20,
) -> list[str]:
    due: list[str] = []
    for window in CORPORATE_ACTION_WINDOWS:
        target = _target_for(run_at, window.scheduled_time_ist)
        if _within_grace(run_at, target, grace_minutes=grace_minutes):
            due.append(window.source_key)
    return list(dict.fromkeys(due))


def should_run_corporate_action_confirmation(
    run_at: datetime,
    grace_minutes: int = 20,
) -> bool:
    target = _target_for(run_at, MATCH_CONFIRMATION_TIME)
    return _within_grace(run_at, target, grace_minutes=grace_minutes)


def require_corporate_action_window(
    source_key: str,
    run_at: datetime,
    grace_minutes: int = 20,
) -> None:
    if source_key not in {"NSE_CORPORATE_ACTIONS", "BSE_CORPORATE_ACTIONS"}:
        return
    due = due_corporate_action_sources(run_at=run_at, grace_minutes=grace_minutes)
    if source_key not in due:
        raise ValueError(
            f"{source_key} is outside its scheduled IST collection windows at {run_at.isoformat()}"
        )


def require_confirmation_window(run_at: datetime, grace_minutes: int = 20) -> None:
    if not should_run_corporate_action_confirmation(run_at=run_at, grace_minutes=grace_minutes):
        raise ValueError(
            f"Corporate action confirmation is outside the scheduled 20:00 IST window at {run_at.isoformat()}"
        )
