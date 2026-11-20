"""Deterministic OD08 query and bounded replay using pinned domain inputs."""

from __future__ import annotations

from collections import Counter
from dataclasses import replace
from datetime import date, datetime
from typing import Any

from omegadata.adjustments.contracts import canonical, digest
from omegadata.identity import IdentifierClaim, MemoryIdentityRepository, Resolution, query_time
from omegadata.identity_authority import EvidenceAuthority
from omegadata.universe import contracts as c
from omegadata.universe.eligibility import adjustment_eligible, liquidity
from omegadata.universe.temporal import (
    authorized,
    availability,
    business_day,
    coverage_reconcile,
    known,
    select_memberships,
)


def bindings(
    x: c.UniverseContext,
    day: date | datetime,
    cutoff: datetime,
    p: c.EligibilityPolicy,
    selected: tuple[c.MembershipRevision, ...],
) -> dict[str, Any]:
    visible = tuple(
        r
        for r in x.memberships
        if r.universe_id == x.definition.universe_id
        and (r.claim.known_from is None or r.claim.known_from <= cutoff)
    )
    reported_keys = {(r.claim.exchange, r.claim.symbol, r.claim.series) for r in selected}
    listing_ids = {r.listing_id for r in selected if r.listing_id is not None}
    claims = tuple(
        v
        for v in x.identity.claims
        if (v.known_from is None or v.known_from <= cutoff)
        and (v.listing_id in listing_ids or (v.exchange, v.symbol, v.series) in reported_keys)
    )
    listing_ids.update(v.listing_id for v in claims)
    listings = tuple(v for v in x.identity.listings if v.listing_id in listing_ids)
    security_ids = {v.security_id for v in listings}
    securities = tuple(v for v in x.identity.securities if v.security_id in security_ids)
    issuer_ids = {v.issuer_id for v in securities}
    identity = {
        "claims": claims,
        "listings": listings,
        "securities": securities,
        "issuers": tuple(v for v in x.identity.issuers if v.issuer_id in issuer_ids),
    }
    calendar = {
        "claims": tuple(
            v
            for v in x.calendar.claims
            if v.exchange in x.definition.exchange_scope
            and (v.known_from is None or v.known_from <= cutoff)
            and (x.calendar_version is None or v.calendar_version == x.calendar_version)
        ),
        "coverage": tuple(
            v
            for v in x.calendar.coverage
            if v.exchange in x.definition.exchange_scope
            and (v.known_from is None or v.known_from <= cutoff)
            and (x.calendar_version is None or v.calendar_version == x.calendar_version)
        ),
    }
    observations = tuple(
        sorted(
            (
                o
                for o in x.observations
                if o.listing_id in listing_ids
                and (o.known_from is None or o.known_from <= cutoff)
                and p.view != "MEMBERSHIP"
            ),
            key=lambda o: o.observation_id,
        )
    )
    refs = tuple(
        {
            "observation_id": o.observation_id,
            "raw_observation_digest": digest(o.adjustment_pin.raw) if o.adjustment_pin else None,
            "adjustment_context_id": o.adjustment_pin.snapshot_id if o.adjustment_pin else None,
            "adjustment_result_digest": o.adjustment.output_digest,
            "bindings": o.adjustment.context_bindings,
        }
        for o in observations
        if o.adjustment is not None
    )
    return {
        "universe_definition": digest(x.definition),
        "membership_ledger_digest": digest(tuple(sorted(visible, key=lambda r: r.revision_id))),
        "coverage_evidence_digest": digest(
            tuple(
                sorted(
                    (v for v in x.coverage if v.known_from is None or v.known_from <= cutoff),
                    key=lambda v: v.coverage_id,
                )
            )
        ),
        "identity_snapshot_digest": digest(identity),
        "calendar_snapshot_digest": digest(calendar),
        "source_authority_digest": (
            x.authority or EvidenceAuthority.unconfigured()
        ).snapshot_digest(),
        "observation_digest": digest(tuple(replace(o, adjustment_pin=None) for o in observations)),
        "adjustment_context_references": refs,
        "policy": p,
        "known_at": cutoff,
        "valid_at": day,
        "source_snapshot_id": x.source_snapshot_id,
        "version": x.version,
    }


def identity_views(
    x: c.UniverseContext, selected: tuple[c.MembershipRevision, ...]
) -> dict[str, MemoryIdentityRepository]:
    """Index once, then reuse the existing resolver on complete listing lineages."""
    claims_by_listing: dict[str, list[IdentifierClaim]] = {}
    reported: dict[tuple[str, str, str], set[str]] = {}
    for claim in x.identity.claims:
        claims_by_listing.setdefault(claim.listing_id, []).append(claim)
        reported.setdefault((claim.exchange, claim.symbol, claim.series), set()).add(
            claim.listing_id
        )
    listings = {v.listing_id: v for v in x.identity.listings}
    securities = {v.security_id: v for v in x.identity.securities}
    issuers = {v.issuer_id: v for v in x.identity.issuers}
    cache: dict[tuple[str, ...], MemoryIdentityRepository] = {}
    views = {}
    for member in selected:
        ids = set(
            reported.get((member.claim.exchange, member.claim.symbol, member.claim.series), set())
        )
        if member.listing_id in listings:
            ids.add(str(member.listing_id))
        key = tuple(sorted(ids))
        if key not in cache:
            selected_listings = tuple(listings[n] for n in key)
            security_ids = sorted(
                {v.security_id for v in selected_listings if v.security_id is not None}
            )
            selected_securities = tuple(securities[n] for n in security_ids)
            issuer_ids = sorted(
                {v.issuer_id for v in selected_securities if v.issuer_id is not None}
            )
            cache[key] = MemoryIdentityRepository(
                tuple(issuers[n] for n in issuer_ids),
                selected_securities,
                selected_listings,
                tuple(
                    sorted(
                        (v for n in key for v in claims_by_listing.get(n, [])),
                        key=lambda v: v.claim_id,
                    )
                ),
                authority=x.identity.authority,
            )
        views[member.revision_id] = cache[key]
    return views


def get_universe_as_of(
    x: c.UniverseContext,
    valid_at: date | datetime,
    known_at: datetime,
    eligibility_policy: c.EligibilityPolicy,
    source_snapshot_id: str,
) -> c.UniverseSnapshot:
    query_time(known_at)
    d = x.definition
    p = eligibility_policy
    valid_point = valid_at
    valid_at = business_day(valid_point)
    if source_snapshot_id != x.source_snapshot_id:
        raise ValueError("EXACT_SOURCE_PIN_REQUIRED")
    if (
        not d.valid_from <= valid_at
        or d.valid_to is not None
        and valid_at >= d.valid_to
        or d.known_from is None
        or not known(d.known_from, d.known_to, known_at)
    ):
        raise ValueError("DEFINITION_NOT_AVAILABLE")
    selected = select_memberships(x, valid_point, known_at)
    views = identity_views(x, selected)
    resolutions: dict[str, Resolution | None] = {}
    identities = []
    unresolved = []
    for r in selected:
        # Resolve as reported when the source claim became applicable, then follow stable IDs.
        origin = views[r.revision_id].resolve_listing(
            r.claim.exchange, r.claim.symbol, r.claim.series, r.claim.valid_from, known_at, x.mode
        )
        current = (
            views[r.revision_id].resolve_listing_id(origin.listing_id, valid_at, known_at, x.mode)
            if origin.listing_id is not None
            else origin
        )
        if (
            origin.state != "RESOLVED"
            or current.state != "RESOLVED"
            or origin.security_id != current.security_id
            or (r.security_id is not None and r.security_id != origin.security_id)
            or (r.listing_id is not None and r.listing_id != origin.listing_id)
        ):
            unresolved.append(r.revision_id)
            resolutions[r.revision_id] = None
            continue
        resolutions[r.revision_id] = current
        if r.event_type != "CANCEL":
            identities.append(
                current.security_id if d.identity_granularity == "SECURITY" else current.listing_id
            )
    actual = tuple(v for v in identities if v is not None)
    counts = Counter(actual)
    state, reconciliation = coverage_reconcile(x, valid_at, known_at, actual, tuple(unresolved))
    decisions = []
    complete = state in {"COMPLETE_VERIFIED", "COMPLETE_FOR_DECLARED_NON_MARKET_SCOPE"}
    for r in selected:
        resolution = resolutions[r.revision_id]
        security = resolution.security_id if resolution else None
        listing = resolution.listing_id if resolution else None
        ident = security if d.identity_granularity == "SECURITY" else listing
        status = "INCLUDED"
        reasons = []
        research = "NOT_REQUESTED"
        liq = "NOT_REQUESTED"
        tradability = resolution.lifecycle if resolution else "UNKNOWN"
        execution = False
        if r.event_type == "CANCEL":
            status = "EXCLUDED_BY_POLICY"
            reasons.append("CANCELLED")
        elif (
            r.claim.exchange not in d.exchange_scope
            or r.source_id not in d.source_scope
            or not authorized(d, x, known_at)
            or not authorized(r, x, known_at)
        ):
            status = "BLOCKED_SOURCE_RIGHTS"
        elif (
            r.claim.known_from is None
            or (
                r.effective_convention == "UNKNOWN"
                or r.effective_convention == "EXPLICIT_TIMESTAMP"
                and not isinstance(valid_point, datetime)
            )
            or any(v is not None and v > known_at for v in (r.published_at, r.announcement_at))
        ):
            status = "BLOCKED_AVAILABILITY"
        elif r.claim.status == "CONFLICTING" or ident is not None and counts[ident] > 1:
            status = "CONFLICTING_MEMBERSHIP"
        elif resolution is None:
            status = "UNRESOLVED_IDENTITY"
        elif (
            r.claim.status in {"RECONSTRUCTED_PROVISIONAL", "UNKNOWN"}
            or d.universe_type == "PROVISIONAL_RECONSTRUCTION"
        ):
            status = "PROVISIONAL_ONLY"
        elif not complete:
            status = "BLOCKED_REFERENCE_COVERAGE"
        elif p.view != "MEMBERSHIP":
            obs = tuple(
                o
                for o in x.observations
                if o.listing_id == listing
                and o.session_date <= valid_at
                and (o.known_from is None or o.known_from <= known_at)
            )
            if p.require_observations and (
                not obs
                or any(
                    availability(o, known_at, p.availability_policy, x) != "AVAILABLE" for o in obs
                )
            ):
                status = "BLOCKED_AVAILABILITY"
                research = status
            else:
                research = (
                    "ELIGIBLE_NON_MARKET" if x.mode == "CANARY_ONLY" else "ELIGIBLE_SOURCE_BACKED"
                )
            if (
                status == "INCLUDED"
                and p.require_adjustment
                and (
                    not obs
                    or any(
                        o.adjustment is None
                        or adjustment_eligible(
                            o.adjustment,
                            o.adjustment_pin,
                            known_at,
                            p.required_profile,
                            p.required_basis,
                        ).startswith("BLOCKED")
                        or o.adjustment_pin is not None
                        and o.adjustment_pin.raw.raw.listing_id != listing
                        for o in obs
                    )
                )
            ):
                status = "BLOCKED_AVAILABILITY"
                reasons.append("BLOCKED_ADJUSTMENT_CONTEXT")
            if status == "INCLUDED" and p.view == "LIQUIDITY":
                if p.liquidity_policy is None:
                    status = liq = "BLOCKED_LIQUIDITY_COVERAGE"
                else:
                    liq, detail = liquidity(
                        replace(r, listing_id=listing),
                        x,
                        obs,
                        valid_at,
                        known_at,
                        p.liquidity_policy,
                    )
                    reasons.append(canonical(detail))
                    if liq != "ELIGIBLE":
                        status = liq
            if status == "INCLUDED" and p.view == "EXECUTION":
                eligible = [
                    o
                    for o in obs
                    if o.adjustment is not None
                    and o.adjustment_pin is not None
                    and o.session_date == valid_at
                    and availability(o, known_at, p.availability_policy, x) == "AVAILABLE"
                    and adjustment_eligible(
                        o.adjustment, o.adjustment_pin, known_at, "EXECUTION", "RAW_UNADJUSTED"
                    )
                    == "ELIGIBLE_SOURCE_BACKED"
                    and o.adjustment.execution_eligibility
                    and o.adjustment_pin.raw.raw.listing_id == listing
                ]
                execution = bool(eligible) and x.mode == "STRICT"
                if not execution:
                    status = "BLOCKED_TRADABILITY"
        reasons.append(status)
        decisions.append(
            c.MemberDecision(
                r.revision_id,
                security,
                listing,
                status,
                tuple(reasons),
                r.evidence.evidence_id,
                digest(resolution),
                r.claim.status,
                research,
                liq,
                tradability or "UNKNOWN",
                execution,
            )
        )
    rows = tuple(decisions)
    if len(rows) != len(selected) or len({r.revision_id for r in rows}) != len(rows):
        raise ValueError("ACCOUNTING_INVARIANT")
    included = tuple(
        sorted(
            {
                str(v.security_id if d.identity_granularity == "SECURITY" else v.listing_id)
                for v in rows
                if v.status == "INCLUDED"
                and (v.security_id if d.identity_granularity == "SECURITY" else v.listing_id)
                is not None
            }
        )
    )
    snapshot = c.UniverseSnapshot(
        d.universe_id,
        d.version,
        valid_point,
        known_at,
        x.source_snapshot_id,
        tuple(v.revision_id for v in selected),
        rows,
        tuple(sorted(set(actual))),
        included,
        state,
        canonical(reconciliation),
        canonical(bindings(x, valid_point, known_at, p, selected)),
        digest(rows),
        p.policy_version,
        p.availability_policy.policy_version,
        p.liquidity_policy.policy_version if p.liquidity_policy else None,
    )
    # Publication remains blocked until separate authentic corpus and release gates pass.
    return snapshot


def get_eligible_members(snapshot: c.UniverseSnapshot) -> tuple[c.MemberDecision, ...]:
    return tuple(v for v in snapshot.decisions if v.status == "INCLUDED")


def explain_member_decision(snapshot: c.UniverseSnapshot, revision_id: str) -> c.MemberDecision:
    return next(v for v in snapshot.decisions if v.revision_id == revision_id)


def compare_universe_snapshots(old: c.UniverseSnapshot, new: c.UniverseSnapshot) -> dict[str, Any]:
    if old.universe_id != new.universe_id:
        raise ValueError("SNAPSHOT_SCOPE_MISMATCH")
    a = {v.revision_id: v for v in old.decisions}
    b = {v.revision_id: v for v in new.decisions}
    return {
        "added": sorted(set(b) - set(a)),
        "removed": sorted(set(a) - set(b)),
        "changed": sorted(n for n in set(a) & set(b) if a[n] != b[n]),
        "old": old.snapshot_digest,
        "new": new.snapshot_digest,
    }


def replay_universe_decisions(
    x: c.UniverseContext,
    steps: tuple[tuple[date, datetime], ...],
    policy: c.EligibilityPolicy,
    *,
    max_steps: int = 366,
) -> tuple[c.UniverseSnapshot, ...]:
    if (
        type(steps) is not tuple
        or type(max_steps) is not int
        or not 0 < max_steps <= 3660
        or len(steps) > max_steps
    ):
        raise ValueError("REPLAY_BUDGET")
    if steps and (max(v[0] for v in steps) - min(v[0] for v in steps)).days > 3660:
        raise ValueError("REPLAY_DATE_BUDGET")
    return tuple(get_universe_as_of(x, d, k, policy, x.source_snapshot_id) for d, k in steps)
