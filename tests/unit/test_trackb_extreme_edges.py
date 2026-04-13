from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select

from omegadata.db.models import (
    ConfirmedCorporateAction,
    CorporateActionStaging,
    ManualReviewQueue,
    PriceRecord,
    ValidationAuditLog,
)
from omegadata.domain import ConfidenceLevel, CorporateActionType, Exchange, ValidationResult
from omegadata.track_b.adjustment_engine import PriceAdjustmentEngine
from omegadata.track_b.corporate_actions import CorporateActionService
from omegadata.track_b.cross_source_validation import CrossSourceValidator


def _price(db_session, trade_date: date, close: str) -> None:
    db_session.add(
        PriceRecord(
            isin="INE009A01021",
            exchange=Exchange.NSE,
            trade_date=trade_date,
            open_price=Decimal(close),
            high_price=Decimal(close),
            low_price=Decimal(close),
            close_price=Decimal(close),
            volume=Decimal("100"),
            raw_source="nse_bhavcopy",
            confidence_score=Decimal("1.00"),
        )
    )


def test_staging_validation_warn_when_bse_missing(db_session) -> None:
    db_session.add(
        CorporateActionStaging(
            source=Exchange.NSE,
            isin="INE009A01021",
            action_type=CorporateActionType.BONUS,
            announcement_date=date(2026, 4, 1),
            ex_date=date(2026, 4, 2),
            record_date=date(2026, 4, 2),
            payload={"isin": "INE009A01021", "bonus_ratio_numerator": "1", "bonus_ratio_denominator": "1"},
            matched=False,
        )
    )

    outcomes = CrossSourceValidator().validate_corporate_actions(db_session, "INE009A01021")

    assert outcomes
    assert any(o.result == ValidationResult.WARN for o in outcomes)
    audit = db_session.scalar(
        select(ValidationAuditLog).where(ValidationAuditLog.field_compared == "corporate_action_coverage")
    )
    assert audit is not None
    assert audit.result == ValidationResult.WARN


def test_staging_validation_date_gap_fail(db_session) -> None:
    db_session.add_all(
        [
            CorporateActionStaging(
                source=Exchange.NSE,
                isin="INE009A01021",
                action_type=CorporateActionType.BONUS,
                announcement_date=date(2026, 4, 1),
                ex_date=date(2026, 4, 2),
                record_date=date(2026, 4, 2),
                payload={"isin": "INE009A01021", "bonus_ratio_numerator": "1", "bonus_ratio_denominator": "1"},
                matched=False,
            ),
            CorporateActionStaging(
                source=Exchange.BSE,
                isin="INE009A01021",
                action_type=CorporateActionType.BONUS,
                announcement_date=date(2026, 4, 15),
                ex_date=date(2026, 4, 15),
                record_date=date(2026, 4, 15),
                payload={"isin": "INE009A01021", "bonus_ratio_numerator": "1", "bonus_ratio_denominator": "1"},
                matched=False,
            ),
        ]
    )

    outcomes = CrossSourceValidator().validate_corporate_actions(db_session, "INE009A01021")

    assert any(o.result == ValidationResult.FAIL for o in outcomes)
    review = db_session.scalar(
        select(ManualReviewQueue).where(ManualReviewQueue.category == "CORPORATE_ACTION_TYPE_FAIL")
    )
    assert review is not None


def test_staging_numeric_payload_warn_band(db_session) -> None:
    db_session.add_all(
        [
            CorporateActionStaging(
                source=Exchange.NSE,
                isin="INE009A01021",
                action_type=CorporateActionType.RIGHTS,
                announcement_date=date(2026, 4, 1),
                ex_date=date(2026, 4, 2),
                record_date=date(2026, 4, 2),
                payload={"isin": "INE009A01021", "issue_price": "102", "rights_ratio_numerator": "1", "rights_ratio_denominator": "4"},
                matched=False,
            ),
            CorporateActionStaging(
                source=Exchange.BSE,
                isin="INE009A01021",
                action_type=CorporateActionType.RIGHTS,
                announcement_date=date(2026, 4, 1),
                ex_date=date(2026, 4, 2),
                record_date=date(2026, 4, 2),
                payload={"isin": "INE009A01021", "issue_price": "100", "rights_ratio_numerator": "1", "rights_ratio_denominator": "4"},
                matched=False,
            ),
        ]
    )

    outcomes = CrossSourceValidator().validate_corporate_actions(db_session, "INE009A01021")

    price_outcomes = [o for o in outcomes if o.field == "issue_price"]
    assert price_outcomes
    assert any(o.result == ValidationResult.WARN for o in price_outcomes)


def test_validation_logs_are_idempotent_on_repeat(db_session) -> None:
    db_session.add_all(
        [
            CorporateActionStaging(
                source=Exchange.NSE,
                isin="INE009A01021",
                action_type=CorporateActionType.RIGHTS,
                announcement_date=date(2026, 4, 1),
                ex_date=date(2026, 4, 2),
                record_date=date(2026, 4, 2),
                payload={"isin": "INE009A01021", "issue_price": "102", "rights_ratio_numerator": "1", "rights_ratio_denominator": "4"},
                matched=False,
            ),
            CorporateActionStaging(
                source=Exchange.BSE,
                isin="INE009A01021",
                action_type=CorporateActionType.RIGHTS,
                announcement_date=date(2026, 4, 1),
                ex_date=date(2026, 4, 2),
                record_date=date(2026, 4, 2),
                payload={"isin": "INE009A01021", "issue_price": "100", "rights_ratio_numerator": "1", "rights_ratio_denominator": "4"},
                matched=False,
            ),
        ]
    )

    validator = CrossSourceValidator()
    validator.validate_corporate_actions(db_session, "INE009A01021")
    count_after_first = int(
        db_session.scalar(select(func.count()).select_from(ValidationAuditLog)) or 0
    )

    validator.validate_corporate_actions(db_session, "INE009A01021")
    count_after_second = int(
        db_session.scalar(select(func.count()).select_from(ValidationAuditLog)) or 0
    )

    assert count_after_first > 0
    assert count_after_second == count_after_first


def test_adjustment_reverse_split_and_invalid_demerger(db_session) -> None:
    _price(db_session, date(2026, 4, 1), "100")
    _price(db_session, date(2026, 4, 2), "200")
    _price(db_session, date(2026, 4, 3), "180")

    db_session.add_all(
        [
            ConfirmedCorporateAction(
                isin="INE009A01021",
                action_type=CorporateActionType.SPLIT_REVERSE,
                confidence=ConfidenceLevel.HIGH,
                announcement_date=date(2026, 3, 20),
                ex_date=date(2026, 4, 2),
                record_date=date(2026, 4, 2),
                parameters={"old_face_value": "1", "new_face_value": "2"},
                source_preference=Exchange.NSE,
                superseded=False,
            ),
            ConfirmedCorporateAction(
                isin="INE009A01021",
                action_type=CorporateActionType.DEMERGER_PARENT,
                confidence=ConfidenceLevel.MEDIUM,
                announcement_date=date(2026, 3, 25),
                ex_date=date(2026, 4, 3),
                record_date=date(2026, 4, 3),
                parameters={"parent_value_pre_demerger": "0", "spinoff_value": "20"},
                source_preference=Exchange.NSE,
                superseded=False,
            ),
        ]
    )

    PriceAdjustmentEngine().recompute_adjusted_series(db_session, "INE009A01021")
    row = db_session.scalar(
        select(PriceRecord).where(PriceRecord.trade_date == date(2026, 4, 1))
    )
    assert row is not None
    assert Decimal(str(row.adjusted_close_price)) == Decimal("200.000000")


def test_unmatched_staging_older_than_48h_is_escalated(db_session) -> None:
    svc = CorporateActionService()
    rec = svc.add_staging_record(
        db_session,
        source=Exchange.BSE_ONLY,
        isin="INE009A01021",
        action_type=CorporateActionType.RIGHTS,
        announcement_date=date(2026, 4, 1),
        ex_date=date(2026, 4, 2),
        record_date=date(2026, 4, 2),
        payload={"isin": "INE009A01021", "ex_date": "2026-04-02", "record_date": "2026-04-02"},
    )
    rec.fetched_at = datetime.utcnow() - timedelta(days=3)

    svc.run_daily_confirmation(db_session, as_of=date(2026, 4, 8))
    review = db_session.scalar(
        select(ManualReviewQueue).where(ManualReviewQueue.category == "CORPORATE_ACTION_UNMATCHED")
    )
    assert review is not None


def test_validator_treats_bse_only_as_valid_bse_candidate(db_session) -> None:
    db_session.add_all(
        [
            CorporateActionStaging(
                source=Exchange.NSE,
                isin="INE009A01021",
                action_type=CorporateActionType.RIGHTS,
                announcement_date=date(2026, 4, 1),
                ex_date=date(2026, 4, 2),
                record_date=date(2026, 4, 2),
                payload={"isin": "INE009A01021", "issue_price": "100", "rights_ratio_numerator": "1", "rights_ratio_denominator": "4"},
                matched=False,
            ),
            CorporateActionStaging(
                source=Exchange.BSE_ONLY,
                isin="INE009A01021",
                action_type=CorporateActionType.RIGHTS,
                announcement_date=date(2026, 4, 1),
                ex_date=date(2026, 4, 2),
                record_date=date(2026, 4, 2),
                payload={"isin": "INE009A01021", "issue_price": "100", "rights_ratio_numerator": "1", "rights_ratio_denominator": "4"},
                matched=False,
            ),
        ]
    )

    outcomes = CrossSourceValidator().validate_corporate_actions(db_session, "INE009A01021")
    assert any(outcome.result == ValidationResult.PASS for outcome in outcomes)
    coverage_warn = db_session.scalar(
        select(ValidationAuditLog).where(ValidationAuditLog.field_compared == "corporate_action_coverage")
    )
    assert coverage_warn is None


def test_unmatched_validation_requires_high_similarity_before_type_fail(db_session) -> None:
    db_session.add_all(
        [
            CorporateActionStaging(
                source=Exchange.NSE,
                isin="INE009A01021",
                action_type=CorporateActionType.BONUS,
                announcement_date=date(2026, 4, 1),
                ex_date=date(2026, 4, 2),
                record_date=date(2026, 4, 2),
                payload={"isin": "INE009A01021", "bonus_ratio_numerator": "1", "bonus_ratio_denominator": "1"},
                matched=False,
            ),
            CorporateActionStaging(
                source=Exchange.BSE,
                isin="INE009A01021",
                action_type=CorporateActionType.SPLIT,
                announcement_date=date(2026, 4, 1),
                ex_date=date(2026, 4, 2),
                record_date=date(2026, 4, 2),
                payload={"isin": "INE009A01021", "old_face_value": "10", "new_face_value": "5"},
                matched=False,
            ),
        ]
    )

    outcomes = CrossSourceValidator().validate_corporate_actions(db_session, "INE009A01021")
    assert any(outcome.result == ValidationResult.WARN for outcome in outcomes)
    assert not any(outcome.result == ValidationResult.FAIL for outcome in outcomes)


def test_unmatched_validation_tracks_false_negative_risk(db_session) -> None:
    db_session.add_all(
        [
            CorporateActionStaging(
                source=Exchange.NSE,
                isin="INE009A01021",
                action_type=CorporateActionType.DIVIDEND_CASH,
                announcement_date=date(2026, 4, 1),
                ex_date=date(2026, 4, 8),
                record_date=date(2026, 4, 8),
                payload={"isin": "INE009A01021", "dividend_per_share": "1.25"},
                matched=False,
            ),
            CorporateActionStaging(
                source=Exchange.BSE,
                isin="INE009A01021",
                action_type=CorporateActionType.DIVIDEND_SPECIAL,
                announcement_date=date(2026, 4, 1),
                ex_date=date(2026, 4, 2),
                record_date=date(2026, 4, 2),
                payload={"isin": "INE009A01021", "dividend_per_share": "1.25"},
                matched=False,
            ),
        ]
    )

    outcomes = CrossSourceValidator().validate_corporate_actions(db_session, "INE009A01021")
    assert any(outcome.field == "corporate_action_false_negative_risk" for outcome in outcomes)
    audit = db_session.scalar(
        select(ValidationAuditLog).where(ValidationAuditLog.field_compared == "corporate_action_false_negative_risk")
    )
    assert audit is not None
    review = db_session.scalar(
        select(ManualReviewQueue).where(ManualReviewQueue.category == "CORPORATE_ACTION_FALSE_NEGATIVE_RISK")
    )
    assert review is not None
