"""Bitemporal selection and independently declared coverage; no raw file access."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from omegadata.identity import query_time
from omegadata.identity_authority import EvidenceAuthority
from omegadata.universe import contracts as c


def known(start: datetime | None, end: datetime | None, cutoff: datetime) -> bool:
    return (start is None or start <= cutoff) and (end is None or cutoff < end)


def authorized(
    value: Any, x: c.UniverseContext, cutoff: datetime, purpose: str = "RESEARCH"
) -> bool:
    e = value.evidence
    if e is None or e.permission != "PERMITTED":
        return False
    if x.mode == "CANARY_ONLY":
        return bool(e.eligible("CANARY_ONLY"))
    return (
        (x.authority or EvidenceAuthority.unconfigured())
        .check_claim(value, cutoff, purpose)
        .allowed
    )


def validate_revisions(rows: tuple[c.MembershipRevision, ...]) -> dict[str, datetime]:
    by_id = {r.revision_id: r for r in rows}
    if len(by_id) != len(rows):
        raise ValueError("DUPLICATE_MEMBERSHIP_REVISION")
    ends: dict[str, datetime] = {}
    for r in rows:
        parent = r.claim.supersedes_membership_id
        if parent is None:
            if r.revision_number != 1:
                raise ValueError("REVISION_PARENT_REQUIRED")
            continue
        old = by_id.get(parent)
        if (
            old is None
            or parent in ends
            or old.event_id != r.event_id
            or old.universe_id != r.universe_id
            or r.revision_number != old.revision_number + 1
            or old.claim.known_from is None
            or r.claim.known_from is None
            or r.claim.known_from <= old.claim.known_from
        ):
            raise ValueError("MEMBERSHIP_SUPERSESSION")
        if old.claim.known_to is not None and old.claim.known_to < r.claim.known_from:
            raise ValueError("MEMBERSHIP_KNOWLEDGE_GAP")
        ends[parent] = r.claim.known_from
    return ends


def visible_revisions(x: c.UniverseContext, cutoff: datetime) -> tuple[c.MembershipRevision, ...]:
    query_time(cutoff)
    ends = validate_revisions(x.memberships)
    return tuple(
        sorted(
            (
                r
                for r in x.memberships
                if r.universe_id == x.definition.universe_id
                and known(r.claim.known_from, r.claim.known_to, cutoff)
                and (r.revision_id not in ends or cutoff < ends[r.revision_id])
            ),
            key=lambda r: r.revision_id,
        )
    )


def business_day(point: date | datetime) -> date:
    if isinstance(point, datetime):
        query_time(point)
        return point.astimezone(ZoneInfo("Asia/Kolkata")).date()
    if type(point) is not date:
        raise ValueError("DATE_OR_AWARE_TIMESTAMP_REQUIRED")
    return point


def valid_member(r: c.MembershipRevision, point: date | datetime) -> bool:
    day = business_day(point)
    claim = r.claim
    upper = claim.valid_to
    if claim.valid_from > day:
        return False
    if upper is not None and (day > upper or day == upper and r.removal_effective_at is None):
        return False
    if isinstance(point, datetime):
        if r.effective_at is not None and point < r.effective_at:
            return False
        if r.removal_effective_at is not None and point >= r.removal_effective_at:
            return False
    return True


def select_memberships(
    x: c.UniverseContext, day: date | datetime, cutoff: datetime
) -> tuple[c.MembershipRevision, ...]:
    business_day(day)
    return tuple(r for r in visible_revisions(x, cutoff) if valid_member(r, day))


def get_membership_history(x: c.UniverseContext, event_id: str) -> tuple[c.MembershipRevision, ...]:
    validate_revisions(x.memberships)
    return tuple(
        sorted(
            (r for r in x.memberships if r.event_id == event_id),
            key=lambda r: (r.revision_number, r.revision_id),
        )
    )


def get_known_upcoming_changes(
    x: c.UniverseContext, day: date, cutoff: datetime, *, horizon_days: int = 30
) -> tuple[tuple[c.MembershipRevision, str], ...]:
    if not 1 <= horizon_days <= 366:
        raise ValueError("UPCOMING_BUDGET")
    out = []
    for r in visible_revisions(x, cutoff):
        boundary = r.claim.valid_from
        if not day < boundary <= day + timedelta(days=horizon_days):
            continue
        status = (
            "EFFECTIVE_BUT_AVAILABILITY_UNKNOWN"
            if r.claim.known_from is None
            else "CONFLICTING"
            if r.claim.status == "CONFLICTING"
            else "SUPERSEDED"
            if r.event_type == "CANCEL"
            else "KNOWN_AND_NOT_YET_EFFECTIVE"
        )
        if any(v is not None and v > cutoff for v in (r.announcement_at, r.published_at)):
            status = "BLOCKED_AVAILABILITY"
        if not authorized(r, x, cutoff):
            status = "SOURCE_BLOCKED"
        out.append((r, status))
    return tuple(out)


def availability(
    o: c.AvailabilityObservation,
    cutoff: datetime,
    policy: c.AvailabilityPolicy,
    x: c.UniverseContext,
) -> str:
    query_time(cutoff)
    if (
        o.version != "od08.availability/v1"
        or not o.record_identity
        or o.source_id not in x.definition.source_scope
    ):
        return "BLOCKED_AVAILABILITY"
    if policy.mode not in {"STRICT", "CONSERVATIVE"}:
        return "BLOCKED_AVAILABILITY"
    lower = o.known_from
    if lower is None:
        if (
            policy.mode != "CONSERVATIVE"
            or policy.bound is None
            or not policy.semantics_reference
            or policy.evidence is None
            or x.mode != "STRICT"
            or not authorized(policy, x, cutoff)
        ):
            return "BLOCKED_AVAILABILITY"
        lower = policy.bound
    if lower > cutoff or o.known_to is not None and cutoff >= o.known_to:
        return "BLOCKED_AVAILABILITY"
    for stamp in (o.observed_at, o.published_at, o.interval_completed_at):
        if stamp is not None and stamp > cutoff:
            return "BLOCKED_AVAILABILITY"
    if o.interval_completed_at is None:
        return "BLOCKED_AVAILABILITY"
    return "AVAILABLE" if authorized(o, x, cutoff) else "BLOCKED_SOURCE_RIGHTS"


def coverage_reconcile(
    x: c.UniverseContext,
    day: date,
    cutoff: datetime,
    actual: tuple[str, ...],
    unresolved: tuple[str, ...],
) -> tuple[str, dict[str, Any]]:
    candidates = tuple(
        v
        for v in x.coverage
        if v.universe_id == x.definition.universe_id
        and v.valid_from <= day < v.valid_to
        and v.known_from is not None
        and known(v.known_from, v.known_to, cutoff)
    )
    diagnostics: dict[str, Any] = {
        "missing": [],
        "unexpected": [],
        "matching": [],
        "duplicates": sorted({v for v in actual if actual.count(v) > 1}),
        "unresolved": list(unresolved),
    }
    if not candidates:
        return "UNKNOWN", diagnostics
    if len(candidates) != 1:
        return "CONFLICTING", diagnostics
    cov = candidates[0]
    if (
        cov.source_id not in x.definition.source_scope
        or cov.methodology_version != x.definition.methodology_version
        or not cov.independent_reference_identity
        or not cov.artifact_identity
        or not authorized(cov, x, cutoff)
    ):
        return "SOURCE_BLOCKED", diagnostics
    if cov.state not in {"COMPLETE_VERIFIED", "COMPLETE_FOR_DECLARED_NON_MARKET_SCOPE"}:
        return cov.state, diagnostics
    if cov.state == "COMPLETE_VERIFIED" and x.mode != "STRICT":
        return "SOURCE_BLOCKED", diagnostics
    if cov.state == "COMPLETE_FOR_DECLARED_NON_MARKET_SCOPE" and x.mode != "CANARY_ONLY":
        return "SOURCE_BLOCKED", diagnostics
    expected = set(cov.expected_member_identities)
    if cov.expected_count is not None and cov.expected_count != len(expected):
        return "CONFLICTING", diagnostics
    if cov.granularity == "SNAPSHOT":
        if day != cov.valid_from or cov.valid_to != cov.valid_from + timedelta(days=1):
            return "PARTIAL", diagnostics
    else:
        if not cov.ending_reference:
            return "PARTIAL", diagnostics
        relevant = visible_revisions(x, cutoff)
        required = []
        for r in relevant:
            if r.event_type == "CANCEL":
                continue
            ident = (
                r.security_id if x.definition.identity_granularity == "SECURITY" else r.listing_id
            )
            if ident is None:
                continue
            if cov.valid_from < r.claim.valid_from < cov.valid_to:
                required.append((r.revision_id, ident, "ADD", r.claim.valid_from))
            if r.claim.valid_to is not None and cov.valid_from < r.claim.valid_to < cov.valid_to:
                required.append((r.revision_id, ident, "REMOVE", r.claim.valid_to))
        supplied = [
            (v.revision_id, v.member_identity, v.event_type, v.effective_date)
            for v in cov.transitions
        ]
        if len(set(supplied)) != len(supplied) or set(supplied) != set(required):
            return "PARTIAL", diagnostics
        final = set(expected)
        for transition in sorted(
            cov.transitions, key=lambda v: (v.effective_date, v.event_type, v.revision_id)
        ):
            if transition.event_type == "ADD":
                if transition.member_identity in final:
                    return "CONFLICTING", diagnostics
                final.add(transition.member_identity)
            elif transition.event_type == "REMOVE":
                if transition.member_identity not in final:
                    return "CONFLICTING", diagnostics
                final.remove(transition.member_identity)
            else:
                return "CONFLICTING", diagnostics
        if final != set(cov.ending_member_identities):
            return "CONFLICTING", diagnostics
        for transition in sorted(
            cov.transitions, key=lambda v: (v.effective_date, v.event_type, v.revision_id)
        ):
            if transition.effective_date > day:
                continue
            if transition.event_type == "ADD":
                expected.add(transition.member_identity)
            else:
                expected.discard(transition.member_identity)
    observed = set(actual)
    diagnostics.update(
        missing=sorted(expected - observed),
        unexpected=sorted(observed - expected),
        matching=sorted(expected & observed),
    )
    if (
        diagnostics["missing"]
        or diagnostics["unexpected"]
        or diagnostics["duplicates"]
        or unresolved
    ):
        return "CONFLICTING", diagnostics
    return cov.state, diagnostics
