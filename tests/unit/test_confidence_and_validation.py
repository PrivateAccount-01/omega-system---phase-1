from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from omegadata.db.models import ConfirmedCorporateAction, ManualReviewQueue, PriceRecord
from omegadata.domain import (
    ConfidenceLevel,
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
                volume=Decimal("100"),
                raw_source="nse_bhavcopy",
                confidence_score=Decimal("1.00"),
            ),
            PriceRecord(
                isin="INE009A01021",
                exchange=Exchange.BSE,
                trade_date=date(2024, 1, 1),
                    open_price=Decimal("100.15"),
                    high_price=Decimal("100.15"),
                    low_price=Decimal("100.15"),
                    close_price=Decimal("100.15"),
                volume=Decimal("100"),
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
                volume=Decimal("100"),
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
                volume=Decimal("100"),
                raw_source="bse_bhavcopy",
                confidence_score=Decimal("1.00"),
            ),
        ]
    )
    outcomes = CrossSourceValidator().validate_nse_bse_prices(db_session, "INE009A01021")
    assert any(o.result.value == "WARN" for o in outcomes)
    assert any(o.result.value == "FAIL" for o in outcomes)


def test_cross_source_ca_type_mismatch_creates_review(db_session) -> None:
    db_session.add_all(
        [
            ConfirmedCorporateAction(
                isin="INE009A01021",
                action_type=CorporateActionType.BONUS,
                confidence=ConfidenceLevel.HIGH,
                announcement_date=date(2024, 1, 1),
                ex_date=date(2024, 1, 2),
                record_date=date(2024, 1, 2),
                parameters={"bonus_ratio_numerator": "1", "bonus_ratio_denominator": "1"},
                source_preference=Exchange.NSE,
                superseded=False,
            ),
            ConfirmedCorporateAction(
                isin="INE009A01021",
                action_type=CorporateActionType.SPLIT,
                confidence=ConfidenceLevel.HIGH,
                announcement_date=date(2024, 1, 1),
                ex_date=date(2024, 1, 2),
                record_date=date(2024, 1, 2),
                parameters={"old_face_value": "10", "new_face_value": "5"},
                source_preference=Exchange.BSE,
                superseded=False,
            ),
        ]
    )
    CrossSourceValidator().validate_corporate_actions(db_session, "INE009A01021")
    review = db_session.scalar(
        select(ManualReviewQueue).where(ManualReviewQueue.category == "CORPORATE_ACTION_TYPE_FAIL")
    )
    assert review is not None
