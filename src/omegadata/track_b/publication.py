from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from omegadata.db.models import ManualReviewQueue, PriceRecord
from omegadata.domain import PublicationState, ReviewBlockScope
from omegadata.track_b.review_policy import load_review_policies


@dataclass(frozen=True)
class PublicationBlock:
    review_id: int
    category: str
    scope: ReviewBlockScope
    reason: str
    requires_reprocess: bool


@dataclass(frozen=True)
class PublicationStatus:
    isin: str
    trade_date: date
    state: PublicationState
    blocks: list[PublicationBlock]


class PublicationService:
    def _applies(self, review: ManualReviewQueue, trade_date: date) -> bool:
        policy = load_review_policies().for_category(review.category)
        event_date = review.event_date
        if event_date is None:
            return policy.scope == ReviewBlockScope.INSTRUMENT
        if policy.scope == ReviewBlockScope.INSTRUMENT:
            return True
        if policy.scope == ReviewBlockScope.RECORD:
            return trade_date == event_date
        if policy.scope == ReviewBlockScope.FORWARD_SERIES:
            return trade_date >= event_date
        return False

    def _is_active(self, review: ManualReviewQueue) -> bool:
        payload = dict(review.payload or {})
        requires_reprocess = bool(payload.get("requires_reprocess", False))
        if not review.resolved:
            return True
        return requires_reprocess and payload.get("reprocess_status") != "COMPLETED"

    def status_for_row(self, session: Session, row: PriceRecord) -> PublicationStatus:
        reviews = session.scalars(
            select(ManualReviewQueue).where(ManualReviewQueue.isin == row.isin)
        ).all()
        blocks: list[PublicationBlock] = []
        for review in reviews:
            if not self._is_active(review):
                continue
            policy = load_review_policies().for_category(review.category)
            if not policy.blocks_publication:
                continue
            if not self._applies(review, row.trade_date):
                continue
            blocks.append(
                PublicationBlock(
                    review_id=review.id,
                    category=review.category,
                    scope=policy.scope,
                    reason=review.reason,
                    requires_reprocess=policy.requires_reprocess,
                )
            )
        state = PublicationState.BLOCKED if blocks else PublicationState.PUBLISHABLE
        return PublicationStatus(isin=row.isin, trade_date=row.trade_date, state=state, blocks=blocks)

    def filter_records(
        self,
        session: Session,
        records: list[PriceRecord],
    ) -> tuple[list[PriceRecord], int, tuple[date, date] | None]:
        kept: list[PriceRecord] = []
        blocked_dates: list[date] = []
        for row in records:
            status = self.status_for_row(session, row)
            if status.state == PublicationState.BLOCKED:
                blocked_dates.append(row.trade_date)
                continue
            kept.append(row)
        if not blocked_dates:
            return kept, 0, None
        ordered = sorted(blocked_dates)
        return kept, len(blocked_dates), (ordered[0], ordered[-1])
