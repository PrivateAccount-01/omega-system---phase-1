from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

from omegadata.config import settings
from omegadata.track_a.trading_calendar import TradingCalendar


def main() -> None:
    calendar = TradingCalendar.from_config()
    statuses = calendar.all_coverage_statuses(
        anchor_date=date.today(),
        warning_window_days=settings.trading_calendar_warning_window_days,
    )

    out_dir = Path("artifacts/verification")
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact = {
        "generated_at": datetime.now(UTC).isoformat(),
        "warning_window_days": settings.trading_calendar_warning_window_days,
        "owner_role": "OmegaData data operations",
        "statuses": statuses,
    }
    out_path = out_dir / "trading_calendar_coverage.json"
    out_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")

    for status in statuses:
        level = status["status"]
        message = str(status["message"])
        exchange = str(status["exchange"])
        if level == "expired":
            print(f"::error::{exchange}: {message}")
        elif level in {"warning", "missing"}:
            print(f"::warning::{exchange}: {message}")

    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
