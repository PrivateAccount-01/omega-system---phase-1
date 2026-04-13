from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from omegadata.db.models import ManualReviewQueue, PriceRecord
from omegadata.domain import PublicationState, ReviewBlockScope
from omegadata.track_b.review_policy import ReviewPolicy, load_review_policies


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
    def __init__(self) -> None:
        self._policy_set = load_review_policies()

    def _policy_for_category(self, category: str) -> ReviewPolicy:
        return self._policy_set.for_category(category)

    @staticmethod
    def _resolution_decision(review: ManualReviewQueue) -> str | None:
        payload = dict(review.payload or {})
        resolution = payload.get("resolution")
        if not isinstance(resolution, dict):
            return None
        decision = resolution.get("decision")
        return None if decision is None else str(decision)

    def _applies(self, review: ManualReviewQueue, trade_date: date) -> bool:
        policy = self._policy_for_category(review.category)
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
        decision = self._resolution_decision(review)
        if decision in {"FALSE_POSITIVE", "OVERRIDE_APPROVED"}:
            return False
        return requires_reprocess and payload.get("reprocess_status") != "COMPLETED"

    def active_reviews_for_isin(
        self,
        session: Session,
        isin: str,
    ) -> list[tuple[ManualReviewQueue, ReviewPolicy]]:
        reviews = session.scalars(
            select(ManualReviewQueue).where(ManualReviewQueue.isin == isin)
        ).all()
        active: list[tuple[ManualReviewQueue, ReviewPolicy]] = []
        for review in reviews:
            if not self._is_active(review):
                continue
            policy = self._policy_for_category(review.category)
            if not policy.blocks_publication:
                continue
            active.append((review, policy))
        return active

    def blocked_dates(
        self,
        rows: list[PriceRecord],
        reviews_with_policy: list[tuple[ManualReviewQueue, ReviewPolicy]],
    ) -> tuple[set[date], dict[date, list[PublicationBlock]]]:
        if not rows or not reviews_with_policy:
            return set(), {}

        rows_by_date = {row.trade_date: row for row in rows}
        ordered_dates = sorted(rows_by_date)
        blocked: set[date] = set()
        blocks_by_date: dict[date, list[PublicationBlock]] = {}
        instrument_blocks: list[PublicationBlock] = []
        record_blocks: dict[date, list[PublicationBlock]] = {}
        forward_blocks: list[tuple[date, PublicationBlock]] = []

        for review, policy in reviews_with_policy:
            block = PublicationBlock(
                review_id=review.id,
                category=review.category,
                scope=policy.scope,
                reason=review.reason,
                requires_reprocess=policy.requires_reprocess,
            )
            if policy.scope == ReviewBlockScope.INSTRUMENT:
                instrument_blocks.append(block)
                continue
            if review.event_date is None:
                continue
            if policy.scope == ReviewBlockScope.RECORD:
                record_blocks.setdefault(review.event_date, []).append(block)
                continue
            if policy.scope == ReviewBlockScope.FORWARD_SERIES:
                forward_blocks.append((review.event_date, block))

        forward_blocks.sort(key=lambda item: item[0])
        active_forward: list[PublicationBlock] = []
        forward_index = 0
        for trade_date in ordered_dates:
            while forward_index < len(forward_blocks) and forward_blocks[forward_index][0] <= trade_date:
                active_forward.append(forward_blocks[forward_index][1])
                forward_index += 1
            row_blocks = [
                *instrument_blocks,
                *record_blocks.get(trade_date, []),
                *active_forward,
            ]
            if row_blocks:
                blocked.add(trade_date)
                blocks_by_date[trade_date] = row_blocks
        return blocked, blocks_by_date

    def status_for_row(self, session: Session, row: PriceRecord) -> PublicationStatus:
        reviews_with_policy = self.active_reviews_for_isin(session, row.isin)
        _, blocks_by_date = self.blocked_dates([row], reviews_with_policy)
        blocks = blocks_by_date.get(row.trade_date, [])
        state = PublicationState.BLOCKED if blocks else PublicationState.PUBLISHABLE
        return PublicationStatus(isin=row.isin, trade_date=row.trade_date, state=state, blocks=blocks)

    def evaluate_records(
        self,
        session: Session,
        records: list[PriceRecord],
    ) -> tuple[list[PriceRecord], list[PriceRecord], list[tuple[ManualReviewQueue, ReviewPolicy]]]:
        if not records:
            return [], [], []
        reviews_with_policy = self.active_reviews_for_isin(session, records[0].isin)
        blocked_dates, _ = self.blocked_dates(records, reviews_with_policy)
        publishable = [row for row in records if row.trade_date not in blocked_dates]
        blocked_rows = [row for row in records if row.trade_date in blocked_dates]
        return publishable, blocked_rows, reviews_with_policy

    def filter_records(
        self,
        session: Session,
        records: list[PriceRecord],
    ) -> tuple[list[PriceRecord], int, tuple[date, date] | None]:
        publishable, blocked_rows, _ = self.evaluate_records(session, records)
        if not blocked_rows:
            return publishable, 0, None
        blocked_dates = sorted({row.trade_date for row in blocked_rows})
        return publishable, len(blocked_rows), (blocked_dates[0], blocked_dates[-1])
