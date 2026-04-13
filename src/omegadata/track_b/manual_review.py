from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from omegadata.db.models import ManualReviewQueue, ReprocessJob
from omegadata.domain import ReviewDecision
from omegadata.track_a.alerting import AlertEvent, AlertRouter
from omegadata.track_a.monitoring import (
    REPROCESS_JOB_GAUGE,
    REVIEW_OPEN_GAUGE,
    REVIEW_OVERDUE_GAUGE,
)
from omegadata.track_a.trading_calendar import TradingCalendar
from omegadata.track_b.review_policy import ReviewPolicy, load_review_policies


@dataclass(frozen=True)
class ReviewResolution:
    review_id: int
    decision: ReviewDecision
    requires_reprocess: bool
    reprocess_status: str
    reprocess_job_id: int | None = None


class ManualReviewService:
    def __init__(self) -> None:
        self.alert_router = AlertRouter()

    @staticmethod
    def _fingerprint(payload: dict[str, object]) -> str:
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _policy(self, category: str) -> ReviewPolicy:
        return load_review_policies().for_category(category)

    @staticmethod
    def _calendar_exchange(payload: dict[str, object]) -> str:
        exchange_value = payload.get("exchange") or payload.get("source_exchange")
        if isinstance(exchange_value, str) and exchange_value.strip() in {"NSE", "BSE"}:
            return exchange_value.strip()
        return "NSE"

    def _apply_sla_metadata(
        self,
        payload: dict[str, Any],
        *,
        policy: ReviewPolicy,
        created_at: datetime,
        resolved: bool,
    ) -> None:
        if policy.sla_business_days is None or policy.sla_business_days <= 0:
            return
        calendar = TradingCalendar.from_config()
        exchange = self._calendar_exchange(payload)
        created_date = created_at.date()
        due_date = calendar.add_business_days(
            exchange,
            anchor_date=created_date,
            business_days=policy.sla_business_days,
            strict=False,
        )
        payload["sla_business_days"] = policy.sla_business_days
        payload["sla_exchange"] = exchange
        payload.setdefault("sla_due_date", due_date.isoformat())
        if resolved:
            payload["sla_status"] = "RESOLVED"
            payload["sla_breached"] = False
            payload["sla_overdue_business_days"] = 0
            return

        today = datetime.now(UTC).date()
        due_date_value = date.fromisoformat(str(payload["sla_due_date"]))
        overdue_business_days = calendar.business_days_between(
            exchange,
            start_date=due_date_value,
            end_date=today,
            strict=False,
        )
        if today > due_date_value and overdue_business_days > 0:
            payload["sla_status"] = "OVERDUE"
            payload["sla_breached"] = True
            payload["sla_overdue_business_days"] = overdue_business_days
            payload.setdefault("escalation_status", "ESCALATED")
            payload.setdefault("escalated_at", datetime.now(UTC).isoformat())
            payload["release_gate_impact"] = (
                "BLOCK_RELEASE" if policy.blocks_release_when_overdue and policy.blocks_publication else "NONE"
            )
            if payload.get("escalation_notified_at") is None and policy.blocks_release_when_overdue:
                sent = self.alert_router.route(
                    AlertEvent(
                        severity=policy.escalation_severity,
                        title=f"Manual review overdue: {policy.category}",
                        message=(
                            f"Review for {payload.get('isin') or 'unknown'} is overdue and "
                            f"assigned to {policy.assignment_team}."
                        ),
                        source="manual_review",
                        created_at=datetime.now(UTC),
                    )
                )
                payload["escalation_notified_at"] = datetime.now(UTC).isoformat()
                payload["escalation_notification_sent"] = sent
        elif today == due_date_value:
            payload["sla_status"] = "DUE_TODAY"
            payload["sla_breached"] = False
            payload["sla_overdue_business_days"] = 0
            payload["release_gate_impact"] = "NONE"
        else:
            payload["sla_status"] = "OPEN"
            payload["sla_breached"] = False
            payload["sla_overdue_business_days"] = 0
            payload["release_gate_impact"] = "NONE"

    def _refresh_review_payload(self, review: ManualReviewQueue) -> bool:
        policy = self._policy(review.category)
        payload: dict[str, Any] = dict(review.payload or {})
        before = json.dumps(payload, sort_keys=True, default=str)
        self._apply_sla_metadata(
            payload,
            policy=policy,
            created_at=review.created_at,
            resolved=review.resolved,
        )
        after = json.dumps(payload, sort_keys=True, default=str)
        if before == after:
            return False
        review.payload = payload
        return True

    @staticmethod
    def _update_review_metrics(rows: list[ManualReviewQueue]) -> None:
        categories = {row.category for row in rows}
        for category in categories:
            category_rows = [row for row in rows if row.category == category]
            REVIEW_OPEN_GAUGE.labels(category=category).set(len(category_rows))
            overdue = 0
            for row in category_rows:
                payload = dict(row.payload or {})
                if bool(payload.get("sla_breached")):
                    overdue += 1
            REVIEW_OVERDUE_GAUGE.labels(category=category).set(overdue)

    @staticmethod
    def _update_reprocess_metrics(session: Session) -> None:
        counts: dict[str, int] = {}
        rows = session.scalars(select(ReprocessJob)).all()
        for row in rows:
            counts[row.status] = counts.get(row.status, 0) + 1
        for status in {"QUEUED", "RUNNING", "COMPLETED", "FAILED"}:
            REPROCESS_JOB_GAUGE.labels(status=status).set(counts.get(status, 0))

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
        enriched_payload.setdefault("isin", isin)
        enriched_payload["payload_fingerprint"] = self._fingerprint(payload)
        enriched_payload["policy_version"] = policy_set.version
        enriched_payload["block_scope"] = policy.scope.value
        enriched_payload["blocks_publication"] = policy.blocks_publication
        enriched_payload["requires_reprocess"] = policy.requires_reprocess
        enriched_payload["triage_instructions"] = policy.triage_instructions
        enriched_payload["assignment_team"] = policy.assignment_team
        enriched_payload["escalation_severity"] = policy.escalation_severity
        enriched_payload["blocks_release_when_overdue"] = policy.blocks_release_when_overdue
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
        self._apply_sla_metadata(
            enriched_payload,
            policy=policy,
            created_at=review.created_at,
            resolved=False,
        )
        review.payload = enriched_payload
        session.flush()
        return review

    def list_open_reviews(self, session: Session) -> list[ManualReviewQueue]:
        rows = list(
            session.scalars(
                select(ManualReviewQueue)
                .where(ManualReviewQueue.resolved.is_(False))
                .order_by(ManualReviewQueue.created_at.asc(), ManualReviewQueue.id.asc())
            ).all()
        )
        updated = False
        for review in rows:
            updated = self._refresh_review_payload(review) or updated
        if updated:
            session.flush()
        self._update_review_metrics(rows)
        self._update_reprocess_metrics(session)
        return rows

    def _queue_reprocess_job(self, session: Session, *, review: ManualReviewQueue, requested_at: str) -> ReprocessJob:
        existing = session.scalar(select(ReprocessJob).where(ReprocessJob.review_id == review.id))
        if existing is not None:
            existing.status = "QUEUED"
            existing.requested_payload = dict(existing.requested_payload or {})
            existing.requested_payload.update(
                {
                    "review_id": review.id,
                    "category": review.category,
                    "isin": review.isin,
                    "event_date": None if review.event_date is None else review.event_date.isoformat(),
                    "requested_at": requested_at,
                    "reason": review.reason,
                }
            )
            session.flush()
            return existing
        job = ReprocessJob(
            review_id=review.id,
            isin=review.isin,
            event_date=review.event_date,
            status="QUEUED",
            requested_payload={
                "review_id": review.id,
                "category": review.category,
                "isin": review.isin,
                "event_date": None if review.event_date is None else review.event_date.isoformat(),
                "requested_at": requested_at,
                "reason": review.reason,
            },
        )
        session.add(job)
        session.flush()
        return job

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
        reprocess_job_id: int | None = None
        now = datetime.now(UTC).isoformat()
        payload["resolution"] = {
            "decision": decision.value,
            "reviewer": reviewer,
            "notes": notes,
            "resolved_at": now,
        }
        review.resolved = True
        existing_job = session.scalar(select(ReprocessJob).where(ReprocessJob.review_id == review.id))

        if decision in {ReviewDecision.FALSE_POSITIVE, ReviewDecision.OVERRIDE_APPROVED}:
            payload["reprocess_status"] = "NOT_REQUIRED"
            if existing_job is not None and existing_job.status in {"QUEUED", "RUNNING"}:
                existing_job.status = "FAILED"
                existing_job.completion_payload = {
                    "completed_by": reviewer,
                    "notes": f"Cancelled due to {decision.value}: {notes}",
                    "completed_at": now,
                }
        elif requires_reprocess and decision == ReviewDecision.REMEDIATED:
            payload["reprocess_status"] = "PENDING"
            job = self._queue_reprocess_job(session, review=review, requested_at=now)
            reprocess_job_id = job.id
            payload["reprocess_job_id"] = job.id
        else:
            payload["reprocess_status"] = "NOT_REQUIRED"

        review.payload = payload
        self._apply_sla_metadata(
            payload,
            policy=self._policy(review.category),
            created_at=review.created_at,
            resolved=True,
        )
        review.payload = payload
        session.flush()
        self._update_reprocess_metrics(session)
        return ReviewResolution(
            review_id=review.id,
            decision=decision,
            requires_reprocess=requires_reprocess,
            reprocess_status=str(payload["reprocess_status"]),
            reprocess_job_id=reprocess_job_id,
        )

    def complete_reprocess(
        self,
        session: Session,
        *,
        review_id: int,
        completed_by: str,
        notes: str,
        rebuilt_tables: list[str],
        rebuilt_isins: list[str],
        validation_checks: list[str],
        evidence_paths: list[str],
        date_range: dict[str, str] | None,
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
        if not rebuilt_tables:
            raise ValueError("reprocess completion requires rebuilt_tables evidence")
        if not validation_checks:
            raise ValueError("reprocess completion requires validation_checks evidence")
        if not evidence_paths:
            raise ValueError("reprocess completion requires evidence_paths")

        job = session.scalar(select(ReprocessJob).where(ReprocessJob.review_id == review.id))
        if job is None:
            raise ValueError(f"Manual review {review_id} has no queued reprocess job")
        if job.status not in {"QUEUED", "RUNNING"}:
            raise ValueError(f"Manual review {review_id} reprocess job is not pending")

        normalized_paths = []
        for raw_path in evidence_paths:
            candidate = Path(raw_path)
            if not candidate.is_absolute():
                candidate = Path.cwd() / candidate
            normalized_paths.append(candidate.resolve().as_posix())

        payload["reprocess_status"] = "COMPLETED"
        payload["reprocess_completed"] = {
            "completed_by": completed_by,
            "notes": notes,
            "completed_at": datetime.now(UTC).isoformat(),
            "rebuilt_tables": rebuilt_tables,
            "rebuilt_isins": rebuilt_isins,
            "validation_checks": validation_checks,
            "evidence_paths": normalized_paths,
            "date_range": date_range,
        }
        review.payload = payload
        job.status = "COMPLETED"
        job.completed_at = datetime.now(UTC)
        job.completion_payload = dict(payload["reprocess_completed"])
        session.flush()
        self._update_reprocess_metrics(session)
        return payload
