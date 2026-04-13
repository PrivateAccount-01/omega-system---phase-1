from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from omegadata.config import settings
from omegadata.db.models import ManualReviewQueue
from omegadata.domain import ReviewDecision
from omegadata.track_b.review_policy import ReviewPolicy, load_review_policies


@dataclass(frozen=True)
class ReviewResolution:
    review_id: int
    decision: ReviewDecision
    requires_reprocess: bool
    reprocess_status: str


class ManualReviewService:
    @staticmethod
    def _fingerprint(payload: dict[str, object]) -> str:
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _policy(self, category: str) -> ReviewPolicy:
        return load_review_policies().for_category(category)

    def _reprocess_request_path(self, review_id: int) -> Path:
        root = Path(settings.reprocess_root)
        root.mkdir(parents=True, exist_ok=True)
        return root / f"review_{review_id}.json"

    def review_exists(
        self,
        session: Session,
        *,
        category: str,
        isin: str | None,
        event_date: date | None,
        reason: str,
        payload: dict[str, object],
    ) -> bool:
        fingerprint = self._fingerprint(payload)
        reviews = session.scalars(
            select(ManualReviewQueue)
            .where(ManualReviewQueue.category == category)
            .where(ManualReviewQueue.isin == isin)
            .where(ManualReviewQueue.event_date == event_date)
            .where(ManualReviewQueue.reason == reason)
            .where(ManualReviewQueue.resolved.is_(False))
        ).all()
        for review in reviews:
            review_payload = dict(review.payload or {})
            if review_payload.get("payload_fingerprint") == fingerprint:
                return True
        return False

    def queue_review(
        self,
        session: Session,
        *,
        category: str,
        isin: str | None,
        event_date: date | None,
        reason: str,
        payload: dict[str, object],
    ) -> ManualReviewQueue | None:
        policy_set = load_review_policies()
        policy = policy_set.for_category(category)
        enriched_payload: dict[str, Any] = dict(payload)
        enriched_payload["payload_fingerprint"] = self._fingerprint(payload)
        enriched_payload["policy_version"] = policy_set.version
        enriched_payload["block_scope"] = policy.scope.value
        enriched_payload["blocks_publication"] = policy.blocks_publication
        enriched_payload["requires_reprocess"] = policy.requires_reprocess
        enriched_payload["triage_instructions"] = policy.triage_instructions
        enriched_payload.setdefault(
            "reprocess_status",
            "NOT_REQUIRED" if not policy.requires_reprocess else "REVIEW_PENDING",
        )
        if self.review_exists(
            session,
            category=category,
            isin=isin,
            event_date=event_date,
            reason=reason,
            payload=enriched_payload,
        ):
            return None
        review = ManualReviewQueue(
            category=category,
            isin=isin,
            event_date=event_date,
            reason=reason,
            payload=enriched_payload,
        )
        session.add(review)
        session.flush()
        return review

    def list_open_reviews(self, session: Session) -> list[ManualReviewQueue]:
        return list(
            session.scalars(
                select(ManualReviewQueue)
                .where(ManualReviewQueue.resolved.is_(False))
                .order_by(ManualReviewQueue.created_at.asc(), ManualReviewQueue.id.asc())
            ).all()
        )

    def resolve_review(
        self,
        session: Session,
        *,
        review_id: int,
        decision: ReviewDecision,
        reviewer: str,
        notes: str,
    ) -> ReviewResolution:
        review = session.get(ManualReviewQueue, review_id)
        if review is None:
            raise LookupError(f"No manual review with id {review_id}")

        payload: dict[str, Any] = dict(review.payload or {})
        requires_reprocess = bool(payload.get("requires_reprocess", False))
        now = datetime.now(UTC).isoformat()
        payload["resolution"] = {
            "decision": decision.value,
            "reviewer": reviewer,
            "notes": notes,
            "resolved_at": now,
        }
        review.resolved = True

        if decision in {ReviewDecision.FALSE_POSITIVE, ReviewDecision.OVERRIDE_APPROVED}:
            payload["reprocess_status"] = "NOT_REQUIRED"
        elif requires_reprocess:
            payload["reprocess_status"] = "PENDING"
            request = {
                "review_id": review.id,
                "category": review.category,
                "isin": review.isin,
                "event_date": None if review.event_date is None else review.event_date.isoformat(),
                "requested_at": now,
                "reason": review.reason,
            }
            self._reprocess_request_path(review.id).write_text(json.dumps(request, indent=2), encoding="utf-8")
        else:
            payload["reprocess_status"] = "NOT_REQUIRED"

        review.payload = payload
        session.flush()
        return ReviewResolution(
            review_id=review.id,
            decision=decision,
            requires_reprocess=requires_reprocess,
            reprocess_status=str(payload["reprocess_status"]),
        )

    def complete_reprocess(
        self,
        session: Session,
        *,
        review_id: int,
        completed_by: str,
        notes: str,
    ) -> dict[str, Any]:
        review = session.get(ManualReviewQueue, review_id)
        if review is None:
            raise LookupError(f"No manual review with id {review_id}")

        payload: dict[str, Any] = dict(review.payload or {})
        requires_reprocess = bool(payload.get("requires_reprocess", False))
        if not requires_reprocess:
            raise ValueError(f"Manual review {review_id} does not require reprocess")
        if not review.resolved:
            raise ValueError(f"Manual review {review_id} must be resolved before reprocess completion")
        resolution = payload.get("resolution")
        decision = resolution.get("decision") if isinstance(resolution, dict) else None
        if decision != ReviewDecision.REMEDIATED.value:
            raise ValueError(f"Manual review {review_id} is not in a remediated state")
        if payload.get("reprocess_status") != "PENDING":
            raise ValueError(f"Manual review {review_id} is not awaiting reprocess completion")

        request_path = self._reprocess_request_path(review.id)
        if not request_path.exists():
            raise ValueError(f"Manual review {review_id} has no pending reprocess request artifact")

        payload["reprocess_status"] = "COMPLETED"
        payload["reprocess_completed"] = {
            "completed_by": completed_by,
            "notes": notes,
            "completed_at": datetime.now(UTC).isoformat(),
        }
        review.payload = payload
        request_path.unlink()
        session.flush()
        return payload
