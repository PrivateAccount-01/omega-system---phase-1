from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from omegadata.db.models import InstrumentMaster, SymbolMap
from omegadata.domain import Exchange, InstrumentType
from omegadata.track_b.isin_master import ISINMasterService


def test_isin_validation_real_values() -> None:
    svc = ISINMasterService()
    assert svc.validate_isin("INE009A01021")  # Infosys
    assert svc.validate_isin("INE467B01029")  # TCS
    assert not svc.validate_isin("INE009A01022")
    assert not svc.validate_isin("US0378331005")


def test_symbol_change_protocol(db_session) -> None:
    svc = ISINMasterService()
    svc.create_instrument(
        session=db_session,
        isin="INE009A01021",
        company_name="Infosys Limited",
        instrument_type=InstrumentType.EQUITY,
        primary_exchange=Exchange.NSE,
        listed_date=date(1993, 2, 8),
        symbol="INFY",
    )

    svc.apply_symbol_change(
        session=db_session,
        isin="INE009A01021",
        exchange=Exchange.NSE,
        new_symbol="INFOSYS",
        effective_date=date(2026, 1, 2),
        reason="NSE symbol alignment",
        circular_reference="NSE/CML/2026/001",
    )

    old_map = db_session.scalar(
        select(SymbolMap)
        .where(SymbolMap.symbol == "INFY")
        .where(SymbolMap.exchange == Exchange.NSE)
    )
    new_map = db_session.scalar(
        select(SymbolMap)
        .where(SymbolMap.symbol == "INFOSYS")
        .where(SymbolMap.exchange == Exchange.NSE)
    )
    assert old_map is not None and old_map.valid_to == date(2026, 1, 1)
    assert new_map is not None and new_map.valid_from == date(2026, 1, 2)


def test_delisting_protocol(db_session) -> None:
    svc = ISINMasterService()
    svc.create_instrument(
        session=db_session,
        isin="INE009A01021",
        company_name="Test Delist Corp",
        instrument_type=InstrumentType.EQUITY,
        primary_exchange=Exchange.NSE,
        listed_date=date(2000, 1, 1),
        symbol="DLIST",
    )
    svc.mark_delisted(
        session=db_session,
        isin="INE009A01021",
        delisting_date=date(2024, 12, 31),
        reason="voluntary",
        delisting_type="DELISTING_VOLUNTARY",
        last_recorded_price=Decimal("120.5"),
    )
    master = db_session.get(InstrumentMaster, "INE009A01021")
    assert master is not None
    assert master.active is False
    assert master.delisted_date == date(2024, 12, 31)
