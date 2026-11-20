"""Append-only revision selection and OD06 authority/identity/calendar integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omegadata.adjustments.bound_contracts import ReferenceObservation

from omegadata.adjustments.contracts import (
    Action,
    Context,
    Demerger,
    Dividend,
    Raw,
    Reference,
    Rights,
    canonical,
    digest,
)
from omegadata.identity import Evidence, query_time, text
from omegadata.identity import Policy as EvidencePolicy
from omegadata.session_calendar import VerifiedCalendar


def select_revisions(actions: tuple[Action, ...], known_at: datetime) -> tuple[Action, ...]:
    query_time(known_at)
    if type(actions) is not tuple:
        raise ValueError("IMMUTABLE_ACTION_LEDGER")
    by_id = {a.action_id: a for a in actions}
    if len(by_id) != len(actions):
        raise ValueError("DUPLICATE_ACTION_ID")
    ends = {}
    for a in actions:
        if a.supersedes_action_id is None:
            continue
        old = by_id.get(a.supersedes_action_id)
        if (
            old is None
            or old.action_id in ends
            or a.known_from is None
            or old.known_from is None
            or a.known_from <= old.known_from
            or (old.security_id, old.listing_id, old.exchange, old.ex_date, old.action_type)
            != (a.security_id, a.listing_id, a.exchange, a.ex_date, a.action_type)
            or a.action_revision != old.action_revision + 1
            or old.known_to is not None
            and old.known_to < a.known_from
        ):
            raise ValueError("INVALID_ACTION_SUPERSESSION")
        ends[old.action_id] = a.known_from
    return tuple(
        sorted(
            (
                a
                for a in actions
                if (a.known_from is None or a.known_from <= known_at)
                and (a.known_to is None or known_at < a.known_to)
                and (a.action_id not in ends or known_at < ends[a.action_id])
            ),
            key=lambda a: a.action_id,
        )
    )


def references(a: Action) -> tuple[Reference | ReferenceObservation, ...]:
    p = a.parameters
    ref = (
        p.reference
        if isinstance(p, Rights)
        else p.reinvestment
        if isinstance(p, Dividend)
        else p.successor_value
        if isinstance(p, Demerger)
        else None
    )
    return () if ref is None else (ref,)


@dataclass(frozen=True)
class AuthorityClaim:
    evidence: Evidence
    payload: str
    source_evidence_version: str


def verified(value: object, evidence: Evidence, x: Context) -> bool:
    return (
        x.authority is not None
        and x.authority.check_claim(
            AuthorityClaim(evidence, canonical(value), x.source_evidence_version), x.known_at
        ).allowed
    )


def raw_eligibility(raw: Raw, x: Context, *, execution: bool = False) -> tuple[str, str]:
    if raw.known_from is None or raw.known_from > x.known_at:
        return "BLOCKED_KNOWLEDGE", "RAW_AVAILABILITY_UNKNOWN"
    if raw.evidence.permission != "PERMITTED":
        return "BLOCKED_EVIDENCE", "RAW_RIGHTS_REFUSAL"
    mode: EvidencePolicy = "CANARY_ONLY" if x.mode == "NON_MARKET_MATH" else "STRICT"
    if not (
        raw.evidence.eligible(mode) if mode == "CANARY_ONLY" else verified(raw, raw.evidence, x)
    ):
        return "BLOCKED_EVIDENCE", "RAW_AUTHORITY_NOT_SUPPLIED"
    for day in (raw.trade_date, x.valid_at):
        result = (
            x.identity_repository.resolve_listing(
                raw.exchange, raw.symbol, raw.series, day, x.known_at, mode
            )
            if day == raw.trade_date
            else x.identity_repository.resolve_listing_id(raw.listing_id, day, x.known_at, mode)
        )
        if (
            result.state != "RESOLVED"
            or result.security_id != raw.security_id
            or result.listing_id != raw.listing_id
            or execution
            and result.lifecycle != "LISTED"
        ):
            return "BLOCKED_IDENTITY", "IDENTITY_OR_EXECUTION_STATUS_UNRESOLVED"
    return "CALCULATED", "RAW_ELIGIBILITY_CHECKED"


def eligibility(a: Action, raw: Raw, x: Context) -> tuple[str, str, str]:
    for v in (raw.known_from, a.known_from):
        if v is None or v > x.known_at:
            return "BLOCKED_KNOWLEDGE", "UNKNOWN_OR_FUTURE_AVAILABILITY", ""
    for v in (a.announcement_at, a.published_at, a.parameter_known_from):
        if v is not None and v > x.known_at:
            return "BLOCKED_KNOWLEDGE", "FUTURE_ACTION_PARAMETER", ""
    for ref in references(a):
        if ref.known_from is not None:
            query_time(ref.known_from)
        if ref.known_from is None or ref.known_from > x.known_at:
            return "BLOCKED_KNOWLEDGE", "REFERENCE_NOT_YET_KNOWN", ""
        query_time(ref.known_from)
    if (
        a.review_status in {"REVOKED", "CONFLICTING"}
        or a.evidence.permission != "PERMITTED"
        or raw.evidence.permission != "PERMITTED"
    ):
        return "BLOCKED_EVIDENCE", "REVIEW_OR_RIGHTS_REFUSAL", ""
    if (
        (a.security_id, a.exchange) != (raw.security_id, raw.exchange)
        or a.listing_id is not None
        and a.listing_id != raw.listing_id
    ):
        return "BLOCKED_IDENTITY", "WRONG_ACTION_IDENTITY", ""
    mode: EvidencePolicy = "CANARY_ONLY" if x.mode == "NON_MARKET_MATH" else "STRICT"
    if mode == "CANARY_ONLY":
        if not a.evidence.eligible(mode) or not raw.evidence.eligible(mode):
            return "BLOCKED_EVIDENCE", "MATH_ONLY_INPUT_REQUIRED", ""
    else:
        # Plain labels cannot qualify; actual configured authority and canonical action binding required.
        if not verified(a, a.evidence, x):
            return "BLOCKED_EVIDENCE", "AUTHENTIC_ACTION_AUTHORITY_NOT_SUPPLIED", ""
    for ref in references(a):
        try:
            text(ref.artifact_id)
        except ValueError:
            return "INVALID_PARAMETERS", "REFERENCE_IDENTITY_REQUIRED", ""
        if ref.currency != raw.currency:
            return "INVALID_PARAMETERS", "REFERENCE_CURRENCY_MISMATCH", ""
        if mode == "STRICT" and (ref.evidence is None or not verified(ref, ref.evidence, x)):
            return "BLOCKED_EVIDENCE", "REFERENCE_AUTHORITY_UNKNOWN", ""
    if isinstance(a.parameters, (Rights, Dividend)) and a.parameters.currency != raw.currency:
        return "INVALID_PARAMETERS", "ACTION_CURRENCY_MISMATCH", ""
    identity = x.identity_repository.resolve_listing_id(
        raw.listing_id, x.valid_at, x.known_at, mode
    )
    historical = x.identity_repository.resolve_listing(
        raw.exchange, raw.symbol, raw.series, raw.trade_date, x.known_at, mode
    )
    if any(
        v.state != "RESOLVED" or v.security_id != raw.security_id or v.listing_id != raw.listing_id
        for v in (identity, historical)
    ):
        return "BLOCKED_IDENTITY", "IDENTITY_UNRESOLVED_OR_CONFLICTING", ""
    if a.ex_date is None:
        return "BLOCKED_CALENDAR", "EX_DATE_UNKNOWN", ""
    session = x.calendar.query(
        a.exchange, a.ex_date, x.known_at, mode, calendar_version=x.calendar_version
    )
    if session.status not in {"AUTHORITATIVE_SESSION", "VERIFIED_SPECIAL_SESSION"}:
        return "BLOCKED_CALENDAR", "EX_SESSION_UNVERIFIED", ""
    calendar_ref = canonical(tuple(c.claim_id for c in session.claims))
    if isinstance(a.parameters, Rights):
        try:
            pinned = VerifiedCalendar(
                tuple(c for c in x.calendar.claims if c.calendar_version == x.calendar_version),
                tuple(c for c in x.calendar.coverage if c.calendar_version == x.calendar_version),
                x.calendar.authority,
            )
            prior = pinned.previous_session(a.exchange, a.ex_date, x.known_at, mode)
        except ValueError:
            return "BLOCKED_CALENDAR", "PRIOR_SESSION_OR_COVERAGE_UNKNOWN", ""
        prior_ref = a.parameters.reference
        if (
            prior_ref is None
            or prior.claims[0].session_date != prior_ref.session_date
            or prior.claims[0].calendar_version != x.calendar_version
        ):
            return "BLOCKED_CALENDAR", "PRIOR_VERIFIED_SESSION_MISMATCH", ""
        calendar_ref = canonical((calendar_ref, prior.claims[0].claim_id))
    if (
        isinstance(a.parameters, Dividend)
        and a.parameters.reinvestment is not None
        and a.parameters.reinvestment.session_date != a.ex_date
    ):
        return "BLOCKED_CALENDAR", "REINVESTMENT_SESSION_MISMATCH", ""
    return "CALCULATED", digest((identity, historical)), calendar_ref
