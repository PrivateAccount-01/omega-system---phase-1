from __future__ import annotations

from datetime import date
from decimal import Decimal

from omegadata.db.models import ConfirmedCorporateAction, ExclusionDate, PriceRecord
from omegadata.domain import ConfidenceLevel, CorporateActionType, Exchange
from omegadata.track_b.discontinuity import DiscontinuityDetector


def _price(isin: str, d: date, close: str, high: str | None = None, low: str | None = None) -> PriceRecord:
    close_dec = Decimal(close)
    return PriceRecord(
        isin=isin,
        exchange=Exchange.NSE,
        trade_date=d,
        open_price=close_dec,
        high_price=close_dec if high is None else Decimal(high),
        low_price=close_dec if low is None else Decimal(low),
        close_price=close_dec,
        volume=Decimal("100"),
        raw_source="nse_bhavcopy",
        confidence_score=Decimal("1.00"),
    )


def test_category_a_with_matching_action_autoqueues(db_session) -> None:
    db_session.add_all(
        [
            _price("MARKET", date(2024, 1, 1), "100"),
            _price("MARKET", date(2024, 1, 2), "100"),
            _price("INE009A01021", date(2024, 1, 1), "1000"),
            _price("INE009A01021", date(2024, 1, 2), "600"),
            ConfirmedCorporateAction(
                isin="INE009A01021",
                action_type=CorporateActionType.BONUS,
                confidence=ConfidenceLevel.HIGH,
                announcement_date=date(2023, 12, 1),
                ex_date=date(2024, 1, 2),
                record_date=date(2024, 1, 2),
                parameters={"bonus_ratio_numerator": "1", "bonus_ratio_denominator": "1"},
                source_preference=Exchange.NSE,
                superseded=False,
            ),
        ]
    )
    outcomes = DiscontinuityDetector().detect(db_session, market_isin="MARKET")
    assert any(o.category.value == "A" for o in outcomes)


def test_category_c_ohlc_integrity_fail(db_session) -> None:
    db_session.add_all(
        [
            _price("MARKET", date(2024, 1, 1), "100"),
            _price("MARKET", date(2024, 1, 2), "99"),
            _price("INE009A01021", date(2024, 1, 1), "100"),
            _price("INE009A01021", date(2024, 1, 2), "95", high="90", low="96"),
        ]
    )
    outcomes = DiscontinuityDetector().detect(db_session, market_isin="MARKET")
    assert any(o.category.value == "C" for o in outcomes)


def test_exclusion_date_relaxes_thresholds(db_session) -> None:
    db_session.add_all(
        [
            _price("MARKET", date(2024, 3, 20), "100"),
            _price("MARKET", date(2024, 3, 21), "96"),
            _price("INE009A01021", date(2024, 3, 20), "100"),
            _price("INE009A01021", date(2024, 3, 21), "60"),
            ExclusionDate(event_date=date(2024, 3, 21), reason="circuit breaker", severity="HIGH"),
        ]
    )
    outcomes = DiscontinuityDetector().detect(db_session, market_isin="MARKET")
    # Because threshold relaxes to -50%, this -40% move should not be category A.
    assert not any(o.category.value == "A" and o.event_date == date(2024, 3, 21) for o in outcomes)
