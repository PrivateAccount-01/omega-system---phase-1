from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from omegadata.db.models import DiscontinuityEvent, InstrumentMaster, PriceRecord
from omegadata.domain import Exchange, InstrumentType
from omegadata.track_b.discontinuity import DiscontinuityDetector


def _add_price(db_session, isin: str, trade_date: date, close: Decimal) -> None:
    db_session.add(
        PriceRecord(
            isin=isin,
            exchange=Exchange.NSE,
            trade_date=trade_date,
            open_price=close,
            high_price=close,
            low_price=close,
            close_price=close,
            volume=Decimal("100"),
            raw_source="nse_bhavcopy",
            confidence_score=Decimal("1.00"),
        )
    )


def test_sector_median_beta_fallback_used_for_short_history_stock(db_session) -> None:
    db_session.add_all(
        [
            InstrumentMaster(
                isin="PEERBETA0001",
                company_name="Peer Beta",
                instrument_type=InstrumentType.EQUITY,
                primary_exchange=Exchange.NSE,
                sector_name="IT",
                active=True,
            ),
            InstrumentMaster(
                isin="SHORTBETA001",
                company_name="Short Beta",
                instrument_type=InstrumentType.EQUITY,
                primary_exchange=Exchange.NSE,
                sector_name="IT",
                active=True,
            ),
        ]
    )

    start = date(2026, 1, 1)
    market_close = Decimal("100")
    peer_close = Decimal("100")
    market_returns = [Decimal("0.01"), Decimal("-0.008"), Decimal("0.012"), Decimal("-0.007")]

    _add_price(db_session, "MARKET", start, market_close)
    _add_price(db_session, "PEERBETA0001", start, peer_close)

    for idx in range(1, 75):
        market_ret = market_returns[idx % len(market_returns)]
        peer_ret = market_ret * Decimal("1.8")
        market_close = (market_close * (Decimal("1") + market_ret)).quantize(Decimal("0.000001"))
        peer_close = (peer_close * (Decimal("1") + peer_ret)).quantize(Decimal("0.000001"))
        trade_date = start + timedelta(days=idx)
        _add_price(db_session, "MARKET", trade_date, market_close)
        _add_price(db_session, "PEERBETA0001", trade_date, peer_close)

    _add_price(db_session, "SHORTBETA001", start + timedelta(days=73), Decimal("100"))
    _add_price(db_session, "SHORTBETA001", start + timedelta(days=74), Decimal("55"))

    outcomes = DiscontinuityDetector().detect(db_session, market_isin="MARKET")
    assert any(outcome.isin == "SHORTBETA001" for outcome in outcomes)

    event = db_session.scalar(
        select(DiscontinuityEvent)
        .where(DiscontinuityEvent.isin == "SHORTBETA001")
        .where(DiscontinuityEvent.event_date == start + timedelta(days=74))
    )
    assert event is not None
    assert Decimal(str(event.beta_used)) > Decimal("1.50")
