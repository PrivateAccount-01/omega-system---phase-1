"""Versioned consumer policies; membership is never silently filtered."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from fractions import Fraction
from typing import Any

from omegadata.adjustments.bound_chain import calculate_bound_chain
from omegadata.adjustments.bound_contracts import BOUND_VERSION, BoundResult, PinnedCalculation
from omegadata.universe import contracts as c
from omegadata.universe.temporal import availability


def adjustment_eligible(
    result: BoundResult, pin: PinnedCalculation | None, cutoff: datetime, profile: str, basis: str
) -> str:
    if (
        pin is None
        or result.version != BOUND_VERSION
        or result.status != "CALCULATED"
        or result.calculation.consumer_profile != profile
        or result.adjustment_basis != basis
        or pin.context.known_at > cutoff
    ):
        return "BLOCKED_ADJUSTMENT_CONTEXT"
    rebuilt = calculate_bound_chain(pin)
    if (
        rebuilt.canonical_json != result.canonical_json
        or pin.raw.observation_id != result.calculation.original_raw_reference
    ):
        return "BLOCKED_ADJUSTMENT_CONTEXT"
    return (
        "ELIGIBLE_NON_MARKET" if pin.context.mode == "NON_MARKET_MATH" else "ELIGIBLE_SOURCE_BACKED"
    )


def liquidity(
    member: c.MembershipRevision,
    x: c.UniverseContext,
    observations: tuple[c.AvailabilityObservation, ...],
    day: date,
    cutoff: datetime,
    p: c.LiquidityPolicy,
) -> tuple[str, dict[str, Any]]:
    needed = []
    current = day
    calendar = x.calendar
    diagnostics: dict[str, Any] = {}
    for _ in range(3660):
        if calendar.coverage_status(member.claim.exchange, current, cutoff, x.mode) != "COMPLETE":
            return "BLOCKED_LIQUIDITY_COVERAGE", {
                "reason": "CALENDAR_COVERAGE_UNKNOWN",
                "date": current.isoformat(),
            }
        session = calendar.query(
            member.claim.exchange, current, cutoff, x.mode, calendar_version=x.calendar_version
        )
        if session.status in {"AUTHORITATIVE_SESSION", "VERIFIED_SPECIAL_SESSION"}:
            close = session.claims[0].closes_at
            if close is None:
                return "BLOCKED_LIQUIDITY_COVERAGE", {"reason": "SESSION_COMPLETION_UNKNOWN"}
            if close <= cutoff:
                needed.append(current)
        elif session.status != "KNOWN_CLOSURE":
            return "BLOCKED_LIQUIDITY_COVERAGE", {"reason": "SESSION_UNKNOWN"}
        if len(needed) == p.lookback_sessions:
            break
        current -= timedelta(days=1)
    if len(needed) != p.lookback_sessions:
        return "BLOCKED_LIQUIDITY_COVERAGE", {"reason": "WINDOW_BUDGET"}
    usable = []
    missing = []
    for d in needed:
        rows = [o for o in observations if o.session_date == d]
        if len(rows) > 1:
            return "BLOCKED_LIQUIDITY_COVERAGE", {"reason": "DUPLICATE_SESSION"}
        if not rows:
            missing.append(d)
            continue
        o = rows[0]
        if (
            o.listing_id != member.listing_id
            or (o.currency, o.price_unit, o.price_basis, o.volume_basis)
            != (p.currency, p.price_unit, p.price_basis, p.volume_basis)
            or o.volume is None
            or o.turnover is None
            or availability(o, cutoff, c.AvailabilityPolicy(), x) != "AVAILABLE"
        ):
            return "BLOCKED_LIQUIDITY_COVERAGE", {
                "reason": "OBSERVATION_IDENTITY_UNITS_AVAILABILITY_OR_MISSING_VALUE"
            }
        if p.volume_basis != "RAW" and o.adjustment_binding is not None:
            from omegadata.universe.observation_binding import validate_binding

            if validate_binding(o, o.adjustment_binding, cutoff).startswith("BLOCKED"):
                return "BLOCKED_LIQUIDITY_COVERAGE", {"reason": "EXACT_VOLUME_BINDING_REQUIRED"}
        if p.volume_basis != "RAW" and (
            o.adjustment is None
            or adjustment_eligible(
                o.adjustment, o.adjustment_pin, cutoff, "VOLUME", o.adjustment.adjustment_basis
            ).startswith("BLOCKED")
        ):
            return "BLOCKED_LIQUIDITY_COVERAGE", {"reason": "VOLUME_ADJUSTMENT_CONTEXT_REQUIRED"}
        usable.append(o)
    with localcontext(Context(prec=80, rounding=ROUND_HALF_EVEN, Emin=-999, Emax=999)) as math:
        math.prec = 80
        ratio = Decimal(len(usable)) / Decimal(len(needed))
        if len(usable) < p.minimum_completed_sessions or Fraction(
            len(usable), len(needed)
        ) < Fraction(p.minimum_observation_coverage):
            return "BLOCKED_LIQUIDITY_COVERAGE", {
                "reason": "INSUFFICIENT_OBSERVATIONS",
                "expected": len(needed),
                "actual": len(usable),
                "missing": missing,
            }
        if not usable:
            return "BLOCKED_LIQUIDITY_COVERAGE", {"reason": "ZERO_OBSERVATIONS"}
        from omegadata.adjustments.contracts import number

        try:
            for o in usable:
                number(o.volume, zero=True)
                number(o.turnover, zero=True)
        except (ValueError, ArithmeticError):
            return "BLOCKED_LIQUIDITY_COVERAGE", {"reason": "NUMERIC_RESOURCE_LIMIT"}
        volumes = [o.volume for o in usable if o.volume is not None]
        turnovers = sorted(o.turnover for o in usable if o.turnover is not None)
        average = sum(volumes, Decimal(0)) / Decimal(len(volumes))
        n = len(turnovers)
        median = (
            turnovers[n // 2] if n % 2 else (turnovers[n // 2 - 1] + turnovers[n // 2]) / Decimal(2)
        )
    median_exact = (
        Fraction(turnovers[n // 2])
        if n % 2
        else (Fraction(turnovers[n // 2 - 1]) + Fraction(turnovers[n // 2])) / 2
    )
    diagnostics.update(
        median_turnover_exact_ratio=(median_exact.numerator, median_exact.denominator),
        arithmetic_version="od08.liquidity-fraction-decimal80/v2",
        window=needed,
        missing=missing,
        coverage=ratio,
        average_volume=average,
        median_turnover=median,
    )
    return (
        "ELIGIBLE"
        if Fraction(sum(Fraction(v) for v in volumes), len(volumes))
        >= Fraction(p.minimum_average_volume)
        and median_exact >= Fraction(p.minimum_median_turnover)
        else "EXCLUDED_BY_POLICY"
    ), diagnostics


def reconstruct(
    rows: tuple[c.RankingCandidate, ...], top_n: int, cutoff: datetime, x: c.UniverseContext
) -> tuple[str, tuple[str, ...], tuple[tuple[str, str], ...]]:
    if not 1 <= top_n <= 10000 or len(rows) > 10000:
        raise ValueError("RANKING_BUDGET")
    if len({r.member_identity for r in rows}) != len(rows):
        raise ValueError("DUPLICATE_RANKING_MEMBER")
    accepted = []
    excluded = []
    for r in rows:
        if type(r.metric) is not Decimal or not r.metric.is_finite() or r.metric < 0:
            raise ValueError("RANKING_NUMBER")
        if availability(r.observation, cutoff, c.AvailabilityPolicy(), x) != "AVAILABLE":
            excluded.append((r.member_identity, "BLOCKED_AVAILABILITY"))
            continue
        resolution = x.identity.resolve_listing_id(
            r.observation.listing_id, r.observation.session_date, cutoff, x.mode
        )
        expected = (
            resolution.security_id
            if x.definition.identity_granularity == "SECURITY"
            else resolution.listing_id
        )
        if resolution.state != "RESOLVED" or expected != r.member_identity:
            excluded.append((r.member_identity, "UNRESOLVED_IDENTITY"))
            continue
        accepted.append(r)
    ordered = sorted(accepted, key=lambda r: (-r.metric, r.member_identity))
    return (
        "RECONSTRUCTED_PROVISIONAL",
        tuple(r.member_identity for r in ordered[:top_n]),
        tuple(
            sorted(excluded + [(r.member_identity, "BELOW_RANK_CUTOFF") for r in ordered[top_n:]])
        ),
    )
