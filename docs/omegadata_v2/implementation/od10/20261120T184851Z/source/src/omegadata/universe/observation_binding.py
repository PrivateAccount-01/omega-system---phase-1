"""Exact field-level OD07 consumption contract; replay is not source authentication."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from omegadata.adjustments.contracts import digest, number
from omegadata.identity import query_time
from omegadata.universe.contracts import AvailabilityObservation


@dataclass(frozen=True)
class AdjustmentBinding:
    availability_observation_id: str
    source_record_identity: str
    source_artifact_identity: str
    security_id: str
    listing_id: str
    exchange: str
    session_date: date
    raw_observation_id: str
    raw_observation_digest: str
    adjustment_context_id: str
    adjustment_result_digest: str
    adjustment_profile: str
    adjustment_basis: str
    basis_date: date
    currency: str
    price_unit: str
    volume_unit: str
    consumed_field: str
    numerical_value: Decimal
    knowledge_cutoff: datetime
    version: str = "od08.observation-binding/v2"


def validate_binding(
    o: AvailabilityObservation, b: AdjustmentBinding | None, cutoff: datetime
) -> str:
    from omegadata.universe.eligibility import adjustment_eligible

    blocked = "BLOCKED_OBSERVATION_BINDING"
    if b is None or type(b) is not AdjustmentBinding or b.version != "od08.observation-binding/v2":
        return blocked
    pin = o.adjustment_pin
    result = o.adjustment
    if pin is None or result is None:
        return blocked
    try:
        query_time(cutoff)
        query_time(b.knowledge_cutoff)
        number(b.numerical_value, zero=True)
        raw = pin.raw.raw
        if (
            b.availability_observation_id,
            b.source_record_identity,
            b.source_artifact_identity,
            b.listing_id,
            b.session_date,
            b.currency,
            b.price_unit,
        ) != (
            o.observation_id,
            o.record_identity,
            o.artifact_identity,
            o.listing_id,
            o.session_date,
            o.currency,
            o.price_unit,
        ):
            return blocked
        if (
            b.security_id,
            b.listing_id,
            b.exchange,
            b.session_date,
            b.source_artifact_identity,
            b.source_record_identity,
            b.currency,
            b.price_unit,
        ) != (
            raw.security_id,
            raw.listing_id,
            raw.exchange,
            raw.trade_date,
            raw.artifact_id,
            pin.raw.source_record_identity,
            raw.currency,
            pin.raw.price_unit,
        ):
            return blocked
        if o.source_id != pin.raw.source_id or (
            b.raw_observation_id,
            b.raw_observation_digest,
            b.adjustment_context_id,
            b.adjustment_result_digest,
        ) != (pin.raw.observation_id, digest(pin.raw), pin.snapshot_id, result.output_digest):
            return blocked
        if (b.adjustment_profile, b.adjustment_basis, b.basis_date, b.knowledge_cutoff) != (
            pin.policy.profile,
            result.adjustment_basis,
            result.basis_date,
            pin.context.known_at,
        ) or b.knowledge_cutoff > cutoff:
            return blocked
        if b.consumed_field == "volume":
            if (
                b.volume_unit != "SHARES"
                or b.adjustment_profile != "VOLUME"
                or o.volume_basis != b.adjustment_basis
                or b.numerical_value != o.volume
                or o.volume != result.calculation.adjusted_volume
            ):
                return blocked
        elif b.consumed_field == "price":
            if (
                o.price_basis != b.adjustment_basis
                or o.price_value != b.numerical_value
                or b.numerical_value != result.adjusted_price
            ):
                return blocked
        else:
            return blocked
        return adjustment_eligible(result, pin, cutoff, b.adjustment_profile, b.adjustment_basis)
    except (ValueError, ArithmeticError, TypeError):
        return blocked
