from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from omegadata.config import settings


@dataclass(frozen=True)
class TradingCalendar:
    holidays_by_exchange: dict[str, set[date]]
    coverage_years_by_exchange: dict[str, set[int]]

    @classmethod
    def from_config(cls) -> TradingCalendar:
        path = Path(settings.trading_holiday_path)
        if not path.exists():
            return cls(holidays_by_exchange={}, coverage_years_by_exchange={})
        payload = json.loads(path.read_text(encoding="utf-8"))
        holidays_by_exchange: dict[str, set[date]] = {}
        coverage_years_by_exchange: dict[str, set[int]] = {}
        raw = payload.get("holidays", {})
        if isinstance(raw, dict):
            for exchange, values in raw.items():
                if not isinstance(values, list):
                    continue
                holidays_by_exchange[str(exchange)] = {
                    date.fromisoformat(value) for value in values if isinstance(value, str)
                }
        raw_years = payload.get("coverage_years", {})
        if isinstance(raw_years, dict):
            for exchange, values in raw_years.items():
                if not isinstance(values, list):
                    continue
                coverage_years_by_exchange[str(exchange)] = {
                    int(value) for value in values if isinstance(value, int)
                }
        if not coverage_years_by_exchange:
            for exchange, holidays in holidays_by_exchange.items():
                coverage_years_by_exchange[exchange] = {item.year for item in holidays}
        return cls(
            holidays_by_exchange=holidays_by_exchange,
            coverage_years_by_exchange=coverage_years_by_exchange,
        )

    def year_is_covered(self, exchange: str, year: int) -> bool:
        covered_years = self.coverage_years_by_exchange.get(exchange, set())
        return year in covered_years

    def ensure_year_covered(self, exchange: str, year: int) -> None:
        if not self.year_is_covered(exchange, year):
            raise ValueError(
                f"Trading calendar coverage for {exchange} does not include year {year}; "
                "update trading_holidays_india.json before running source verification."
            )

    def is_trading_day(self, exchange: str, candidate: date, *, strict: bool = False) -> bool:
        if strict:
            self.ensure_year_covered(exchange, candidate.year)
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
        strict: bool = False,
    ) -> list[date]:
        values: list[date] = []
        offset = 1
        while len(values) < limit:
            candidate = anchor_date - timedelta(days=offset)
            offset += 1
            if self.is_trading_day(exchange, candidate, strict=strict):
                values.append(candidate)
        return values

    def coverage_status(
        self,
        exchange: str,
        *,
        anchor_date: date,
        warning_window_days: int,
    ) -> dict[str, object]:
        covered_years = sorted(self.coverage_years_by_exchange.get(exchange, set()))
        if not covered_years:
            return {
                "exchange": exchange,
                "status": "missing",
                "warning": True,
                "message": f"No configured trading-calendar coverage for {exchange}.",
                "covered_years": [],
                "latest_covered_year": None,
                "days_until_expiry": None,
            }

        latest_covered_year = covered_years[-1]
        expiry_date = date(latest_covered_year, 12, 31)
        days_until_expiry = (expiry_date - anchor_date).days
        if anchor_date.year > latest_covered_year:
            status = "expired"
            warning = True
            message = (
                f"Trading-calendar coverage for {exchange} expired after {latest_covered_year}; "
                "update trading_holidays_india.json before running verification in the new year."
            )
        elif days_until_expiry <= warning_window_days:
            status = "warning"
            warning = True
            message = (
                f"Trading-calendar coverage for {exchange} expires in {days_until_expiry} days; "
                "prepare the next-year holiday update."
            )
        else:
            status = "healthy"
            warning = False
            message = f"Trading-calendar coverage for {exchange} is current."

        return {
            "exchange": exchange,
            "status": status,
            "warning": warning,
            "message": message,
            "covered_years": covered_years,
            "latest_covered_year": latest_covered_year,
            "days_until_expiry": days_until_expiry,
        }

    def all_coverage_statuses(
        self,
        *,
        anchor_date: date,
        warning_window_days: int,
    ) -> list[dict[str, object]]:
        exchanges = sorted(
            set(self.coverage_years_by_exchange)
            | set(self.holidays_by_exchange)
        )
        return [
            self.coverage_status(
                exchange,
                anchor_date=anchor_date,
                warning_window_days=warning_window_days,
            )
            for exchange in exchanges
        ]
