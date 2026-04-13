from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from omegadata.config import settings


@dataclass(frozen=True)
class TradingCalendar:
    holidays_by_exchange: dict[str, set[date]]

    @classmethod
    def from_config(cls) -> TradingCalendar:
        path = Path(settings.trading_holiday_path)
        if not path.exists():
            return cls(holidays_by_exchange={})
        payload = json.loads(path.read_text(encoding="utf-8"))
        holidays_by_exchange: dict[str, set[date]] = {}
        raw = payload.get("holidays", {})
        if isinstance(raw, dict):
            for exchange, values in raw.items():
                if not isinstance(values, list):
                    continue
                holidays_by_exchange[str(exchange)] = {
                    date.fromisoformat(value) for value in values if isinstance(value, str)
                }
        return cls(holidays_by_exchange=holidays_by_exchange)

    def is_trading_day(self, exchange: str, candidate: date) -> bool:
        if candidate.weekday() >= 5:
            return False
        holidays = self.holidays_by_exchange.get(exchange, set())
        return candidate not in holidays

    def recent_trading_days(
        self,
        exchange: str,
        *,
        anchor_date: date,
        limit: int,
    ) -> list[date]:
        values: list[date] = []
        offset = 1
        while len(values) < limit:
            candidate = anchor_date - timedelta(days=offset)
            offset += 1
            if self.is_trading_day(exchange, candidate):
                values.append(candidate)
        return values
