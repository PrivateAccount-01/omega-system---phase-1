"""Bound OD07 calculation; v1 scalar/inverse comparison API remains compatible."""

from __future__ import annotations

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, DecimalException, Inexact, localcontext
from typing import Any, NoReturn

from omegadata.adjustments import bound_contracts as b
from omegadata.adjustments import contracts as c
from omegadata.adjustments.factors import factor
from omegadata.adjustments.temporal import references, select_revisions, verified
from omegadata.identity import Evidence, Resolution, query_time, text
from omegadata.identity import Policy as EvidencePolicy
from omegadata.identity_authority import EvidenceAuthority
from omegadata.session_calendar import VerifiedCalendar


class Refusal(ValueError):
    def __init__(self, status: str, reason: str) -> None:
        self.status = status
        self.reason = reason
        super().__init__(reason)


def refuse(status: str, reason: str) -> NoReturn:
    raise Refusal(status, reason)


def mode(x: c.Context) -> EvidencePolicy:
    return "CANARY_ONLY" if x.mode == "NON_MARKET_MATH" else "STRICT"


def evidence_ok(value: Any, evidence: Evidence | None, x: c.Context) -> bool:
    if evidence is None:
        return False
    return (
        evidence.eligible("CANARY_ONLY")
        if mode(x) == "CANARY_ONLY"
        else verified(value, evidence, x)
    )


def available(start: datetime | None, end: datetime | None, x: c.Context) -> None:
    if start is None:
        refuse("BLOCKED_KNOWLEDGE", "AVAILABILITY_UNKNOWN")
    query_time(start)
    if end is not None:
        query_time(end)
    if start > x.known_at or end is not None and x.known_at >= end:
        refuse("BLOCKED_KNOWLEDGE", "NOT_AVAILABLE_AT_CUTOFF")


def active_window(
    actions: tuple[c.Action, ...], raw: b.RawObservation, p: b.BasisPolicy
) -> tuple[c.Action, ...]:
    day = raw.raw.trade_date
    if p.adjustment_basis == "RAW_UNADJUSTED":
        return ()
    if p.adjustment_basis == "TOTAL_RETURN_INDEX":
        refuse("UNSUPPORTED_POLICY", "INDEX_BASE_AND_COMPLETE_REINVESTMENT_CONVENTION_REQUIRED")
    if p.adjustment_basis in {"BACKWARD_ADJUSTED", "INVERSE_FACTOR_COMPARISON"}:
        selected = [a for a in actions if a.ex_date is None or day < a.ex_date <= p.basis_date]
    else:
        selected = [a for a in actions if a.ex_date is None or p.basis_date < a.ex_date <= day]
    for a in selected:
        peers = [other for other in selected if other.ex_date == a.ex_date]
        if len(peers) > 1 and (
            any(v.sequence is None for v in peers) or len({v.sequence for v in peers}) != len(peers)
        ):
            refuse("CONFLICTING_ACTIONS", "SAME_DAY_ORDER_UNKNOWN")
    return tuple(sorted(selected, key=lambda a: (a.ex_date or day, a.sequence or 0, a.action_id)))


def validate_history(pin: b.PinnedCalculation) -> tuple[c.Action, ...]:
    h, x, p, raw = pin.history, pin.context, pin.policy, pin.raw
    if type(h.actions) is not tuple or len(h.actions) > 128:
        refuse("CONFLICTING_ACTIONS", "HISTORY_RESOURCE_OR_MUTABILITY")
    if (
        h.snapshot_version != "od07.action-history/v2"
        or h.effective_policy_version != p.version
        or h.source_evidence_version != x.source_evidence_version
        or h.known_at != x.known_at
    ):
        refuse("BLOCKED_EVIDENCE", "HISTORY_VERSION_OR_CUTOFF_MISMATCH")
    if (h.security_id, h.listing_id) != (raw.raw.security_id, raw.raw.listing_id):
        refuse("BLOCKED_IDENTITY", "HISTORY_SCOPE_IDENTITY")
    if h.history_coverage_state != "COMPLETE_FOR_DECLARED_SCOPE" or not h.coverage_reference:
        refuse("BLOCKED_EVIDENCE", "COMPLETE_HISTORY_NOT_ESTABLISHED")
    if (
        not h.valid_from <= min(raw.raw.trade_date, p.basis_date)
        or max(raw.raw.trade_date, p.basis_date) >= h.valid_to
    ):
        refuse("BLOCKED_EVIDENCE", "HISTORY_INTERVAL_NOT_COVERED")
    try:
        selected = select_revisions(h.actions, x.known_at)
    except ValueError as error:
        refuse("CONFLICTING_ACTIONS", str(error))
    if h.action_revision_ids != tuple(
        a.action_id for a in selected
    ) or h.selected_revision_digest != c.digest(selected):
        refuse("CONFLICTING_ACTIONS", "SELECTED_REVISIONS_MISSING_OR_CHANGED")
    for a in selected:
        if (
            a.security_id != h.security_id
            or a.listing_id is not None
            and a.listing_id != h.listing_id
            or a.source_id not in h.source_scope
            or a.ex_date is not None
            and not h.valid_from <= a.ex_date < h.valid_to
        ):
            refuse("CONFLICTING_ACTIONS", "ACTION_OUTSIDE_HISTORY_SCOPE")
    event_map = dict(h.economic_event_ids)
    if (
        len(event_map) != len(h.economic_event_ids)
        or set(event_map) != set(h.action_revision_ids)
        or len(set(event_map.values())) != len(event_map)
    ):
        refuse("CONFLICTING_ACTIONS", "DUPLICATE_OR_UNREVIEWED_ECONOMIC_EVENT")
    if not evidence_ok(h, h.coverage_reference, x):
        refuse("BLOCKED_EVIDENCE", "HISTORY_COVERAGE_AUTHORITY_BLOCKED")
    return selected


def identity_state(pin: b.PinnedCalculation) -> tuple[str, Resolution, Resolution]:
    r, x = pin.raw.raw, pin.context
    past = x.identity_repository.resolve_listing(
        r.exchange, r.symbol, r.series, r.trade_date, x.known_at, mode(x)
    )
    current = x.identity_repository.resolve_listing_id(
        r.listing_id, pin.policy.basis_date, x.known_at, mode(x)
    )
    if any(
        v.state != "RESOLVED" or v.security_id != r.security_id or v.listing_id != r.listing_id
        for v in (past, current)
    ):
        refuse("BLOCKED_IDENTITY", "IDENTITY_TRANSITION_BLOCKED")
    status = (
        "HISTORICALLY_VALID_BUT_NOT_TRADABLE"
        if current.lifecycle in {"SUSPENDED", "DELISTED"}
        else "SAME_LISTING_CONTINUITY"
    )
    return status, past, current


def reference_valid(
    ref: c.Reference | b.ReferenceObservation, action: c.Action, pin: b.PinnedCalculation
) -> None:
    x, r = pin.context, pin.raw
    if type(ref) is not b.ReferenceObservation:
        refuse("BLOCKED_IDENTITY", "BOUND_REFERENCE_IDENTITY_REQUIRED")
    expected_security = (
        action.parameters.successor_security_id
        if isinstance(action.parameters, c.Demerger)
        else action.security_id
    )
    if (
        ref.security_id != expected_security
        or not isinstance(action.parameters, c.Demerger)
        and ref.listing_id != r.raw.listing_id
        or ref.exchange != action.exchange
    ):
        refuse("BLOCKED_IDENTITY", "REFERENCE_INSTRUMENT_OR_VENUE_MISMATCH")
    try:
        for value in (
            ref.observation_id,
            ref.source_record_identity,
            ref.artifact_id,
            ref.source_id or "",
            ref.symbol_as_reported,
            ref.series_as_reported,
        ):
            text(value)
        if (
            type(ref.source_row_ordinal) is not int
            or ref.source_row_ordinal < 1
            or ref.reference_version != "od07.reference/v2"
        ):
            raise ValueError("REFERENCE_VERSION")
        c.number(ref.value)
    except (ValueError, TypeError):
        refuse("BLOCKED_EVIDENCE", "REFERENCE_IDENTITY_OR_VALUE_INVALID")
    if (
        ref.price_basis != "RAW_UNADJUSTED"
        or ref.price_unit != r.price_unit
        or ref.currency != r.raw.currency
    ):
        refuse("BLOCKED_EVIDENCE", "REFERENCE_PRICE_BASIS_OR_UNITS")
    available(ref.known_from, ref.known_to, x)
    for stamp in (ref.observed_at, ref.published_at):
        if stamp is not None:
            query_time(stamp)
            if stamp > x.known_at:
                refuse("BLOCKED_KNOWLEDGE", "REFERENCE_PUBLICATION_OR_OBSERVATION_FUTURE")
    expected_type = (
        "RAW_CLOSE"
        if isinstance(action.parameters, c.Rights)
        else "REINVESTMENT_PRICE"
        if isinstance(action.parameters, c.Dividend)
        else "SUCCESSOR_VALUATION"
    )
    if ref.observation_type != expected_type:
        refuse("BLOCKED_EVIDENCE", "REFERENCE_OBSERVATION_TYPE")
    resolution = x.identity_repository.resolve_listing(
        ref.exchange,
        ref.symbol_as_reported,
        ref.series_as_reported,
        ref.session_date,
        x.known_at,
        mode(x),
    )
    if (
        resolution.state != "RESOLVED"
        or resolution.security_id != ref.security_id
        or resolution.listing_id != ref.listing_id
    ):
        refuse("BLOCKED_IDENTITY", "REFERENCE_REPORTED_IDENTITY_UNRESOLVED")
    if not evidence_ok(ref, ref.evidence, x):
        refuse("BLOCKED_EVIDENCE", "REFERENCE_AUTHORITY_BLOCKED")


def snapshot_bindings(
    pin: b.PinnedCalculation,
    selected: tuple[c.Action, ...],
    identity: tuple[Resolution, Resolution] | None = None,
) -> dict[str, Any]:
    x, r, h = pin.context, pin.raw, pin.history
    known_claims = tuple(
        v
        for v in x.identity_repository.claims
        if v.known_from is None or v.known_from <= x.known_at
    )
    identity_records = {
        "issuers": x.identity_repository.issuers,
        "securities": x.identity_repository.securities,
        "listings": x.identity_repository.listings,
        "claims": known_claims,
    }
    calendar = {
        "claims": tuple(
            v
            for v in x.calendar.claims
            if v.calendar_version == x.calendar_version
            and (v.known_from is None or v.known_from <= x.known_at)
        ),
        "coverage": tuple(
            v
            for v in x.calendar.coverage
            if v.calendar_version == x.calendar_version
            and (v.known_from is None or v.known_from <= x.known_at)
        ),
    }
    active_ids = {a.action_id for a in selected}
    history = {
        "id": h.history_snapshot_id,
        "security": h.security_id,
        "listing": h.listing_id,
        "scope": h.source_scope,
        "valid_from": h.valid_from,
        "valid_to": h.valid_to,
        "known_at": h.known_at,
        "selected": selected,
        "known_lineage": tuple(
            a for a in h.actions if a.known_from is None or a.known_from <= x.known_at
        ),
        "coverage": h.history_coverage_state,
        "coverage_reference": h.coverage_reference,
        "events": h.economic_event_ids,
        "version": h.snapshot_version,
    }
    authority = x.authority or EvidenceAuthority.unconfigured()
    return {
        "raw_observation_identity": r.observation_id,
        "raw_observation_digest": c.digest(r),
        "action_history_snapshot_id": h.history_snapshot_id,
        "action_history_snapshot_digest": c.digest(history),
        "selected_action_revision_digest": c.digest(active_window(selected, r, pin.policy)),
        "identity_snapshot_id": c.digest(identity_records),
        "identity_snapshot_digest": c.digest(identity_records),
        "identity_resolution_digest": c.digest(identity),
        "calendar_version": x.calendar_version,
        "calendar_snapshot_digest": c.digest(calendar),
        "source_authority_version": x.source_evidence_version,
        "source_authority_digest": authority.snapshot_digest(),
        "knowledge_cutoff": x.known_at,
        "valid_at": x.valid_at,
        "basis_date": pin.policy.basis_date,
        "basis_policy": pin.policy,
        "consumer_policy_version": pin.policy.version,
        "calculation_algorithm_version": b.BOUND_VERSION,
        "rounding_policy_version": "decimal80-final-half-up/v1",
        "parameter_state_digest": c.digest(
            tuple(v for v in pin.parameters if v.action_revision_id in active_ids)
        ),
    }


def pin_calculation(
    snapshot_id: str,
    raw: b.RawObservation,
    history: b.HistorySnapshot,
    policy: b.BasisPolicy,
    context: c.Context,
    parameters: tuple[b.ParameterSet, ...] = (),
    execution_constraints: b.ExecutionConstraints | None = None,
) -> b.PinnedCalculation:
    text(snapshot_id)
    if (
        type(raw) is not b.RawObservation
        or type(history) is not b.HistorySnapshot
        or type(policy) is not b.BasisPolicy
        or type(parameters) is not tuple
    ):
        raise ValueError("PINNED_INPUT_TYPES")
    return b.PinnedCalculation(
        snapshot_id, raw, history, policy, context, parameters, execution_constraints
    )


def execution_state(
    pin: b.PinnedCalculation, past: Resolution | None
) -> tuple[str, str, str, bool]:
    r, x = pin.raw.raw, pin.context
    calendar = x.calendar.query(
        r.exchange, r.trade_date, x.known_at, mode(x), calendar_version=x.calendar_version
    )
    tradability = (past.lifecycle or "UNKNOWN") if past is not None else "UNKNOWN"
    if tradability != "LISTED":
        return calendar.status, tradability, "BLOCKED_LIFECYCLE", False
    if calendar.status not in {"AUTHORITATIVE_SESSION", "VERIFIED_SPECIAL_SESSION"}:
        return calendar.status, tradability, "BLOCKED_CALENDAR", False
    terms = pin.execution_constraints
    if (
        terms is None
        or terms.lot_size is None
        or terms.quantity is None
        or terms.quantity_convention is None
        or terms.settlement_policy is None
    ):
        return calendar.status, tradability, "BLOCKED_LOT_OR_SETTLEMENT_UNKNOWN", False
    if (
        (terms.security_id, terms.listing_id, terms.exchange, terms.session_date)
        != (r.security_id, r.listing_id, r.exchange, r.trade_date)
        or terms.restrictions_status != "CLEAR"
        or terms.quantity_convention != "WHOLE_UNITS"
        or not terms.settlement_policy
    ):
        return calendar.status, tradability, "BLOCKED_EXECUTION_CONSTRAINTS", False
    try:
        available(terms.known_from, None, x)
        if (
            type(terms.lot_size) is not int
            or terms.lot_size < 1
            or Decimal(terms.quantity) <= 0
            or Decimal(terms.quantity) % terms.lot_size
        ):
            raise ValueError("LOT_QUANTITY")
    except (ValueError, DecimalException):
        return calendar.status, tradability, "BLOCKED_EXECUTION_CONSTRAINTS", False
    if not evidence_ok(terms, terms.evidence, x):
        return calendar.status, tradability, "BLOCKED_EXECUTION_AUTHORITY", False
    if x.mode != "STRICT":
        return calendar.status, tradability, "BLOCKED_NON_MARKET_CONTROL", False
    return calendar.status, tradability, "ELIGIBLE_FOR_DECLARED_CONSTRAINT_SCOPE", True


def calculate_bound_chain(pin: b.PinnedCalculation) -> b.BoundResult:
    x, r, p = pin.context, pin.raw, pin.policy
    bindings: dict[str, Any] = {}
    identity_status = "UNKNOWN"
    past: Resolution | None = None
    calendar_status = "COVERAGE_UNKNOWN"
    tradability = "UNKNOWN"
    exec_status = "BLOCKED_UNKNOWN_CONSTRAINTS"
    exec_allowed = False

    def output(inner: c.Result) -> b.BoundResult:
        result = b.BoundResult(
            inner,
            c.canonical(bindings),
            p.adjustment_basis,
            p.basis_date,
            identity_status,
            calendar_status,
            tradability,
            exec_status,
            "NON_MARKET_STRUCTURAL_CONTROL"
            if x.mode == "NON_MARKET_MATH"
            else "UNVERIFIED_SOURCE_CALCULATION",
        )
        if inner.status == "CALCULATED" and exec_allowed:
            object.__setattr__(result, "execution_eligibility", True)
        return result

    try:
        if p.basis_date > x.valid_at or r.raw.trade_date > x.valid_at:
            refuse("BLOCKED_KNOWLEDGE", "OBSERVATION_OR_BASIS_AFTER_VALID_HORIZON")
        selected = validate_history(pin)
        available(r.raw.known_from, None, x)
        if not evidence_ok(r, r.raw.evidence, x):
            refuse("BLOCKED_EVIDENCE", "RAW_OBSERVATION_AUTHORITY_BLOCKED")
        identity_status, past, current = identity_state(pin)
        calendar_status, tradability, exec_status, exec_allowed = execution_state(pin, past)
        window = active_window(selected, r, p)
        bindings = snapshot_bindings(pin, selected, (past, current))
        parameters = {v.action_revision_id: v for v in pin.parameters}
        if len(parameters) != len(pin.parameters):
            refuse("BLOCKED_KNOWLEDGE", "COMPETING_PARAMETER_REVISIONS")
        pinned_calendar = VerifiedCalendar(
            tuple(v for v in x.calendar.claims if v.calendar_version == x.calendar_version),
            tuple(v for v in x.calendar.coverage if v.calendar_version == x.calendar_version),
            x.calendar.authority,
        )
        links = []
        legacy_policy = c.Policy(
            p.profile,
            "FORWARD"
            if p.adjustment_basis in {"FORWARD_ADJUSTED", "INVERSE_FACTOR_COMPARISON"}
            else "BACKWARD",
        )
        with localcontext(c.arithmetic_context()) as math:
            n = d = vn = vd = Decimal(1)
            for a in window:
                if (
                    a.exchange != r.raw.exchange
                    or a.security_id != r.raw.security_id
                    or a.listing_id is not None
                    and a.listing_id != r.raw.listing_id
                ):
                    refuse("BLOCKED_IDENTITY", "WRONG_ACTION_IDENTITY")
                available(a.known_from, a.known_to, x)
                for stamp in (a.announcement_at, a.published_at, a.parameter_known_from):
                    if stamp is not None:
                        query_time(stamp)
                        if stamp > x.known_at:
                            refuse("BLOCKED_KNOWLEDGE", "ACTION_PUBLICATION_FUTURE")
                terms = parameters.get(a.action_id)
                if (
                    terms is None
                    or terms.parameters_digest != c.digest(a.parameters)
                    or terms.parameter_revision != a.parameter_version
                    or terms.version != "od07.parameter-availability/v2"
                ):
                    refuse("BLOCKED_KNOWLEDGE", "COMPLETE_PARAMETER_AVAILABILITY_REQUIRED")
                available(terms.known_from, terms.known_to, x)
                if not evidence_ok(terms, terms.evidence, x):
                    refuse("BLOCKED_EVIDENCE", "PARAMETER_EVIDENCE_BLOCKED")
                if a.review_status in {"REVOKED", "CONFLICTING"} or not evidence_ok(
                    a, a.evidence, x
                ):
                    refuse("BLOCKED_EVIDENCE", "ACTION_EVIDENCE_BLOCKED")
                if p.adjustment_basis == "FORWARD_ADJUSTED" and a.action_type not in {
                    "SPLIT",
                    "SPLIT_REVERSE",
                    "BONUS",
                }:
                    refuse("UNSUPPORTED_POLICY", "FORWARD_ECONOMIC_TRANSFORMATION_UNDEFINED")
                for ref in references(a):
                    reference_valid(ref, a, pin)
                if a.ex_date is None:
                    refuse("BLOCKED_CALENDAR", "EX_DATE_UNKNOWN")
                session = pinned_calendar.query(
                    a.exchange, a.ex_date, x.known_at, mode(x), calendar_version=x.calendar_version
                )
                if session.status not in {"AUTHORITATIVE_SESSION", "VERIFIED_SPECIAL_SESSION"}:
                    refuse("BLOCKED_CALENDAR", "ACTION_SESSION_UNVERIFIED")
                calref = [v.claim_id for v in session.claims]
                if isinstance(a.parameters, c.Rights):
                    prior = pinned_calendar.previous_session(
                        a.exchange, a.ex_date, x.known_at, mode(x)
                    )
                    prior_reference = a.parameters.reference
                    if (
                        prior_reference is None
                        or prior_reference.session_date != prior.claims[0].session_date
                    ):
                        refuse("BLOCKED_CALENDAR", "REQUIRED_PRIOR_SESSION_OBSERVATION_MISMATCH")
                    calref.append(prior.claims[0].claim_id)
                if (
                    isinstance(a.parameters, c.Dividend)
                    and a.parameters.reinvestment is not None
                    and a.parameters.reinvestment.session_date != a.ex_date
                ):
                    refuse("BLOCKED_CALENDAR", "REINVESTMENT_SESSION_MISMATCH")
                f = factor(a.action_type, a.parameters, legacy_policy)
                if f.status not in {"CALCULATED", "NOT_APPLICABLE"}:
                    refuse(f.status, f.reason)
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
                    c.Link(
                        a.action_id,
                        a.source_artifact_identity,
                        c.digest((past, current)),
                        c.canonical(calref),
                        r.observation_id,
                        b.BOUND_VERSION,
                        p.profile,
                        c.canonical(a),
                        f,
                        "decimal80-final-half-up/v1",
                        x.known_at,
                    )
                )
            math.prec = c.PRECISION
            math.traps[Inexact] = False
            cumulative = n / d
            volume_factor = vn / vd
            price = (
                r.raw.price
                if p.profile in {"RAW", "EXECUTION", "VOLUME"}
                else (r.raw.price * n / d).quantize(
                    legacy_policy.price_quantum, rounding=ROUND_HALF_UP
                )
            )
            quantity = (
                r.raw.volume
                if p.profile in {"RAW", "EXECUTION"}
                else (r.raw.volume * vn / vd).quantize(
                    legacy_policy.volume_quantum, rounding=ROUND_HALF_UP
                )
            )
        inner = c.Result(
            "CALCULATED",
            "BOUND_MATH_NOT_FINANCIAL_RELEASE",
            r.observation_id,
            "RAW",
            p.profile,
            tuple(links),
            cumulative,
            volume_factor,
            price,
            quantity,
            c.canonical({"bindings": bindings, "raw": r, "selected_actions": window, "policy": p}),
            version=b.BOUND_VERSION,
        )
        return output(inner)
    except Refusal as error:
        return output(
            c.Result(
                error.status,
                error.reason,
                r.observation_id,
                consumer_profile=p.profile,
                version=b.BOUND_VERSION,
            )
        )
    except (ValueError, TypeError, DecimalException) as error:
        return output(
            c.Result(
                "INVALID_PARAMETERS",
                str(error),
                r.observation_id,
                consumer_profile=p.profile,
                version=b.BOUND_VERSION,
            )
        )
