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
