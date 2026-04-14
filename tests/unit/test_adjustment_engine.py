from __future__ import annotations

from datetime import date
from decimal import Decimal

from omegadata.db.models import ConfirmedCorporateAction, PriceRecord
from omegadata.domain import ConfidenceLevel, CorporateActionType, Exchange
from omegadata.track_b.adjustment_engine import PriceAdjustmentEngine


def _insert_price(db_session, trade_date: date, close: str, volume: str = "100") -> None:
    db_session.add(
        PriceRecord(
            isin="INE009A01021",
            exchange=Exchange.NSE,
            trade_date=trade_date,
            open_price=Decimal(close),
            high_price=Decimal(close),
            low_price=Decimal(close),
            close_price=Decimal(close),
            volume=Decimal(volume),
            raw_source="nse_bhavcopy",
            confidence_score=Decimal("1.00"),
        )
    )


def test_bonus_adjustment_real_case(db_session) -> None:
    _insert_price(db_session, date(2018, 6, 13), "1270.45", "100")
    _insert_price(db_session, date(2018, 6, 14), "640.00", "210")
    db_session.add(
        ConfirmedCorporateAction(
            isin="INE009A01021",
            action_type=CorporateActionType.BONUS,
            confidence=ConfidenceLevel.HIGH,
            announcement_date=date(2018, 4, 13),
            ex_date=date(2018, 6, 14),
            record_date=date(2018, 6, 16),
            parameters={"bonus_ratio_numerator": "1", "bonus_ratio_denominator": "1"},
            source_preference=Exchange.NSE,
            superseded=False,
        )
    )
    db_session.flush()

    engine = PriceAdjustmentEngine()
    updated = engine.recompute_adjusted_series(db_session, isin="INE009A01021")
    assert updated == 2
    row = next(r for r in db_session.query(PriceRecord).all() if r.trade_date == date(2018, 6, 13))
    assert Decimal(str(row.adjusted_close_price)) == Decimal("635.225000")
    assert Decimal(str(row.adjusted_volume)) == Decimal("200.0000")


def test_rights_fallback_zero_subscription(db_session) -> None:
    _insert_price(db_session, date(2020, 1, 9), "100.00", "100")
    _insert_price(db_session, date(2020, 1, 10), "95.00", "90")
    db_session.add(
        ConfirmedCorporateAction(
            isin="INE009A01021",
            action_type=CorporateActionType.RIGHTS,
            confidence=ConfidenceLevel.MEDIUM,
            announcement_date=date(2019, 12, 1),
            ex_date=date(2020, 1, 10),
            record_date=date(2020, 1, 11),
            parameters={
                "rights_ratio_numerator": "1",
                "rights_ratio_denominator": "4",
                "issue_price": None,
            },
            source_preference=Exchange.NSE,
            superseded=False,
        )
    )
    engine = PriceAdjustmentEngine()
    engine.recompute_adjusted_series(db_session, isin="INE009A01021")
    row = next(r for r in db_session.query(PriceRecord).all() if r.trade_date == date(2020, 1, 9))
    assert row.adjustment_chain
    assert row.adjustment_chain[0]["subscription_price_fallback_zero"] is True


def test_cumulative_multiple_actions(db_session) -> None:
    _insert_price(db_session, date(2021, 1, 1), "1000", "100")
    _insert_price(db_session, date(2021, 1, 2), "500", "200")
    _insert_price(db_session, date(2021, 1, 3), "250", "400")
    db_session.add_all(
        [
            ConfirmedCorporateAction(
                isin="INE009A01021",
                action_type=CorporateActionType.BONUS,
                confidence=ConfidenceLevel.HIGH,
                announcement_date=date(2020, 12, 1),
                ex_date=date(2021, 1, 2),
                record_date=date(2021, 1, 2),
                parameters={"bonus_ratio_numerator": "1", "bonus_ratio_denominator": "1"},
                source_preference=Exchange.NSE,
                superseded=False,
            ),
            ConfirmedCorporateAction(
                isin="INE009A01021",
                action_type=CorporateActionType.SPLIT,
                confidence=ConfidenceLevel.HIGH,
                announcement_date=date(2020, 12, 15),
                ex_date=date(2021, 1, 3),
                record_date=date(2021, 1, 3),
                parameters={"old_face_value": "10", "new_face_value": "5"},
                source_preference=Exchange.NSE,
                superseded=False,
            ),
        ]
    )
    engine = PriceAdjustmentEngine()
    engine.recompute_adjusted_series(db_session, isin="INE009A01021")
    row = next(r for r in db_session.query(PriceRecord).all() if r.trade_date == date(2021, 1, 1))
    assert Decimal(str(row.cumulative_price_factor)) == Decimal("0.25")


def test_demerger_actuals_finalize_from_preferred_exchange(db_session) -> None:
    db_session.add_all(
        [
            PriceRecord(
                isin="PARENT000001",
                exchange=Exchange.NSE,
                trade_date=date(2025, 4, 4),
                open_price=Decimal("100"),
                high_price=Decimal("100"),
                low_price=Decimal("100"),
                close_price=Decimal("100"),
                volume=Decimal("100"),
                raw_source="nse_bhavcopy",
                confidence_score=Decimal("1.00"),
            ),
            PriceRecord(
                isin="SPINOFF00001",
                exchange=Exchange.BSE,
                trade_date=date(2025, 4, 7),
                open_price=Decimal("21"),
                high_price=Decimal("21"),
                low_price=Decimal("21"),
                close_price=Decimal("21"),
                volume=Decimal("100"),
                raw_source="bse_bhavcopy",
                confidence_score=Decimal("1.00"),
            ),
            PriceRecord(
                isin="SPINOFF00001",
                exchange=Exchange.NSE,
                trade_date=date(2025, 4, 7),
                open_price=Decimal("20"),
                high_price=Decimal("20"),
                low_price=Decimal("20"),
                close_price=Decimal("20"),
                volume=Decimal("100"),
                raw_source="nse_bhavcopy",
                confidence_score=Decimal("1.00"),
            ),
            ConfirmedCorporateAction(
                isin="PARENT000001",
                action_type=CorporateActionType.DEMERGER_PARENT,
                confidence=ConfidenceLevel.MEDIUM,
                announcement_date=date(2025, 4, 1),
                ex_date=date(2025, 4, 7),
                record_date=date(2025, 4, 7),
                parameters={
                    "parent_value_pre_demerger": "100",
                    "spinoff_isin": "SPINOFF00001",
                    "spinoff_value": "18",
                },
                source_preference=Exchange.NSE,
                superseded=False,
            ),
        ]
    )

    engine = PriceAdjustmentEngine()
    refreshed = engine.refresh_demerger_actuals(db_session, isin="PARENT000001", exchange=Exchange.NSE)
    assert refreshed == 1

    action = next(a for a in db_session.query(ConfirmedCorporateAction).all() if a.isin == "PARENT000001")
    assert action.parameters["actual_spinoff_listing_price"] == "20.000000"
    assert action.parameters["actual_spinoff_exchange"] == "NSE"
    assert action.parameters["demerger_adjustment_stage"] == "FINAL"
