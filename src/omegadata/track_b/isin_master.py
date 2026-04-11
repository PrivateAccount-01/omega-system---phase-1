from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from omegadata.db.models import (
    CrossListingMap,
    DelistingRecord,
    IPORegistry,
    InstrumentMaster,
    SymbolChangeLog,
    SymbolMap,
)
from omegadata.domain import Exchange, InstrumentType


class ISINValidationError(ValueError):
    pass


@dataclass(frozen=True)
class SymbolResolution:
    isin: str
    exchange: Exchange
    symbol: str
    as_of: date


class ISINMasterService:
    @staticmethod
    def validate_isin(isin: str) -> bool:
        if len(isin) != 12 or not isin.isalnum() or isin[:2].upper() != "IN":
            return False

        converted = ""
        for ch in isin[:-1].upper():
            if ch.isdigit():
                converted += ch
            else:
                converted += str(ord(ch) - 55)

        digits = [int(d) for d in converted]
        digits.reverse()

        total = 0
        for idx, val in enumerate(digits, start=1):
            doubled = val * 2 if idx % 2 == 1 else val
            total += doubled // 10 + doubled % 10

        check = (10 - (total % 10)) % 10
        return str(check) == isin[-1]

    def create_instrument(
        self,
        session: Session,
        isin: str,
        company_name: str,
        instrument_type: InstrumentType,
        primary_exchange: Exchange,
        listed_date: date,
        symbol: str | None = None,
    ) -> InstrumentMaster:
        if not self.validate_isin(isin):
            raise ISINValidationError(f"Invalid ISIN: {isin}")

        existing = session.get(InstrumentMaster, isin)
        if existing is not None:
            return existing

        master = InstrumentMaster(
            isin=isin,
            company_name=company_name,
            instrument_type=instrument_type,
            primary_exchange=primary_exchange,
            listed_date=listed_date,
            active=True,
        )
        session.add(master)

        if symbol:
            session.add(
                SymbolMap(
                    isin=isin,
                    exchange=primary_exchange,
                    symbol=symbol,
                    valid_from=listed_date,
                    valid_to=None,
                )
            )
        return master

    def add_ipo_record(
        self,
        session: Session,
        isin: str,
        listing_date: date,
        ipo_price: Decimal,
        issue_size: Decimal,
    ) -> IPORegistry:
        record = IPORegistry(
            isin=isin,
            listing_date=listing_date,
            ipo_price=ipo_price,
            issue_size=issue_size,
        )
        session.add(record)
        return record

    def add_cross_listing(
        self,
        session: Session,
        isin: str,
        foreign_exchange: str,
        foreign_identifier: str,
        valid_from: date,
        valid_to: date | None = None,
    ) -> CrossListingMap:
        record = CrossListingMap(
            isin=isin,
            foreign_exchange=foreign_exchange,
            foreign_identifier=foreign_identifier,
            valid_from=valid_from,
            valid_to=valid_to,
        )
        session.add(record)
        return record

    def apply_symbol_change(
        self,
        session: Session,
        isin: str,
        exchange: Exchange,
        new_symbol: str,
        effective_date: date,
        reason: str,
        circular_reference: str,
        discrepancy_found: bool = False,
    ) -> SymbolChangeLog:
        current = session.scalar(
            select(SymbolMap)
            .where(SymbolMap.isin == isin)
            .where(SymbolMap.exchange == exchange)
            .where(SymbolMap.valid_to.is_(None))
        )
        if current is None:
            raise ValueError(f"No active symbol mapping for {isin}/{exchange}")

        old_symbol = current.symbol
        current.valid_to = effective_date - timedelta(days=1)

        session.add(
            SymbolMap(
                isin=isin,
                exchange=exchange,
                symbol=new_symbol,
                valid_from=effective_date,
                valid_to=None,
            )
        )

        log = SymbolChangeLog(
            isin=isin,
            exchange=exchange,
            old_symbol=old_symbol,
            new_symbol=new_symbol,
            effective_date=effective_date,
            reason=reason,
            circular_reference=circular_reference,
            discrepancy_found=discrepancy_found,
        )
        session.add(log)
        return log

    def resolve_symbol(self, session: Session, isin: str, exchange: Exchange, as_of: date) -> SymbolResolution:
        mapping = session.scalar(
            select(SymbolMap)
            .where(SymbolMap.isin == isin)
            .where(SymbolMap.exchange == exchange)
            .where(SymbolMap.valid_from <= as_of)
            .where((SymbolMap.valid_to.is_(None)) | (SymbolMap.valid_to >= as_of))
        )
        if mapping is None:
            raise LookupError(f"No symbol mapping for {isin}/{exchange} on {as_of.isoformat()}")
        return SymbolResolution(isin=isin, exchange=exchange, symbol=mapping.symbol, as_of=as_of)

    def mark_delisted(
        self,
        session: Session,
        isin: str,
        delisting_date: date,
        reason: str,
        delisting_type: str,
        last_recorded_price: Decimal,
    ) -> DelistingRecord:
        master = session.get(InstrumentMaster, isin)
        if master is None:
            raise LookupError(f"Unknown ISIN: {isin}")

        master.delisted_date = delisting_date
        master.active = False

        active_mappings = session.scalars(
            select(SymbolMap).where(SymbolMap.isin == isin).where(SymbolMap.valid_to.is_(None))
        ).all()
        for mapping in active_mappings:
            mapping.valid_to = delisting_date

        record = DelistingRecord(
            isin=isin,
            reason=reason,
            delisting_type=delisting_type,
            last_trading_date=delisting_date,
            last_recorded_price=last_recorded_price,
        )
        session.add(record)
        return record
