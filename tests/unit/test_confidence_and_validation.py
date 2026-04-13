from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from omegadata.db.models import CorporateActionStaging, ManualReviewQueue, PriceRecord
from omegadata.domain import (
    CorporateActionType,
    DiscontinuityCategory,
    Exchange,
    QueryContext,
)
from omegadata.track_b.confidence import ConfidenceInputs, ConfidenceScorer
from omegadata.track_b.cross_source_validation import CrossSourceValidator


def test_confidence_floor_and_thresholds() -> None:
    scorer = ConfidenceScorer()
    score = scorer.compute_score(
        ConfidenceInputs(
            is_secondary_source=True,
            cross_validation_available=False,
            cross_validation_discrepancy_pct=Decimal("0.01"),
            cross_validation_failed=True,
            has_medium_ca=True,
            has_low_ca=True,
            rights_subscription_fallback_zero=True,
            is_gap_fill=True,
            is_reconstructed_universe=True,
            discontinuity_category=DiscontinuityCategory.C,
        )
    )
    assert score == Decimal("0.00")
    assert scorer.enforce_context(Decimal("0.90"), QueryContext.LIVE_SIGNAL)
    assert not scorer.enforce_context(Decimal("0.89"), QueryContext.LIVE_SIGNAL)


def test_cross_source_price_validation_warn_and_fail(db_session) -> None:
    db_session.add_all(
        [
            PriceRecord(
                isin="INE009A01021",
                exchange=Exchange.NSE,
                trade_date=date(2024, 1, 1),
                open_price=Decimal("100"),
                high_price=Decimal("100"),
                low_price=Decimal("100"),
                close_price=Decimal("100"),
                volume=Decimal("20000"),
                raw_source="nse_bhavcopy",
                confidence_score=Decimal("1.00"),
            ),
                PriceRecord(
                    isin="INE009A01021",
                    exchange=Exchange.BSE,
                    trade_date=date(2024, 1, 1),
                    open_price=Decimal("101.50"),
                    high_price=Decimal("101.50"),
                    low_price=Decimal("101.50"),
                    close_price=Decimal("101.50"),
                    volume=Decimal("20000"),
                    raw_source="bse_bhavcopy",
                    confidence_score=Decimal("1.00"),
                ),
            PriceRecord(
                isin="INE009A01021",
                exchange=Exchange.NSE,
                trade_date=date(2024, 1, 2),
                open_price=Decimal("100"),
                high_price=Decimal("100"),
                low_price=Decimal("100"),
                close_price=Decimal("100"),
                volume=Decimal("20000"),
                raw_source="nse_bhavcopy",
                confidence_score=Decimal("1.00"),
            ),
            PriceRecord(
                isin="INE009A01021",
                exchange=Exchange.BSE,
                trade_date=date(2024, 1, 2),
                open_price=Decimal("110"),
                high_price=Decimal("110"),
                low_price=Decimal("110"),
                close_price=Decimal("110"),
                volume=Decimal("20000"),
                raw_source="bse_bhavcopy",
                confidence_score=Decimal("1.00"),
            ),
        ]
    )
    outcomes = CrossSourceValidator().validate_nse_bse_prices(db_session, "INE009A01021")
    assert any(o.result.value == "WARN" for o in outcomes)
    assert any(o.result.value == "FAIL" for o in outcomes)
    failed_row = db_session.scalar(
        select(PriceRecord)
        .where(PriceRecord.isin == "INE009A01021")
        .where(PriceRecord.exchange == Exchange.NSE)
        .where(PriceRecord.trade_date == date(2024, 1, 2))
    )
    assert failed_row is not None
    assert Decimal(str(failed_row.confidence_score)) == Decimal("1.00")


def test_cross_source_price_validation_uses_dynamic_low_liquidity_tolerance(db_session) -> None:
    db_session.add_all(
        [
            PriceRecord(
                isin="INELOW010001",
                exchange=Exchange.NSE,
                trade_date=date(2024, 1, 1),
                open_price=Decimal("10"),
                high_price=Decimal("10"),
                low_price=Decimal("10"),
                close_price=Decimal("10"),
                volume=Decimal("100"),
                raw_source="nse_bhavcopy",
                confidence_score=Decimal("1.00"),
            ),
            PriceRecord(
                isin="INELOW010001",
                exchange=Exchange.BSE,
                trade_date=date(2024, 1, 1),
                open_price=Decimal("10.03"),
                high_price=Decimal("10.03"),
                low_price=Decimal("10.03"),
                close_price=Decimal("10.03"),
                volume=Decimal("100"),
                raw_source="bse_bhavcopy",
                confidence_score=Decimal("1.00"),
            ),
        ]
    )

    outcomes = CrossSourceValidator().validate_nse_bse_prices(db_session, "INELOW010001")
    close_outcome = next(
        outcome for outcome in outcomes if outcome.field == "close_price" and outcome.data_date == date(2024, 1, 1)
    )
    assert close_outcome.result.value == "PASS"


def test_cross_source_price_validation_uses_two_sided_liquidity_not_max_side(db_session) -> None:
    db_session.add_all(
        [
            PriceRecord(
                isin="INETWOSIDED1",
                exchange=Exchange.NSE,
                trade_date=date(2024, 1, 1),
                open_price=Decimal("100"),
                high_price=Decimal("100"),
                low_price=Decimal("100"),
                close_price=Decimal("100"),
                volume=Decimal("500000"),
                raw_source="nse_bhavcopy",
                confidence_score=Decimal("1.00"),
            ),
            PriceRecord(
                isin="INETWOSIDED1",
                exchange=Exchange.BSE,
                trade_date=date(2024, 1, 1),
                open_price=Decimal("100.30"),
                high_price=Decimal("100.30"),
                low_price=Decimal("100.30"),
                close_price=Decimal("100.30"),
                volume=Decimal("500"),
                raw_source="bse_bhavcopy",
                confidence_score=Decimal("1.00"),
            ),
        ]
    )

    outcomes = CrossSourceValidator().validate_nse_bse_prices(db_session, "INETWOSIDED1")
    close_outcome = next(
        outcome for outcome in outcomes if outcome.field == "close_price" and outcome.data_date == date(2024, 1, 1)
    )
    assert close_outcome.result.value == "PASS"


def test_cross_source_ca_type_mismatch_creates_review(db_session) -> None:
    db_session.add_all(
        [
            CorporateActionStaging(
                source=Exchange.NSE,
                isin="INE009A01021",
                action_type=CorporateActionType.DIVIDEND_CASH,
                announcement_date=date(2024, 1, 1),
                ex_date=date(2024, 1, 2),
                record_date=date(2024, 1, 2),
                payload={"dividend_per_share": "1.25"},
                matched=False,
            ),
            CorporateActionStaging(
                source=Exchange.BSE,
                isin="INE009A01021",
                action_type=CorporateActionType.DIVIDEND_SPECIAL,
                announcement_date=date(2024, 1, 1),
                ex_date=date(2024, 1, 2),
                record_date=date(2024, 1, 2),
                payload={"dividend_per_share": "1.25"},
                matched=False,
            ),
        ]
    )
    CrossSourceValidator().validate_corporate_actions(db_session, "INE009A01021")
    review = db_session.scalar(
        select(ManualReviewQueue).where(ManualReviewQueue.category == "CORPORATE_ACTION_TYPE_FAIL")
    )
    assert review is not None


def test_systematic_disagreement_uses_chronological_order(db_session) -> None:
    inserted = [
        (date(2024, 1, 2), Decimal("99")),
        (date(2024, 1, 1), Decimal("101")),
        (date(2024, 1, 3), Decimal("101")),
        (date(2024, 1, 4), Decimal("101")),
        (date(2024, 1, 5), Decimal("101")),
        (date(2024, 1, 6), Decimal("101")),
    ]
    for trade_date, nse_close in inserted:
        db_session.add(
            PriceRecord(
                isin="INEORDER0012",
                exchange=Exchange.NSE,
                trade_date=trade_date,
                open_price=nse_close,
                high_price=nse_close,
                low_price=nse_close,
                close_price=nse_close,
                volume=Decimal("1000"),
                raw_source="nse_bhavcopy",
                confidence_score=Decimal("1.00"),
            )
        )
        db_session.add(
            PriceRecord(
                isin="INEORDER0012",
                exchange=Exchange.BSE,
                trade_date=trade_date,
                open_price=Decimal("100"),
                high_price=Decimal("100"),
                low_price=Decimal("100"),
                close_price=Decimal("100"),
                volume=Decimal("1000"),
                raw_source="bse_bhavcopy",
                confidence_score=Decimal("1.00"),
            )
        )

    CrossSourceValidator().validate_nse_bse_prices(db_session, "INEORDER0012")
    review = db_session.scalar(
        select(ManualReviewQueue).where(ManualReviewQueue.category == "SYSTEMATIC_DISAGREEMENT")
    )
    assert review is None
