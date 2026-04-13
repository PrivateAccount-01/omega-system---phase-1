from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

from omegadata.track_a.trading_calendar import TradingCalendar


def main() -> None:
    calendar = TradingCalendar.from_config()
    statuses = calendar.all_coverage_statuses(
        anchor_date=date.today(),
        warning_window_days=calendar.maintenance.renewal_window_days,
    )

    out_dir = Path("artifacts/verification")
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact = {
        "generated_at": datetime.now(UTC).isoformat(),
        "calendar_config_state": calendar.config_state,
        "calendar_config_path": calendar.config_path,
        "warning_window_days": calendar.maintenance.renewal_window_days,
        "owner_role": calendar.maintenance.owner_role,
        "runbook": calendar.maintenance.runbook,
        "supported_exchanges": list(calendar.maintenance.supported_exchanges),
        "statuses": statuses,
    }
    out_path = out_dir / "trading_calendar_coverage.json"
    out_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")

    fail = False
    for status in statuses:
        level = status["status"]
        message = str(status["message"])
        exchange = str(status["exchange"])
        if level in {"expired", "missing"} and exchange in calendar.maintenance.supported_exchanges:
            fail = True
            print(f"::error::{exchange}: {message}")
        elif level == "warning":
            print(f"::warning::{exchange}: {message}")

    print(f"Wrote {out_path}")
    if fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
