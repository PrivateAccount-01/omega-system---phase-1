"""Append-only review and reprocess contracts. No alerts, jobs or human approvals invented."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from omegadata.identity import query_time, text
from omegadata.identity_authority import EvidenceAuthority
from omegadata.reconciliation.contracts import fingerprint

TRANSITIONS = {
    "OPEN": {"UNDER_REVIEW", "AWAITING_EVIDENCE"},
    "UNDER_REVIEW": {"AWAITING_EVIDENCE", "CORRECTION_PROPOSED", "REJECTED"},
    "AWAITING_EVIDENCE": {"UNDER_REVIEW"},
    "CORRECTION_PROPOSED": {"APPROVED", "REJECTED", "AWAITING_EVIDENCE"},
    "APPROVED": {"REPROCESS_REQUIRED"},
    "REPROCESS_REQUIRED": {"REPROCESS_PENDING"},
    "REPROCESS_PENDING": {"REPROCESS_VERIFIED", "AWAITING_EVIDENCE"},
    "REPROCESS_VERIFIED": {"CLOSED"},
    "REJECTED": {"CLOSED"},
    "CLOSED": set(),
}


@dataclass(frozen=True)
class ReviewerAttestation:
    evidence_id: str
    reviewer_identity: str
    assignment_role: str
    source_record: tuple[tuple[str, Any], ...]
    attestation: tuple[tuple[str, Any], ...]
    reviewed_claim_sha256: str


def reviewer_authorized(
    a: ReviewerAttestation | None,
    authority: EvidenceAuthority | None,
    reviewer: str,
    role: str,
    at: datetime,
    claim_digest: str,
) -> bool:
    if a is None or authority is None or type(authority) is not EvidenceAuthority:
        return False
    if (
        a.reviewer_identity != reviewer
        or a.assignment_role != role
        or a.reviewed_claim_sha256 != claim_digest
    ):
        return False
    record = dict(a.attestation)
    if record.get("reviewer_id") != reviewer or record.get("assignment_role") != role:
        return False
    return authority.verify_identity_evidence(
        a.evidence_id, dict(a.source_record), record, "RESEARCH", at, claim_digest
    ).allowed


@dataclass(frozen=True)
class ReviewRevision:
    revision_id: str
    review_id: str
    discrepancy_id: str
    state: str
    created_at: datetime
    assignment_role: str
    evidence_references: tuple[str, ...]
    review_policy_version: str
    previous_record_digest: str | None
    affected_scope: tuple[str, ...]
    severity: str
    reviewer_identity: str | None = None
    decision_reason: str | None = None
    proposed_revision_digest: str | None = None
    reviewer_attestation: ReviewerAttestation | None = None
    verification_class: str = "NON_MARKET_STRUCTURAL_CONTROL"
    reprocess_evidence: tuple[ReprocessRequest, ReprocessCompletion, ReviewerAttestation] | None = (
        None
    )
    human_authorized: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        query_time(self.created_at)
        for value in (
            self.revision_id,
            self.review_id,
            self.discrepancy_id,
            self.assignment_role,
            self.review_policy_version,
        ):
            text(value)
        if (
            self.state not in TRANSITIONS
            or type(self.evidence_references) is not tuple
            or type(self.affected_scope) is not tuple
        ):
            raise ValueError("REVIEW_CONTRACT")


def advance_review(
    previous: ReviewRevision,
    state: str,
    revision_id: str,
    at: datetime,
    reviewer: str,
    reason: str,
    new_evidence: tuple[str, ...],
    *,
    mode: str = "STRICT",
    authority: EvidenceAuthority | None = None,
    attestation: ReviewerAttestation | None = None,
    proposed_revision_digest: str | None = None,
    reprocess_verified: bool = False,
    reprocess_evidence: tuple[ReprocessRequest, ReprocessCompletion, ReviewerAttestation]
    | None = None,
) -> ReviewRevision:
    query_time(at)
    text(reviewer)
    text(reason)
    if (
        state not in TRANSITIONS[previous.state]
        or at < previous.created_at
        or revision_id == previous.revision_id
    ):
        raise ValueError("INVALID_REVIEW_TRANSITION")
    if state in {"CORRECTION_PROPOSED", "APPROVED"} and (
        not new_evidence or not set(new_evidence) - set(previous.evidence_references)
    ):
        raise ValueError("CORRECTION_REQUIRES_NEW_EVIDENCE")
    decision = (
        fingerprint(previous),
        state,
        revision_id,
        at,
        reviewer,
        reason,
        new_evidence,
        proposed_revision_digest,
    )
    if mode not in {"STRICT", "CANARY_ONLY"}:
        raise ValueError("REVIEW_MODE")
    if mode == "STRICT" and not reviewer_authorized(
        attestation, authority, reviewer, previous.assignment_role, at, fingerprint(decision)
    ):
        raise ValueError("REVIEWER_AUTHORITY_BLOCKED")
    # A caller boolean is never independent completion evidence under STRICT.
    if state == "REPROCESS_VERIFIED":
        if mode == "STRICT":
            if (
                reprocess_evidence is None
                or verify_completion(
                    reprocess_evidence[0],
                    reprocess_evidence[1],
                    mode="STRICT",
                    authority=authority,
                    attestation=reprocess_evidence[2],
                    at=at,
                )
                != "VERIFIED"
            ):
                raise ValueError("REPROCESS_INDEPENDENT_EVIDENCE_REQUIRED")
        elif not reprocess_verified:
            raise ValueError("REPROCESS_INDEPENDENT_EVIDENCE_REQUIRED")
    return ReviewRevision(
        revision_id,
        previous.review_id,
        previous.discrepancy_id,
        state,
        at,
        previous.assignment_role,
        tuple(sorted(set(previous.evidence_references + new_evidence))),
        previous.review_policy_version,
        fingerprint(previous),
        previous.affected_scope,
        previous.severity,
        reviewer,
        reason,
        proposed_revision_digest,
        attestation,
        "NON_MARKET_STRUCTURAL_CONTROL"
        if mode == "CANARY_ONLY"
        else "SOURCE_REVIEW_PENDING_RELEASE",
        reprocess_evidence or previous.reprocess_evidence,
    )


@dataclass(frozen=True)
class CorrectionRevision:
    correction_id: str
    approved_review_revision: str
    previous_record_digest: str
    proposed_revision_digest: str
    affected_scope: tuple[str, ...]
    evidence_references: tuple[str, ...]
    known_from: datetime
    verification_class: str = "NON_MARKET_STRUCTURAL_CONTROL"

    def __post_init__(self) -> None:
        query_time(self.known_from)
        if (
            not self.evidence_references
            or not self.affected_scope
            or self.previous_record_digest == self.proposed_revision_digest
        ):
            raise ValueError("CORRECTION_EVIDENCE_REQUIRED")


@dataclass(frozen=True)
class ReprocessRequest:
    request_id: str
    approved_correction_id: str
    affected_security_or_listing: tuple[str, ...]
    affected_session_or_interval: tuple[date, ...]
    source_record_revisions: tuple[str, ...]
    affected_adjustment_outputs: tuple[str, ...]
    affected_universe_snapshots: tuple[str, ...]
    affected_reconciliation_results: tuple[str, ...]
    required_dependency_versions: tuple[tuple[str, str], ...]
    expected_output_identities: tuple[tuple[str, str], ...] = ()
    version: str = "od09.reprocess-request/v1"

    def __post_init__(self) -> None:
        text(self.request_id)
        text(self.approved_correction_id)
        for items in (
            self.affected_security_or_listing,
            self.affected_session_or_interval,
            self.source_record_revisions,
            self.affected_adjustment_outputs,
            self.affected_universe_snapshots,
            self.affected_reconciliation_results,
            self.required_dependency_versions,
        ):
            if type(items) is not tuple or len(items) > 10000 or len(set(items)) != len(items):
                raise ValueError("REPROCESS_SCOPE_BUDGET_OR_DUPLICATE")
        if not self.affected_security_or_listing or not self.affected_session_or_interval:
            raise ValueError("REPROCESS_EXACT_SCOPE_REQUIRED")

    @property
    def request_digest(self) -> str:
        return fingerprint(self)


@dataclass(frozen=True)
class ReprocessCompletion:
    completion_id: str
    request_id: str
    request_digest: str
    adopted_correction_id: str
    source_record_revisions: tuple[str, ...]
    affected_adjustment_outputs: tuple[str, ...]
    affected_universe_snapshots: tuple[str, ...]
    affected_reconciliation_results: tuple[str, ...]
    required_dependency_versions: tuple[tuple[str, str], ...]
    state: str
    evidence_references: tuple[str, ...]
    output_identities: tuple[tuple[str, str], ...] = ()


def verify_completion(
    request: ReprocessRequest,
    actual: ReprocessCompletion,
    *,
    mode: str = "STRICT",
    authority: EvidenceAuthority | None = None,
    attestation: ReviewerAttestation | None = None,
    at: datetime | None = None,
) -> str:
    if actual.state not in {
        "REQUESTED",
        "QUEUED",
        "RUNNING",
        "FAILED",
        "BLOCKED_DEPENDENCY",
        "COMPLETED_UNVERIFIED",
        "VERIFIED",
    }:
        return "BLOCKED_DEPENDENCY"
    if (actual.request_id, actual.request_digest, actual.adopted_correction_id) != (
        request.request_id,
        request.request_digest,
        request.approved_correction_id,
    ):
        return "BLOCKED_DEPENDENCY"
    for name in (
        "source_record_revisions",
        "affected_adjustment_outputs",
        "affected_universe_snapshots",
        "affected_reconciliation_results",
        "required_dependency_versions",
    ):
        if getattr(actual, name) != getattr(request, name):
            return "BLOCKED_DEPENDENCY"
    if actual.state not in {"COMPLETED_UNVERIFIED", "VERIFIED"}:
        return actual.state
    if actual.output_identities != request.expected_output_identities:
        return "BLOCKED_DEPENDENCY"
    if not actual.evidence_references:
        return "BLOCKED_DEPENDENCY"
    if mode != "STRICT" or not request.expected_output_identities:
        return "COMPLETED_UNVERIFIED"
    if (
        at is None
        or attestation is None
        or not reviewer_authorized(
            attestation,
            authority,
            attestation.reviewer_identity,
            "independent-reprocess-verifier",
            at,
            fingerprint((request, actual)),
        )
    ):
        return "COMPLETED_UNVERIFIED"
    return "VERIFIED"
