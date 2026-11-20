"""Indexed observation matching, economic comparability and deterministic reconciliation."""

from decimal import Decimal
from fractions import Fraction
from typing import cast

from omegadata.identity_authority import EvidenceAuthority
from omegadata.reconciliation import contracts as c
from omegadata.reconciliation.metrics import difference
from omegadata.universe.contracts import AvailabilityPolicy
from omegadata.universe.observation_binding import validate_binding
from omegadata.universe.temporal import availability


def match_candidates(
    x: c.ComparisonContext,
) -> tuple[tuple[tuple[c.Observation, ...], tuple[c.Observation, ...]], ...]:
    groups: dict[tuple[str, ...], list[list[c.Observation]]] = {}
    for side, rows in enumerate((x.left, x.right)):
        for o in rows:
            # Venue/listing and observation semantics are checked after candidate generation.
            # Index by economic identity/date/field; no Cartesian matching or dictionary overwrite.
            key = (o.security_id or "<UNKNOWN>", o.session_date.isoformat(), o.field_name)
            if key not in groups:
                groups[key] = [[], []]
            groups[key][side].append(o)
    if len(groups) > x.maximum_matches:
        raise ValueError("MATCHING_RESOURCE_LIMIT")
    return tuple(
        (
            tuple(sorted(v[0], key=lambda o: o.observation_id)),
            tuple(sorted(v[1], key=lambda o: o.observation_id)),
        )
        for _, v in sorted(groups.items())
    )


def comparability(
    left: c.Observation, right: c.Observation, x: c.ComparisonContext
) -> tuple[str, tuple[str, ...]]:
    p = x.policy
    if left.security_id is None or right.security_id is None:
        return "IDENTITY_UNRESOLVED", ("UNKNOWN_IDENTITY",)
    if left.security_id != right.security_id:
        return "IDENTITY_UNRESOLVED", ("DIFFERENT_SECURITY",)
    cross = left.exchange != right.exchange
    if cross and p.comparison_scope != "CROSS_VENUE_DIAGNOSTIC":
        return "SAME_SECURITY_DIFFERENT_VENUE", ("EXPLICIT_VENUE_POLICY_REQUIRED",)
    if cross and (
        p.field_name not in {"close", "reference_price"}
        or p.metric_definition not in {"ABSOLUTE", "REFERENCE_RELATIVE", "SYMMETRIC_RELATIVE"}
    ):
        return "SAME_SECURITY_DIFFERENT_VENUE", ("UNSUPPORTED_CROSS_VENUE_SEMANTICS",)
    if not cross and left.listing_id != right.listing_id:
        return "IDENTITY_UNRESOLVED", ("DIFFERENT_LISTING",)
    if (
        left.session_date != right.session_date
        or left.observation_interval != right.observation_interval
    ):
        return "INCOMPATIBLE_SESSION", ("SESSION_MISMATCH",)
    if (
        left.observation_type != right.observation_type
        or left.observation_type != p.observation_type
        or left.field_name != right.field_name
        or left.field_name != p.field_name
    ):
        return "INCOMPATIBLE_OBSERVATION_TYPE", ("FIELD_OR_TYPE_MISMATCH",)
    if (left.availability.price_basis, left.availability.currency, left.unit) != (
        right.availability.price_basis,
        right.availability.currency,
        right.unit,
    ):
        return "INCOMPATIBLE_PRICE_BASIS", ("PRICE_BASIS_OR_UNIT_MISMATCH",)
    if left.availability.volume_basis != right.availability.volume_basis:
        return "INCOMPATIBLE_VOLUME_BASIS", ("VOLUME_BASIS_MISMATCH",)
    if (
        (left.availability.currency, left.unit) != (p.currency, p.unit)
        or (left.source_id, right.source_id) != p.source_pair_scope
        or left.exchange not in p.venue_scope
        or right.exchange not in p.venue_scope
    ):
        return "SOURCE_BLOCKED", ("POLICY_SCOPE_MISMATCH",)
    if (
        not p.effective_from <= x.valid_at
        or p.effective_to is not None
        and x.valid_at >= p.effective_to
        or p.known_from > x.known_at
        or p.known_to is not None
        and x.known_at >= p.known_to
        or p.calibration_knowledge_cutoff is not None
        and p.calibration_knowledge_cutoff > x.known_at
    ):
        return "AVAILABILITY_UNKNOWN", ("POLICY_OR_CALIBRATION_NOT_KNOWN",)
    for o in (left, right):
        if o.value is None or o.imputed or not o.publisher_identity or not o.source_record_identity:
            return "SOURCE_BLOCKED", ("MISSING_OR_IMPUTED_INPUT",)
        a = o.availability
        expected = (
            a.volume
            if o.field_name == "volume"
            else a.turnover
            if o.field_name == "turnover"
            else a.price_value
        )
        if o.value != expected:
            return "INCOMPATIBLE_OBSERVATION_TYPE", ("CONSUMED_FIELD_NOT_BOUND",)
        state = availability(a, x.known_at, AvailabilityPolicy(), x.universe)
        if state != "AVAILABLE":
            return (
                "SOURCE_BLOCKED" if state == "BLOCKED_SOURCE_RIGHTS" else "AVAILABILITY_UNKNOWN"
            ), (state,)
        resolution = x.universe.identity.resolve_listing_id(
            o.listing_id, o.session_date, x.known_at, x.universe.mode
        )
        if resolution.state != "RESOLVED" or resolution.security_id != o.security_id:
            return "IDENTITY_UNRESOLVED", ("UNKNOWN_IDENTITY",)
        listing = next(
            (
                listing
                for listing in x.universe.identity.listings
                if listing.listing_id == o.listing_id
            ),
            None,
        )
        if listing is None or listing.exchange != o.exchange:
            return "IDENTITY_UNRESOLVED", ("VENUE_IDENTITY_MISMATCH",)
        adjusted = (
            a.volume_basis != "RAW"
            if o.field_name == "volume"
            else a.price_basis != "RAW_UNADJUSTED"
        )
        if adjusted:
            if validate_binding(a, a.adjustment_binding, x.known_at).startswith("BLOCKED"):
                return "INCOMPATIBLE_PRICE_BASIS", ("EXACT_ADJUSTMENT_BINDING_REQUIRED",)
            if a.adjustment_pin is None:
                return "INCOMPATIBLE_PRICE_BASIS", ("ADJUSTMENT_CONTEXT_MISSING",)
    if (
        left.availability.adjustment_pin is not None
        or right.availability.adjustment_pin is not None
    ):
        left_pin, right_pin = left.availability.adjustment_pin, right.availability.adjustment_pin
        if (
            left_pin is None
            or right_pin is None
            or (
                left_pin.policy,
                left_pin.history.selected_revision_digest,
                left_pin.context.known_at,
            )
            != (
                right_pin.policy,
                right_pin.history.selected_revision_digest,
                right_pin.context.known_at,
            )
        ):
            return "INCOMPATIBLE_PRICE_BASIS", ("ADJUSTMENT_METHODOLOGY_MISMATCH",)
    reasons = []
    if not left.source_lineage_root or not right.source_lineage_root:
        reasons.append("SOURCE_INDEPENDENCE_UNKNOWN")
    elif (
        left.source_lineage_root == right.source_lineage_root
        or left.source_artifact_identity == right.source_artifact_identity
    ):
        reasons.append("DEPENDENT_SOURCE_LINEAGE")
    if p.calibration_state != "APPROVED_AUTHENTIC_CALIBRATION":
        reasons.append("UNCALIBRATED_OR_NON_MARKET_POLICY")
    return (
        "EXPLICITLY_NORMALIZED_COMPARISON" if cross else "SAME_VENUE_EQUIVALENT_OBSERVATION"
    ), tuple(reasons)


def reconcile_context(x: c.ComparisonContext) -> tuple[c.ReconciliationResult, ...]:
    results = []
    context_digest = c.fingerprint(x)
    policy_digest = c.fingerprint(x.policy)
    source_authority = (x.universe.authority or EvidenceAuthority.unconfigured()).snapshot_digest()
    for left, right in match_candidates(x):
        metric = None
        reasons: tuple[str, ...]
        if not left or not right:
            classification, reasons = "MISSING_COUNTERPART", ("MISSING_OBSERVATION",)
        elif len(left) != 1 or len(right) != 1:
            classification, reasons = "CONFLICTING_COUNTERPARTS", ("DUPLICATE_OBSERVATION",)
        else:
            classification, reasons = comparability(left[0], right[0], x)
        outcome = "UNCOMPARABLE"
        if classification in {
            "SAME_VENUE_EQUIVALENT_OBSERVATION",
            "EXPLICITLY_NORMALIZED_COMPARISON",
        }:
            metric = difference(
                cast(Decimal, left[0].value),
                cast(Decimal, right[0].value),
                x.policy.metric_definition,
                tick=x.policy.tick_size,
            )
            if metric.exact_ratio is None:
                reasons += (metric.status,)
            else:
                score = abs(Fraction(*metric.exact_ratio))
                outcome = (
                    "PASS"
                    if score <= Fraction(x.policy.warning_threshold)
                    else "WARN"
                    if score < Fraction(x.policy.failure_threshold)
                    else "FAIL"
                )
                if classification == "EXPLICITLY_NORMALIZED_COMPARISON":
                    reasons += ("VENUE_DIAGNOSTIC_NOT_PARSER_CORRUPTION",)
        ids = (tuple(o.observation_id for o in left), tuple(o.observation_id for o in right))
        result_id = c.fingerprint((x.context_id, ids, x.policy.policy_version, x.known_at))
        results.append(
            c.ReconciliationResult(
                result_id,
                x.context_id,
                ids[0],
                tuple(c.fingerprint(o) for o in left),
                ids[1],
                tuple(c.fingerprint(o) for o in right),
                x.policy.field_name,
                classification,
                metric,
                policy_digest,
                context_digest,
                source_authority,
                x.valid_at,
                x.known_at,
                outcome,
                reasons,
            )
        )
    return tuple(results)


def eligibility(
    confidence: Decimal,
    status: str,
    blocks: tuple[str, ...],
    *,
    mode: str = "STRICT",
    source_authority_status: str = "UNVERIFIED",
    identity_status: str = "UNKNOWN",
    availability_status: str = "UNKNOWN",
    coverage_status: str = "UNKNOWN",
    review_status: str = "OPEN",
    reprocess_status: str = "NOT_VERIFIED",
) -> c.EligibilityDecision:
    if (
        type(confidence) is not Decimal
        or not confidence.is_finite()
        or not Decimal(0) <= confidence <= Decimal(1)
    ):
        raise ValueError("CONFIDENCE_RANGE")
    reasons = list(blocks)
    if status == "UNCOMPARABLE":
        reasons.append("UNCOMPARABLE")
    if status == "FAIL":
        reasons.append("RECONCILIATION_FAILED")
    for state, required, reason in (
        (source_authority_status, "VERIFIED", "SOURCE_AUTHORITY_UNVERIFIED"),
        (identity_status, "RESOLVED", "UNKNOWN_IDENTITY"),
        (availability_status, "AVAILABLE", "AVAILABILITY_UNKNOWN"),
        (coverage_status, "COMPLETE_VERIFIED", "INCOMPLETE_REQUIRED_HISTORY"),
        (review_status, "CLOSED", "UNRESOLVED_CRITICAL_ANOMALY"),
        (reprocess_status, "VERIFIED", "REPROCESS_NOT_COMPLETED"),
    ):
        if state != required:
            reasons.append(reason)
    if mode != "STRICT":
        reasons.append("NON_MARKET_CONTROL")
    # OD11 release and real-reference gates are intentionally outside this implementation.
    reasons.append("FINANCIAL_ACCEPTANCE_NOT_SUPPLIED")
    return c.EligibilityDecision(
        confidence,
        status,
        source_authority_status,
        identity_status,
        availability_status,
        coverage_status,
        review_status,
        reprocess_status,
        tuple(sorted(set(reasons))),
    )
