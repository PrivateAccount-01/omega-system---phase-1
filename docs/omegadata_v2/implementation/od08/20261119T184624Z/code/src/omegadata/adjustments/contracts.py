"""Versioned immutable inputs. NON_MARKET_MATH is permanently publication-ineligible."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import UTC, date, datetime
from decimal import (
    ROUND_HALF_EVEN,
    Decimal,
    DivisionByZero,
    Inexact,
    InvalidOperation,
    Overflow,
)
from decimal import (
    Context as DecimalContext,
)
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from omegadata.adjustments.bound_contracts import ReferenceObservation

from omegadata.identity import Evidence, MemoryIdentityRepository, aware, query_time, text
from omegadata.identity_authority import EvidenceAuthority
from omegadata.session_calendar import VerifiedCalendar

VERSION = "od07.calc/v1"
PRECISION = 80


def normalized(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return normalized(asdict(value))
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("NONFINITE_CANONICAL")
        return str(value)
    if isinstance(value, datetime):
        query_time(value)
        return value.astimezone(UTC).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: normalized(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [normalized(v) for v in value]
    return value


def canonical(value: Any) -> str:
    return json.dumps(normalized(value), sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def number(value: Any, *, zero: bool = False) -> Decimal:
    if (
        type(value) is not Decimal
        or not value.is_finite()
        or value < 0
        or (not zero and value == 0)
    ):
        raise ValueError("INVALID_DECIMAL")
    if len(value.as_tuple().digits) > 64 or abs(int(value.as_tuple().exponent)) > 64:
        raise ValueError("DECIMAL_RESOURCE_LIMIT")
    return value


@dataclass(frozen=True)
class Reference:
    value: Decimal
    session_date: date
    known_from: datetime | None
    artifact_id: str
    currency: str
    evidence: Evidence | None = None
    source_id: str | None = None


@dataclass(frozen=True)
class Split:
    multiplier: Decimal


@dataclass(frozen=True)
class Bonus:
    new_shares: Decimal
    existing_shares: Decimal


@dataclass(frozen=True)
class Rights:
    existing_shares: Decimal
    new_shares: Decimal
    subscription_price: Decimal | None
    reference: Reference | ReferenceObservation | None
    currency: str
    exercise_assumed: bool | None


@dataclass(frozen=True)
class Dividend:
    amount: Decimal
    currency: str
    reinvestment: Reference | ReferenceObservation | None
    convention: str | None


@dataclass(frozen=True)
class Merger:
    successor_security_id: str | None
    exchange_ratio: Decimal | None
    cash_component: Decimal | None


@dataclass(frozen=True)
class Demerger:
    successor_security_id: str | None
    entitlement_ratio: Decimal | None
    successor_value: Reference | ReferenceObservation | None


@dataclass(frozen=True)
class Conversion:
    successor_security_id: str | None
    exchange_ratio: Decimal | None


@dataclass(frozen=True)
class Lifecycle:
    constraint: str = "NO_PRICE_FACTOR"


Parameters = Split | Bonus | Rights | Dividend | Merger | Demerger | Conversion | Lifecycle


@dataclass(frozen=True)
class Action:
    action_id: str
    action_type: str
    security_id: str
    listing_id: str | None
    exchange: str
    evidence: Evidence
    source_artifact_identity: str
    ex_date: date | None
    known_from: datetime | None
    known_to: datetime | None
    parameters: Parameters
    source_id: str
    announcement_at: datetime | None = None
    published_at: datetime | None = None
    effective_date: date | None = None
    record_date: date | None = None
    ingested_at: datetime | None = None
    parameter_known_from: datetime | None = None
    parameter_version: str = "od07.parameters/v1"
    action_revision: int = 1
    supersedes_action_id: str | None = None
    review_status: str = "UNVERIFIED"
    sequence: int | None = None
    version: str = "od07.action/v1"

    def __post_init__(self) -> None:
        for v in (
            self.action_id,
            self.action_type,
            self.security_id,
            self.exchange,
            self.source_id,
            self.source_artifact_identity,
        ):
            text(v)
        if self.listing_id is not None:
            text(self.listing_id)
        for t in (
            self.known_from,
            self.known_to,
            self.announcement_at,
            self.published_at,
            self.ingested_at,
            self.parameter_known_from,
        ):
            aware(t)
        for d in (self.ex_date, self.effective_date, self.record_date):
            if d is not None and type(d) is not date:
                raise ValueError("DATE_REQUIRED")
        if self.known_to is not None and (
            self.known_from is None or self.known_to <= self.known_from
        ):
            raise ValueError("KNOWLEDGE_INTERVAL")
        if (
            self.version != "od07.action/v1"
            or self.parameter_version != "od07.parameters/v1"
            or type(self.action_revision) is not int
            or self.action_revision < 1
        ):
            raise ValueError("ACTION_VERSION")
        if type(self.parameters) not in (
            Split,
            Bonus,
            Rights,
            Dividend,
            Merger,
            Demerger,
            Conversion,
            Lifecycle,
        ):
            raise ValueError("PARAMETER_TYPE")
        if self.sequence is not None and (type(self.sequence) is not int or self.sequence < 0):
            raise ValueError("ACTION_SEQUENCE")
        if self.review_status not in {"UNVERIFIED", "REVIEWED", "REVOKED", "CONFLICTING"}:
            raise ValueError("REVIEW_STATUS")


@dataclass(frozen=True)
class Raw:
    artifact_id: str
    security_id: str
    listing_id: str
    exchange: str
    symbol: str
    series: str
    trade_date: date
    known_from: datetime | None
    price: Decimal
    volume: Decimal
    currency: str
    evidence: Evidence
    original_price_basis: str = "RAW"

    def __post_init__(self) -> None:
        for v in (
            self.artifact_id,
            self.security_id,
            self.listing_id,
            self.exchange,
            self.symbol,
            self.series,
            self.currency,
        ):
            text(v)
        if type(self.trade_date) is not date or self.original_price_basis != "RAW":
            raise ValueError("RAW_BASIS_OR_DATE")
        aware(self.known_from)
        number(self.price)
        number(self.volume, zero=True)


@dataclass(frozen=True)
class Policy:
    profile: str
    direction: str = "BACKWARD"
    version: str = "od07.policy/v1"
    price_quantum: Decimal = Decimal("0.000001")
    volume_quantum: Decimal = Decimal("0.0001")

    def __post_init__(self) -> None:
        if (
            self.profile not in {"RAW", "EXECUTION", "PRICE_RETURN", "TOTAL_RETURN", "VOLUME"}
            or self.direction not in {"BACKWARD", "FORWARD"}
            or self.version != "od07.policy/v1"
        ):
            raise ValueError("UNSUPPORTED_POLICY")
        if self.price_quantum != Decimal(".000001") or self.volume_quantum != Decimal(".0001"):
            raise ValueError("ROUNDING_VERSION")


@dataclass(frozen=True)
class Context:
    valid_at: date
    known_at: datetime
    identity_version: str
    source_evidence_version: str
    calendar_version: str
    mode: str
    identity_repository: MemoryIdentityRepository
    calendar: VerifiedCalendar
    authority: EvidenceAuthority | None = field(default=None, compare=False, repr=False)

    def __post_init__(self) -> None:
        query_time(self.known_at)
        if type(self.valid_at) is not date or self.mode not in {"STRICT", "NON_MARKET_MATH"}:
            raise ValueError("CONTEXT")
        if self.identity_version != "od06.identity/v1":
            raise ValueError("IDENTITY_VERSION")
        for v in (self.source_evidence_version, self.calendar_version):
            text(v)
        if (
            type(self.identity_repository) is not MemoryIdentityRepository
            or type(self.calendar) is not VerifiedCalendar
        ):
            raise ValueError("UPSTREAM_TYPE")
        if self.authority is not None and type(self.authority) is not EvidenceAuthority:
            raise ValueError("AUTHORITY_TYPE")


@dataclass(frozen=True)
class Factor:
    status: str
    reason: str
    numerator: Decimal | None = None
    denominator: Decimal | None = None
    price_factor: Decimal | None = None
    volume_numerator: Decimal | None = None
    volume_denominator: Decimal | None = None
    volume_factor: Decimal | None = None


@dataclass(frozen=True)
class Link:
    action_revision_id: str
    source_artifact_id: str
    identity_resolution_id: str
    calendar_reference: str
    raw_observation_reference: str
    calculation_version: str
    consumer_profile: str
    input_parameters: str
    factor: Factor
    rounding_policy: str
    knowledge_cutoff: datetime


@dataclass(frozen=True)
class Result:
    status: str
    reason: str
    original_raw_reference: str = ""
    original_price_basis: str = "RAW"
    consumer_profile: str = ""
    adjustment_factor_chain: tuple[Link, ...] = ()
    cumulative_factor: Decimal | None = None
    cumulative_volume_factor: Decimal | None = None
    adjusted_price: Decimal | None = None
    adjusted_volume: Decimal | None = None
    inputs: str = ""
    publication_eligibility: bool = field(default=False, init=False)
    version: str = VERSION

    def __post_init__(self) -> None:
        allowed = {
            "CALCULATED",
            "NOT_APPLICABLE",
            "BLOCKED_EVIDENCE",
            "BLOCKED_KNOWLEDGE",
            "BLOCKED_IDENTITY",
            "BLOCKED_CALENDAR",
            "INVALID_PARAMETERS",
            "CONFLICTING_ACTIONS",
            "UNSUPPORTED_POLICY",
        }
        if self.status not in allowed or type(self.adjustment_factor_chain) is not tuple:
            raise ValueError("RESULT_CONTRACT")
        if self.status == "CALCULATED":
            if not self.inputs or not self.original_raw_reference:
                raise ValueError("INCOMPLETE_RESULT")
            for v in (self.cumulative_factor, self.cumulative_volume_factor, self.adjusted_price):
                if type(v) is not Decimal or not v.is_finite() or v <= 0:
                    raise ValueError("RESULT_NUMBER")
            if (
                type(self.adjusted_volume) is not Decimal
                or not self.adjusted_volume.is_finite()
                or self.adjusted_volume < 0
            ):
                raise ValueError("RESULT_VOLUME")
        elif self.adjustment_factor_chain or any(
            v is not None
            for v in (
                self.adjusted_price,
                self.adjusted_volume,
                self.cumulative_factor,
                self.cumulative_volume_factor,
            )
        ):
            raise ValueError("PARTIAL_ACCEPTED_OUTPUT_REFUSED")

    @property
    def canonical_json(self) -> str:
        return canonical(self)

    @property
    def output_digest(self) -> str:
        return hashlib.sha256(self.canonical_json.encode()).hexdigest()


def arithmetic_context() -> DecimalContext:
    """Pin all ambient state; reject inexact intermediate multiplication."""
    return DecimalContext(
        prec=20480,
        rounding=ROUND_HALF_EVEN,
        Emin=-999999,
        Emax=999999,
        traps=[InvalidOperation, DivisionByZero, Overflow, Inexact],
    )
