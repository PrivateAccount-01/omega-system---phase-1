from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from omegadata.db.base import Base
from omegadata.domain import Exchange, InstrumentType
from omegadata.track_b.isin_master import ISINMasterService
from omegadata.track_b.universe_manager import PointInTimeUniverseManager

SEED_PACK_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "synthetic_seed" / "pit_universe_seed_pack.json"
)
PROJECT_ROOT = SEED_PACK_PATH.parents[3]


def test_effective_date_membership_logic(db_session) -> None:
    isin = "INE009A01021"
    ISINMasterService().create_instrument(
        db_session,
        isin=isin,
        company_name="Infosys Limited",
        instrument_type=InstrumentType.EQUITY,
        primary_exchange=Exchange.NSE,
        listed_date=date(1993, 2, 8),
        symbol="INFY",
    )
    manager = PointInTimeUniverseManager()
    manager.add_membership(
        db_session,
        isin=isin,
        index_name="NIFTY50",
        added_date=date(2020, 3, 1),
        effective_date=date(2020, 3, 27),
        source="NSE PR",
    )
    before = manager.get_universe(db_session, "NIFTY50", date(2020, 3, 26))
    on_day = manager.get_universe(db_session, "NIFTY50", date(2020, 3, 27))
    assert len(before) == 0
    assert len(on_day) == 1


def test_delisted_removed_from_future_universe(db_session) -> None:
    isin = "INE467B01029"
    svc = ISINMasterService()
    svc.create_instrument(
        db_session,
        isin=isin,
        company_name="TCS",
        instrument_type=InstrumentType.EQUITY,
        primary_exchange=Exchange.NSE,
        listed_date=date(2004, 8, 25),
        symbol="TCS",
    )
    manager = PointInTimeUniverseManager()
    manager.add_membership(
        db_session,
        isin=isin,
        index_name="NIFTY50",
        added_date=date(2019, 1, 1),
        effective_date=date(2019, 1, 1),
        source="NSE PR",
    )
    svc.mark_delisted(
        db_session,
        isin=isin,
        delisting_date=date(2024, 1, 1),
        reason="merger",
        delisting_type="DELISTING_MERGER",
        last_recorded_price=Decimal("4000"),
    )
    future = manager.get_universe(db_session, "NIFTY50", date(2024, 1, 2))
    assert len(future) == 0


def test_reconstruction_confidence_pre2010(db_session) -> None:
    manager = PointInTimeUniverseManager()
    frame = pd.DataFrame(
        {
            "isin": ["INE009A01021", "INE467B01029"],
            "market_cap": [1000, 900],
            "avg_20d_volume": [1000000, 800000],
            "trade_date": [pd.Timestamp("2009-12-31"), pd.Timestamp("2009-12-31")],
        }
    )
    rows = manager.reconstruct_pre2010(
        db_session,
        index_name="NIFTY500",
        as_of_date=date(2009, 12, 31),
        bhavcopy_universe=frame,
        min_avg_volume=500000,
        top_n=2,
    )
    assert len(rows) == 2
    assert all(str(row.source_confidence) == "0.70" for row in rows)


def test_seed_pack_backfill_reproduces_reference_snapshots(db_session) -> None:
    manager = PointInTimeUniverseManager()
    pack = json.loads(SEED_PACK_PATH.read_text(encoding="utf-8"))

    loaded = manager.backfill_from_seed_pack(
        db_session,
        pack,
        raw_root=PROJECT_ROOT / "data" / "raw",
    )
    assert loaded > 50

    results = manager.validate_seed_pack(
        db_session,
        pack,
        raw_root=PROJECT_ROOT / "data" / "raw",
    )
    assert len(results) == 5
    assert all(result.matched for result in results)


def test_seed_pack_preserves_knowledge_vs_effective_date_semantics(db_session) -> None:
    manager = PointInTimeUniverseManager()
    pack = json.loads(SEED_PACK_PATH.read_text(encoding="utf-8"))
    manager.backfill_from_seed_pack(
        db_session,
        pack,
        raw_root=PROJECT_ROOT / "data" / "raw",
    )

    upcoming = manager.get_upcoming_additions(
        db_session,
        index_name="NIFTY50",
        as_of_date=date(2020, 3, 12),
        horizon_days=10,
    )
    upcoming_isins = {entry.isin for entry in upcoming}
    assert "INE070A01015" in upcoming_isins  # SHREECEM

    before = {entry.isin for entry in manager.get_universe(db_session, "NIFTY50", date(2020, 3, 18))}
    on_day = {entry.isin for entry in manager.get_universe(db_session, "NIFTY50", date(2020, 3, 19))}

    assert "INE528G01035" in before  # YESBANK
    assert "INE070A01015" not in before
    assert "INE528G01035" not in on_day
    assert "INE070A01015" in on_day


def test_seed_pack_backfill_works_with_production_autoflush_setting(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'prod_like.db'}")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    manager = PointInTimeUniverseManager()
    pack = json.loads(SEED_PACK_PATH.read_text(encoding="utf-8"))

    try:
        loaded = manager.backfill_from_seed_pack(
            session,
            pack,
            raw_root=PROJECT_ROOT / "data" / "raw",
        )
        results = manager.validate_seed_pack(
            session,
            pack,
            raw_root=PROJECT_ROOT / "data" / "raw",
        )
        assert loaded > 50
        assert len(results) == 5
        assert all(result.matched for result in results)
    finally:
        session.close()
        engine.dispose()


def test_remove_membership_raises_for_missing_active_row(db_session) -> None:
    manager = PointInTimeUniverseManager()
    try:
        manager.remove_membership(
            db_session,
            isin="INE404040404",
            index_name="NIFTY50",
            removed_date=date(2024, 1, 1),
            removal_effective=date(2024, 1, 2),
        )
    except LookupError as exc:
        assert "No active membership row" in str(exc)
    else:
        raise AssertionError("Expected remove_membership to raise for missing row")


def test_reconstruct_pre2010_validates_required_columns(db_session) -> None:
    manager = PointInTimeUniverseManager()
    frame = pd.DataFrame(
        {
            "isin": ["INE009A01021"],
            "market_cap": [1000],
        }
    )
    try:
        manager.reconstruct_pre2010(
            db_session,
            index_name="NIFTY500",
            as_of_date=date(2009, 12, 31),
            bhavcopy_universe=frame,
            min_avg_volume=500000,
            top_n=1,
        )
    except ValueError as exc:
        assert "Missing reconstruction columns" in str(exc)
    else:
        raise AssertionError("Expected reconstruct_pre2010 to validate required columns")
