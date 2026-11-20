"""Deterministic immutable back/forward comparison chains; no ORM mutation."""

from decimal import ROUND_HALF_UP, Decimal, DecimalException, Inexact, localcontext

from omegadata.adjustments.contracts import (
    PRECISION,
    VERSION,
    Action,
    Context,
    Link,
    Policy,
    Raw,
    Result,
    arithmetic_context,
    canonical,
)
from omegadata.adjustments.factors import factor
from omegadata.adjustments.temporal import (
    eligibility,
    raw_eligibility,
    references,
    select_revisions,
)
from omegadata.identity import query_time


def calculate_chain(raw: Raw, actions: tuple[Action, ...], policy: Policy, x: Context) -> Result:
    for action in actions:
        for reference in references(action):
            if reference.known_from is not None:
                query_time(reference.known_from)
    try:
        selected = select_revisions(actions, x.known_at)
    except ValueError as error:
        return Result(
            "CONFLICTING_ACTIONS", str(error), raw.artifact_id, consumer_profile=policy.profile
        )
    try:
        inputs = canonical(
            {
                "raw": raw,
                "actions": selected,
                "policy": policy,
                "valid_at": x.valid_at,
                "known_at": x.known_at,
                "identity_version": x.identity_version,
                "source_evidence_version": x.source_evidence_version,
                "calendar_version": x.calendar_version,
                "mode": x.mode,
            }
        )
    except (ValueError, TypeError):
        return Result(
            "INVALID_PARAMETERS",
            "NONFINITE_OR_INVALID_INPUT",
            raw.artifact_id,
            consumer_profile=policy.profile,
        )

    def blocked(status: str, reason: str) -> Result:
        return Result(
            status, reason, raw.artifact_id, raw.original_price_basis, policy.profile, inputs=inputs
        )

    if len(actions) > 128:
        return blocked("CONFLICTING_ACTIONS", "ACTION_RESOURCE_LIMIT")
    if raw.trade_date > x.valid_at or raw.known_from is None or raw.known_from > x.known_at:
        return blocked("BLOCKED_KNOWLEDGE", "RAW_NOT_AVAILABLE_AT_QUERY")
    status, reason = raw_eligibility(raw, x, execution=policy.profile == "EXECUTION")
    if status != "CALCULATED":
        return blocked(status, reason)
    try:
        selected = select_revisions(actions, x.known_at)
    except ValueError as e:
        return blocked("CONFLICTING_ACTIONS", str(e))
    # A directly requested future-only revision is a refusal, never silently accepted as complete.
    roots = {a.action_id for a in actions if a.supersedes_action_id is None}
    if any(
        a.known_from is not None and a.known_from > x.known_at and a.action_id in roots
        for a in actions
    ):
        return blocked("BLOCKED_KNOWLEDGE", "REQUESTED_EVENT_NOT_YET_KNOWN")
    if any(
        a.known_to is not None
        and a.known_to <= x.known_at
        and not any(
            b.supersedes_action_id == a.action_id
            and b.known_from is not None
            and b.known_from <= x.known_at
            for b in actions
        )
        for a in actions
    ):
        return blocked("BLOCKED_KNOWLEDGE", "EXPIRED_ACTION_WITHOUT_KNOWN_SUCCESSOR")
    applicable = [
        a for a in selected if a.ex_date is None or raw.trade_date < a.ex_date <= x.valid_at
    ]
    for a in applicable:
        peers = [b for b in applicable if b.ex_date == a.ex_date]
        if len(peers) > 1 and (
            any(b.sequence is None for b in peers) or len({b.sequence for b in peers}) != len(peers)
        ):
            return blocked("CONFLICTING_ACTIONS", "SAME_DAY_ORDER_NOT_ESTABLISHED")
    ordered = sorted(
        applicable, key=lambda a: (a.ex_date or raw.trade_date, a.sequence or 0, a.action_id)
    )
    links = []
    try:
        with localcontext(arithmetic_context()) as math:
            # Bounded 128 inputs * <=64 digits/exponents: exact multiplication before one division.
            math.prec = 20480
            n = d = vn = vd = Decimal(1)
            for a in ordered:
                if policy.profile == "EXECUTION" and a.action_type in {
                    "SUSPENSION",
                    "DELISTING",
                    "DELISTING_VOLUNTARY",
                    "DELISTING_REGULATORY",
                }:
                    return blocked("BLOCKED_IDENTITY", "LIFECYCLE_EXECUTION_CONSTRAINT")
                status, identity_ref, calendar_ref = eligibility(a, raw, x)
                if status != "CALCULATED":
                    return blocked(status, identity_ref)
                f = factor(a.action_type, a.parameters, policy)
                if f.status not in {"CALCULATED", "NOT_APPLICABLE"}:
                    return blocked(f.status, f.reason)
                if None in (f.numerator, f.denominator, f.volume_numerator, f.volume_denominator):
                    return blocked("INVALID_PARAMETERS", "INCOMPLETE_FACTOR")
                assert (
                    f.numerator is not None
                    and f.denominator is not None
                    and f.volume_numerator is not None
                    and f.volume_denominator is not None
                )
                n *= f.numerator
                d *= f.denominator
                vn *= f.volume_numerator
                vd *= f.volume_denominator
                links.append(
                    Link(
                        a.action_id,
                        a.source_artifact_identity,
                        identity_ref,
                        calendar_ref,
                        raw.artifact_id,
                        VERSION,
                        policy.profile,
                        canonical(a),
                        f,
                        "decimal80-final-half-up/v1",
                        x.known_at,
                    )
                )
            math.traps[Inexact] = False
            math.prec = PRECISION
            cumulative = n / d
            volume = vn / vd
            price = (
                raw.price
                if policy.profile in {"RAW", "EXECUTION", "VOLUME"}
                else (raw.price * n / d).quantize(policy.price_quantum, rounding=ROUND_HALF_UP)
            )
            quantity = (
                raw.volume
                if policy.profile in {"RAW", "EXECUTION"}
                else (raw.volume * vn / vd).quantize(policy.volume_quantum, rounding=ROUND_HALF_UP)
            )
    except DecimalException:
        return blocked("INVALID_PARAMETERS", "OUTPUT_PRECISION_OR_RESOURCE_LIMIT")
    return Result(
        "CALCULATED",
        "MATH_ONLY_NOT_AUTHENTIC_FINANCIAL_ACCEPTANCE"
        if x.mode == "NON_MARKET_MATH"
        else "PUBLICATION_REQUIRES_INDEPENDENT_RELEASE_GATE",
        raw.artifact_id,
        "RAW",
        policy.profile,
        tuple(links),
        cumulative,
        volume,
        price,
        quantity,
        inputs,
    )
