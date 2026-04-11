from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from omegadata.db.models import ConfirmedCorporateAction, CorporateActionStaging, ManualReviewQueue
from omegadata.domain import ConfidenceLevel, CorporateActionType, Exchange

REQUIRED_FIELDS: dict[CorporateActionType, tuple[str, ...]] = {
    CorporateActionType.BONUS: (
        "isin",
        "ex_date",
        "record_date",
        "bonus_ratio_numerator",
        "bonus_ratio_denominator",
        "board_meeting_date",
    ),
    CorporateActionType.SPLIT: ("isin", "ex_date", "old_face_value", "new_face_value"),
    CorporateActionType.RIGHTS: (
        "isin",
        "ex_date",
        "record_date",
        "rights_ratio_numerator",
        "rights_ratio_denominator",
        "issue_price",
        "issue_type",
        "subscription_close_date",
    ),
    CorporateActionType.MERGER_TARGET: (
        "isin",
        "merger_effective_date",
        "acquirer_isin",
        "swap_ratio",
        "cash_component",
    ),
    CorporateActionType.DEMERGER_PARENT: ("isin", "ex_date", "spinoff_isin", "demerger_ratio"),
}


@dataclass(frozen=True)
class ConfirmationResult:
    confirmed_id: int
    confidence: ConfidenceLevel


class CorporateActionService:
    @staticmethod
    def _validate_required_fields(action_type: CorporateActionType, payload: Mapping[str, object]) -> list[str]:
        required = REQUIRED_FIELDS.get(action_type, ("isin", "ex_date"))
        missing = [field for field in required if payload.get(field) in (None, "")]
        return missing

    @staticmethod
    def _review_exists(
        session: Session,
        *,
        category: str,
        isin: str | None,
        event_date: date | None,
        reason: str,
    ) -> bool:
        review_id = session.scalar(
            select(ManualReviewQueue.id)
            .where(ManualReviewQueue.category == category)
            .where(ManualReviewQueue.isin == isin)
            .where(ManualReviewQueue.event_date == event_date)
            .where(ManualReviewQueue.reason == reason)
            .where(ManualReviewQueue.resolved.is_(False))
        )
        return review_id is not None

    def _queue_review(
        self,
        session: Session,
        *,
        category: str,
        isin: str | None,
        event_date: date | None,
        reason: str,
        payload: dict[str, str],
    ) -> None:
        if self._review_exists(
            session,
            category=category,
            isin=isin,
            event_date=event_date,
            reason=reason,
        ):
            return
        session.add(
            ManualReviewQueue(
                category=category,
                isin=isin,
                event_date=event_date,
                reason=reason,
                payload=payload,
            )
        )

    def _required_fields_complete(
        self,
        session: Session,
        *,
        row: CorporateActionStaging,
    ) -> bool:
        errors = self._validate_required_fields(row.action_type, row.payload)
        if not errors:
            return True
        self._queue_review(
            session,
            category="CORPORATE_ACTION_REQUIRED_FIELDS",
            isin=row.isin,
            event_date=row.ex_date,
            reason="Missing required fields in corporate action payload",
            payload={"missing_fields": ",".join(errors), "source": row.source.value},
        )
        return False

    def add_staging_record(
        self,
        session: Session,
        source: Exchange,
        isin: str,
        action_type: CorporateActionType,
        announcement_date: date | None,
        ex_date: date | None,
        record_date: date | None,
        payload: dict[str, object],
    ) -> CorporateActionStaging:
        record = CorporateActionStaging(
            source=source,
            isin=isin,
            action_type=action_type,
            announcement_date=announcement_date,
            ex_date=ex_date,
            record_date=record_date,
            payload={k: (None if v is None else str(v)) for k, v in payload.items()},
        )
        session.add(record)
        return record

    def run_daily_confirmation(self, session: Session, as_of: date) -> list[ConfirmationResult]:
        staged = session.scalars(
            select(CorporateActionStaging).where(CorporateActionStaging.matched.is_(False))
        ).all()

        grouped: dict[tuple[str, date | None], list[CorporateActionStaging]] = {}
        for row in staged:
            grouped.setdefault((row.isin, row.ex_date), []).append(row)

        results: list[ConfirmationResult] = []
        for (_isin, _ex_date), rows in grouped.items():
            nse = next((r for r in rows if r.source == Exchange.NSE), None)
            bse = next((r for r in rows if r.source in {Exchange.BSE, Exchange.BSE_ONLY}), None)

            if nse and bse:
                confirmed = self._confirm_pair(session=session, nse=nse, bse=bse)
                if confirmed is not None:
                    results.append(confirmed)
                continue

            lone = nse or bse or rows[0]
            if not self._is_stale_unmatched(lone, as_of):
                continue

            self._queue_review(
                session,
                category="CORPORATE_ACTION_UNMATCHED",
                isin=lone.isin,
                event_date=lone.ex_date,
                reason="Unmatched staging record older than 48 hours",
                payload={"source": lone.source.value, "action_type": lone.action_type.value},
            )
            self._required_fields_complete(session, row=lone)
            if lone.source != Exchange.NSE:
                self._queue_review(
                    session,
                    category="CORPORATE_ACTION_SOURCE_GAP",
                    isin=lone.isin,
                    event_date=lone.ex_date,
                    reason="BSE record found without NSE match",
                    payload={"action_type": lone.action_type.value},
                )

        return results

    @staticmethod
    def _is_stale_unmatched(row: CorporateActionStaging, as_of: date) -> bool:
        cutoff = as_of.toordinal() - 2
        candidate_dates = [
            d
            for d in (
                row.ex_date,
                row.record_date,
                row.announcement_date,
                row.fetched_at.date(),
            )
            if d is not None and d <= as_of
        ]
        if not candidate_dates:
            return False
        return min(candidate_dates).toordinal() <= cutoff

    def _confirm_pair(
        self,
        session: Session,
        nse: CorporateActionStaging,
        bse: CorporateActionStaging,
    ) -> ConfirmationResult | None:
        if nse.action_type != bse.action_type:
            confidence = ConfidenceLevel.MEDIUM
            self._queue_review(
                session,
                category="CORPORATE_ACTION_TYPE_MISMATCH",
                isin=nse.isin,
                event_date=nse.ex_date,
                reason="NSE and BSE action type mismatch",
                payload={"nse": nse.action_type.value, "bse": bse.action_type.value},
            )
        else:
            mismatch = self._payload_mismatch(nse.payload, bse.payload)
            confidence = ConfidenceLevel.HIGH if not mismatch else ConfidenceLevel.MEDIUM
            if mismatch:
                self._queue_review(
                    session,
                    category="CORPORATE_ACTION_PARAMETER_MISMATCH",
                    isin=nse.isin,
                    event_date=nse.ex_date,
                    reason="NSE and BSE corporate action parameters disagree",
                    payload={"differences": ",".join(mismatch)},
                )

        if not self._required_fields_complete(session, row=nse):
            return None

        confirmed = ConfirmedCorporateAction(
            isin=nse.isin,
            action_type=nse.action_type,
            confidence=confidence,
            announcement_date=nse.announcement_date or bse.announcement_date,
            ex_date=nse.ex_date or bse.ex_date,
            record_date=nse.record_date or bse.record_date,
            parameters=nse.payload,
            source_preference=Exchange.NSE,
            superseded=False,
        )
        nse.matched = True
        bse.matched = True
        session.add(confirmed)
        session.flush()
        return ConfirmationResult(confirmed_id=confirmed.id, confidence=confidence)

    def _confirm_single(
        self, session: Session, row: CorporateActionStaging, confidence: ConfidenceLevel
    ) -> ConfirmationResult:
        if not self._required_fields_complete(session, row=row):
            raise ValueError(f"Corporate action {row.id} cannot be auto-confirmed with missing required fields")

        if confidence == ConfidenceLevel.LOW:
            self._queue_review(
                session,
                category="CORPORATE_ACTION_SOURCE_GAP",
                isin=row.isin,
                event_date=row.ex_date,
                reason="BSE record found without NSE match",
                payload={"action_type": row.action_type.value},
            )

        confirmed = ConfirmedCorporateAction(
            isin=row.isin,
            action_type=row.action_type,
            confidence=confidence,
            announcement_date=row.announcement_date,
            ex_date=row.ex_date,
            record_date=row.record_date,
            parameters=row.payload,
            source_preference=row.source,
            superseded=False,
        )
        row.matched = True
        session.add(confirmed)
        session.flush()
        return ConfirmationResult(confirmed_id=confirmed.id, confidence=confidence)

    @staticmethod
    def _payload_mismatch(nse_payload: Mapping[str, object], bse_payload: Mapping[str, object]) -> list[str]:
        mismatches: list[str] = []
        shared_keys = set(nse_payload) & set(bse_payload)
        for key in sorted(shared_keys):
            left = nse_payload.get(key)
            right = bse_payload.get(key)
            if left == right:
                continue

            if CorporateActionService._numerically_close(left, right, tolerance=Decimal("0.01")):
                continue
            mismatches.append(key)
        return mismatches

    @staticmethod
    def _numerically_close(left: object, right: object, tolerance: Decimal) -> bool:
        try:
            left_dec = Decimal(str(left))
            right_dec = Decimal(str(right))
        except Exception:
            return False

        if right_dec == 0:
            return left_dec == 0
        rel = abs((left_dec - right_dec) / right_dec)
        return rel <= tolerance

    def apply_correction(
        self,
        session: Session,
        original_id: int,
        corrected_parameters: dict[str, object],
    ) -> ConfirmedCorporateAction:
        original = session.get(ConfirmedCorporateAction, original_id)
        if original is None:
            raise LookupError(f"No confirmed corporate action with id {original_id}")

        original.superseded = True
        corrected = ConfirmedCorporateAction(
            isin=original.isin,
            action_type=original.action_type,
            confidence=original.confidence,
            announcement_date=original.announcement_date,
            ex_date=original.ex_date,
            record_date=original.record_date,
            parameters={k: (None if v is None else str(v)) for k, v in corrected_parameters.items()},
            source_preference=original.source_preference,
            superseded=False,
            supersedes_id=original.id,
        )
        session.add(corrected)
        return corrected

    def get_active_actions(self, session: Session, isin: str) -> list[ConfirmedCorporateAction]:
        return list(
            session.scalars(
            select(ConfirmedCorporateAction)
            .where(ConfirmedCorporateAction.isin == isin)
            .where(ConfirmedCorporateAction.superseded.is_(False))
            .order_by(ConfirmedCorporateAction.ex_date.asc())
            ).all()
        )

    def get_action_on_date(
        self,
        session: Session,
        isin: str,
        ex_date: date,
    ) -> ConfirmedCorporateAction | None:
        return session.scalar(
            select(ConfirmedCorporateAction)
            .where(and_(
                ConfirmedCorporateAction.isin == isin,
                ConfirmedCorporateAction.ex_date == ex_date,
                ConfirmedCorporateAction.superseded.is_(False),
            ))
        )
