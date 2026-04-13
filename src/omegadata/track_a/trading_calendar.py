from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from omegadata.config import settings


@dataclass(frozen=True)
class CalendarMaintenance:
    owner_role: str = "Unassigned"
    renewal_window_days: int = 60
    runbook: str = ""
    supported_exchanges: tuple[str, ...] = ("NSE", "BSE")


@dataclass(frozen=True)
class TradingCalendar:
    holidays_by_exchange: dict[str, set[date]]
    coverage_years_by_exchange: dict[str, set[int]]
    maintenance: CalendarMaintenance = field(default_factory=CalendarMaintenance)
    config_state: str = "loaded"
    config_path: str | None = None
    config_error: str | None = None

    @classmethod
    def from_config(cls) -> TradingCalendar:
        path = Path(settings.trading_holiday_path)
        if not path.exists():
            return cls(
                holidays_by_exchange={},
                coverage_years_by_exchange={},
                config_state="missing",
                config_path=path.as_posix(),
            )
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return cls(
                holidays_by_exchange={},
                coverage_years_by_exchange={},
                config_state="invalid",
                config_path=path.as_posix(),
                config_error=str(exc),
            )
        holidays_by_exchange: dict[str, set[date]] = {}
        coverage_years_by_exchange: dict[str, set[int]] = {}
        raw_maintenance = payload.get("maintenance", {})
        maintenance = CalendarMaintenance()
        if isinstance(raw_maintenance, dict):
            owner_role = raw_maintenance.get("owner_role", maintenance.owner_role)
            renewal_window_days = raw_maintenance.get(
                "renewal_window_days",
                maintenance.renewal_window_days,
            )
            runbook = raw_maintenance.get("runbook", maintenance.runbook)
            supported_exchanges = raw_maintenance.get(
                "supported_exchanges",
                list(maintenance.supported_exchanges),
            )
            maintenance = CalendarMaintenance(
                owner_role=str(owner_role).strip() or maintenance.owner_role,
                renewal_window_days=(
                    int(renewal_window_days)
                    if isinstance(renewal_window_days, int)
                    else maintenance.renewal_window_days
                ),
                runbook=str(runbook).strip(),
                supported_exchanges=tuple(
                    str(value).strip()
                    for value in supported_exchanges
                    if isinstance(value, str) and str(value).strip()
                )
                or maintenance.supported_exchanges,
            )
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
            maintenance=maintenance,
            config_state="loaded",
            config_path=path.as_posix(),
            config_error=None,
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

    def add_business_days(
        self,
        exchange: str,
        *,
        anchor_date: date,
        business_days: int,
        strict: bool = False,
    ) -> date:
        candidate = anchor_date
        remaining = business_days
        while remaining > 0:
            candidate += timedelta(days=1)
            if self.is_trading_day(exchange, candidate, strict=strict):
                remaining -= 1
        return candidate

    def business_days_between(
        self,
        exchange: str,
        *,
        start_date: date,
        end_date: date,
        strict: bool = False,
    ) -> int:
        if end_date <= start_date:
            return 0
        candidate = start_date
        count = 0
        while candidate < end_date:
            candidate += timedelta(days=1)
            if self.is_trading_day(exchange, candidate, strict=strict):
                count += 1
        return count

    def coverage_status(
        self,
        exchange: str,
        *,
        anchor_date: date,
        warning_window_days: int,
    ) -> dict[str, object]:
        if self.config_state == "invalid":
            return {
                "exchange": exchange,
                "status": "invalid_config",
                "warning": True,
                "message": f"Trading-calendar configuration for {exchange} is invalid.",
                "covered_years": [],
                "latest_covered_year": None,
                "days_until_expiry": None,
                "config_error": self.config_error,
            }
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
                "config_error": self.config_error,
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
            "config_error": self.config_error,
        }

    def all_coverage_statuses(
        self,
        *,
        anchor_date: date,
        warning_window_days: int,
    ) -> list[dict[str, object]]:
        exchanges = sorted(
            set(self.maintenance.supported_exchanges)
            | set(self.coverage_years_by_exchange)
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
