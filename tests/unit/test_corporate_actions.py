from __future__ import annotations

from datetime import date

from sqlalchemy import select

from omegadata.db.models import ManualReviewQueue
from omegadata.domain import CorporateActionType, Exchange
from omegadata.track_b.corporate_actions import CorporateActionService


def test_dual_source_high_confidence_confirmation(db_session) -> None:
    svc = CorporateActionService()
    payload = {
        "isin": "INE009A01021",
        "ex_date": "2018-06-14",
        "record_date": "2018-06-16",
        "bonus_ratio_numerator": "1",
        "bonus_ratio_denominator": "1",
        "board_meeting_date": "2018-04-13",
    }
    svc.add_staging_record(
        db_session,
        Exchange.NSE,
        "INE009A01021",
        CorporateActionType.BONUS,
        date(2018, 4, 13),
        date(2018, 6, 14),
        date(2018, 6, 16),
        payload,
    )
    svc.add_staging_record(
        db_session,
        Exchange.BSE,
        "INE009A01021",
        CorporateActionType.BONUS,
        date(2018, 4, 13),
        date(2018, 6, 14),
        date(2018, 6, 16),
        payload,
    )
    results = svc.run_daily_confirmation(db_session, as_of=date(2018, 6, 14))
    assert len(results) == 1
    assert results[0].confidence.value == "HIGH"


def test_required_fields_missing_goes_to_review(db_session) -> None:
    svc = CorporateActionService()
    svc.add_staging_record(
        db_session,
        Exchange.NSE,
        "INE009A01021",
        CorporateActionType.RIGHTS,
        date(2020, 1, 1),
        date(2020, 2, 1),
        date(2020, 2, 2),
        payload={"isin": "INE009A01021", "ex_date": "2020-02-01"},
    )
    svc.run_daily_confirmation(db_session, as_of=date(2020, 2, 3))
    review = db_session.scalar(
        select(ManualReviewQueue).where(ManualReviewQueue.category == "CORPORATE_ACTION_REQUIRED_FIELDS")
    )
    assert review is not None
    assert review.category == "CORPORATE_ACTION_REQUIRED_FIELDS"


def test_immutability_correction(db_session) -> None:
    svc = CorporateActionService()
    payload = {
        "isin": "INE009A01021",
        "ex_date": "2018-06-14",
        "record_date": "2018-06-16",
        "bonus_ratio_numerator": "1",
        "bonus_ratio_denominator": "1",
        "board_meeting_date": "2018-04-13",
    }
    stage = svc.add_staging_record(
        db_session,
        Exchange.NSE,
        "INE009A01021",
        CorporateActionType.BONUS,
        date(2018, 4, 13),
        date(2018, 6, 14),
        date(2018, 6, 16),
        payload,
    )
    svc.add_staging_record(
        db_session,
        Exchange.BSE,
        "INE009A01021",
        CorporateActionType.BONUS,
        date(2018, 4, 13),
        date(2018, 6, 14),
        date(2018, 6, 16),
        payload,
    )
    svc.run_daily_confirmation(db_session, as_of=date(2018, 6, 14))
    assert stage.source == Exchange.NSE
    active = svc.get_active_actions(db_session, "INE009A01021")
    assert len(active) == 1
    corrected = svc.apply_correction(
        db_session,
        original_id=active[0].id,
        corrected_parameters={**payload, "bonus_ratio_denominator": "2"},
    )
    db_session.flush()
    assert corrected.supersedes_id == active[0].id


def test_multiple_actions_same_date_are_paired_by_event_identity(db_session) -> None:
    svc = CorporateActionService()
    bonus_payload = {
        "isin": "INE009A01021",
        "ex_date": "2018-06-14",
        "record_date": "2018-06-16",
        "bonus_ratio_numerator": "1",
        "bonus_ratio_denominator": "1",
        "board_meeting_date": "2018-04-13",
    }
    split_payload = {
        "isin": "INE009A01021",
        "ex_date": "2018-06-14",
        "old_face_value": "10",
        "new_face_value": "5",
    }
    svc.add_staging_record(
        db_session,
        Exchange.NSE,
        "INE009A01021",
        CorporateActionType.BONUS,
        date(2018, 4, 13),
        date(2018, 6, 14),
        date(2018, 6, 16),
        bonus_payload,
    )
    svc.add_staging_record(
        db_session,
        Exchange.BSE,
        "INE009A01021",
        CorporateActionType.SPLIT,
        date(2018, 4, 13),
        date(2018, 6, 14),
        date(2018, 6, 14),
        split_payload,
    )
    svc.add_staging_record(
        db_session,
        Exchange.NSE,
        "INE009A01021",
        CorporateActionType.SPLIT,
        date(2018, 4, 13),
        date(2018, 6, 14),
        date(2018, 6, 14),
        split_payload,
    )
    svc.add_staging_record(
        db_session,
        Exchange.BSE,
        "INE009A01021",
        CorporateActionType.BONUS,
        date(2018, 4, 13),
        date(2018, 6, 14),
        date(2018, 6, 16),
        bonus_payload,
    )

    results = svc.run_daily_confirmation(db_session, as_of=date(2018, 6, 14))
    assert len(results) == 2


def test_parameter_mismatch_queues_review_but_confirms_pair(db_session) -> None:
    svc = CorporateActionService()
    nse_payload = {
        "isin": "INE009A01021",
        "ex_date": "2018-06-14",
        "record_date": "2018-06-16",
        "bonus_ratio_numerator": "1",
        "bonus_ratio_denominator": "1",
        "board_meeting_date": "2018-04-13",
    }
    bse_payload = {
        **nse_payload,
        "bonus_ratio_denominator": "2",
    }
    svc.add_staging_record(
        db_session,
        Exchange.NSE,
        "INE009A01021",
        CorporateActionType.BONUS,
        date(2018, 4, 13),
        date(2018, 6, 14),
        date(2018, 6, 16),
        nse_payload,
    )
    svc.add_staging_record(
        db_session,
        Exchange.BSE,
        "INE009A01021",
        CorporateActionType.BONUS,
        date(2018, 4, 13),
        date(2018, 6, 14),
        date(2018, 6, 16),
        bse_payload,
    )

    results = svc.run_daily_confirmation(db_session, as_of=date(2018, 6, 14))
    review = db_session.scalar(
        select(ManualReviewQueue).where(ManualReviewQueue.category == "CORPORATE_ACTION_PARAMETER_MISMATCH")
    )

    assert len(results) == 1
    assert results[0].confidence.value == "MEDIUM"
    assert review is not None


def test_missing_required_fields_block_confirmation_for_matched_pair(db_session) -> None:
    svc = CorporateActionService()
    bad_payload = {
        "isin": "INE009A01021",
        "ex_date": "2020-02-01",
    }
    svc.add_staging_record(
        db_session,
        Exchange.NSE,
        "INE009A01021",
        CorporateActionType.RIGHTS,
        date(2020, 1, 1),
        date(2020, 2, 1),
        date(2020, 2, 2),
        bad_payload,
    )
    svc.add_staging_record(
        db_session,
        Exchange.BSE,
        "INE009A01021",
        CorporateActionType.RIGHTS,
        date(2020, 1, 1),
        date(2020, 2, 1),
        date(2020, 2, 2),
        bad_payload,
    )

    results = svc.run_daily_confirmation(db_session, as_of=date(2020, 2, 3))
    review = db_session.scalar(
        select(ManualReviewQueue).where(ManualReviewQueue.category == "CORPORATE_ACTION_REQUIRED_FIELDS")
    )

    assert results == []
    assert review is not None
