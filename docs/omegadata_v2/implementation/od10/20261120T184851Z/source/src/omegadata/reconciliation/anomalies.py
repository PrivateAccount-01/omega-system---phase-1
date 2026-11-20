"""Explainable anomalies are diagnostic evidence, never automatic data repairs."""

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import cast

from omegadata.reconciliation import contracts as c
from omegadata.reconciliation.contracts import ComparisonContext, fingerprint
from omegadata.reconciliation.metrics import difference
from omegadata.universe.contracts import AvailabilityObservation
from omegadata.universe.observation_binding import validate_binding


def structural_anomalies(
    fields: dict[str, Decimal | None], *, ohlc_semantics: str | None = None
) -> tuple[str, ...]:
    if any(
        v is not None and (type(v) is not Decimal or not v.is_finite()) for v in fields.values()
    ):
        return ("STRUCTURAL_INVALIDITY",)
    if fields.get("volume") is not None and cast(Decimal, fields["volume"]) < 0:
        return ("STRUCTURAL_INVALIDITY",)
    if ohlc_semantics == "STANDARD":
        if any(fields.get(k) is None for k in ("open", "high", "low", "close")):
            return ("MISSING_OBSERVATION",)
        o, h, low, close = (cast(Decimal, fields[k]) for k in ("open", "high", "low", "close"))
        if min(o, h, low, close) < 0 or h < max(o, close) or low > min(o, close) or low > h:
            return ("STRUCTURAL_INVALIDITY",)
    return ()


def discontinuity(
    previous: c.Observation,
    current: c.Observation,
    x: c.ComparisonContext,
    threshold: Decimal,
    normalized_previous: AvailabilityObservation | None,
) -> str:
    if (
        previous.security_id != current.security_id
        or previous.listing_id != current.listing_id
        or previous.exchange != current.exchange
    ):
        return "IDENTITY_CONFLICT"
    if previous.session_date > current.session_date:
        return "TEMPORAL_INCONSISTENCY"
    if previous.value is None or current.value is None:
        return "MISSING_OBSERVATION"
    from omegadata.universe.contracts import AvailabilityPolicy
    from omegadata.universe.temporal import availability

    if any(
        availability(o.availability, x.known_at, AvailabilityPolicy(), x.universe) != "AVAILABLE"
        for o in (previous, current)
    ):
        return "TEMPORAL_INCONSISTENCY"
    metric = difference(current.value, previous.value, "REFERENCE_RELATIVE")
    if metric.exact_ratio is None:
        return "UNCOMPARABLE"
    if Fraction(*metric.exact_ratio) <= Fraction(threshold):
        return "NO_DISCONTINUITY"
    if normalized_previous is not None and validate_binding(
        normalized_previous, normalized_previous.adjustment_binding, x.known_at
    ).startswith("ELIGIBLE"):
        binding = normalized_previous.adjustment_binding
        if (
            binding is not None
            and (
                binding.security_id,
                binding.listing_id,
                binding.exchange,
                binding.session_date,
                binding.source_record_identity,
                binding.source_artifact_identity,
            )
            == (
                previous.security_id,
                previous.listing_id,
                previous.exchange,
                previous.session_date,
                previous.source_record_identity,
                previous.source_artifact_identity,
            )
            and binding.basis_date == current.session_date
        ):
            normalized = difference(current.value, binding.numerical_value, "REFERENCE_RELATIVE")
            if normalized.exact_ratio is not None and Fraction(*normalized.exact_ratio) <= Fraction(
                threshold
            ):
                return "CORPORATE_ACTION_DISCONTINUITY"
    return "UNEXPLAINED_DISCONTINUITY"


def persistent_discrepancy(
    values: tuple[Decimal, ...], threshold: Decimal, *, minimum_samples: int
) -> str:
    if not 1 <= minimum_samples <= 10000 or len(values) > 10000:
        raise ValueError("ANOMALY_RESOURCE_LIMIT")
    if type(threshold) is not Decimal or not threshold.is_finite() or threshold < 0:
        raise ValueError("ANOMALY_THRESHOLD")
    if len(values) < minimum_samples:
        return "INSUFFICIENT_OBSERVATIONS"
    if any(
        type(v) is not Decimal
        or not v.is_finite()
        or len(v.as_tuple().digits) > 64
        or abs(int(v.as_tuple().exponent)) > 64
        for v in values
    ):
        raise ValueError("ANOMALY_NUMBER")
    if (all(v > 0 for v in values) or all(v < 0 for v in values)) and all(
        abs(Fraction(v)) >= Fraction(threshold) for v in values
    ):
        return "PERSISTENT_DIRECTIONAL_DISCREPANCY"
    return "NO_PERSISTENT_DIRECTION"


@dataclass(frozen=True)
class AnomalyRecord:
    anomaly_id: str
    context_id: str
    reconciliation_id: str
    observation_ids: tuple[str, ...]
    classification: str
    reason_codes: tuple[str, ...]
    policy_digest: str
    context_digest: str
    version: str = "od09.anomaly/v1"


def evaluate_anomalies(x: ComparisonContext) -> tuple[AnomalyRecord, ...]:
    from omegadata.reconciliation.engine import reconcile_context

    result = []
    for value in reconcile_context(x):
        if value.outcome == "PASS":
            continue
        if value.comparability == "CONFLICTING_COUNTERPARTS":
            kind = "DUPLICATE_OBSERVATION"
        elif value.comparability == "MISSING_COUNTERPART":
            kind = "MISSING_OBSERVATION"
        elif value.comparability in {
            "SAME_SECURITY_DIFFERENT_VENUE",
            "EXPLICITLY_NORMALIZED_COMPARISON",
        }:
            kind = "EXPECTED_VENUE_DIFFERENCE"
        elif value.outcome == "UNCOMPARABLE":
            kind = "UNCOMPARABLE"
        else:
            kind = "CROSS_SOURCE_DISCREPANCY"
        result.append(
            AnomalyRecord(
                fingerprint((value.result_digest, kind)),
                x.context_id,
                value.reconciliation_id,
                value.left_observation_ids + value.right_observation_ids,
                kind,
                value.reason_codes,
                value.policy_digest,
                fingerprint(x),
            )
        )
    return tuple(result)
