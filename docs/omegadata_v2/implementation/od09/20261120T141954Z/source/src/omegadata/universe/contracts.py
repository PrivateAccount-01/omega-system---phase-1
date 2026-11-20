"""Immutable OD08 contracts. Anonymous controls never confer financial authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omegadata.universe.observation_binding import AdjustmentBinding

from omegadata.adjustments.bound_contracts import BoundResult, PinnedCalculation
from omegadata.adjustments.contracts import canonical, digest
from omegadata.identity import (
    Evidence,
    MemoryIdentityRepository,
    Policy,
    intervals,
    query_time,
    text,
)
from omegadata.identity_adapters import MembershipClaim
from omegadata.identity_authority import EvidenceAuthority
from omegadata.session_calendar import VerifiedCalendar


@dataclass(frozen=True)
class UniverseDefinition:
    universe_id: str
    universe_name: str
    universe_type: str
    identity_granularity: str
    methodology_version: str
    source_scope: tuple[str, ...]
    exchange_scope: tuple[str, ...]
    valid_from: date
    valid_to: date | None
    known_from: datetime | None
    known_to: datetime | None
    evidence: Evidence
    version: str = "od08.definition/v1"

    def __post_init__(self) -> None:
        if type(self.source_scope) is not tuple or type(self.exchange_scope) is not tuple:
            raise ValueError("IMMUTABLE_DEFINITION_SCOPE_REQUIRED")
        for v in (self.universe_id, self.universe_name, self.methodology_version):
            text(v)
        intervals(self.valid_from, self.valid_to, self.known_from, self.known_to)
        if (
            self.universe_type
            not in {
                "OFFICIAL_INDEX",
                "EXCHANGE_LISTED_UNIVERSE",
                "RESEARCH_ELIGIBLE_UNIVERSE",
                "PROVISIONAL_RECONSTRUCTION",
                "CUSTOM_POLICY_UNIVERSE",
            }
            or self.identity_granularity not in {"SECURITY", "LISTING"}
            or not self.source_scope
            or not self.exchange_scope
            or self.version != "od08.definition/v1"
        ):
            raise ValueError("UNIVERSE_DEFINITION")


@dataclass(frozen=True)
class MembershipRevision:
    claim: MembershipClaim
    event_id: str
    source_id: str
    artifact_identity: str
    record_identity: str
    security_id: str | None = None
    listing_id: str | None = None
    event_type: str = "ADD"
    announcement_at: datetime | None = None
    published_at: datetime | None = None
    ingested_at: datetime | None = None
    revision_number: int = 1
    effective_convention: str = "SOURCE_DATE"
    version: str = "od08.membership/v1"
    effective_at: datetime | None = None
    removal_effective_at: datetime | None = None

    @property
    def revision_id(self) -> str:
        return self.claim.membership_id

    @property
    def evidence(self) -> Evidence:
        return self.claim.evidence

    @property
    def universe_id(self) -> str:
        return self.claim.index_name

    def __post_init__(self) -> None:
        for v in (self.event_id, self.source_id, self.artifact_identity, self.record_identity):
            text(v)
        for stamp in (
            self.announcement_at,
            self.published_at,
            self.ingested_at,
            self.effective_at,
            self.removal_effective_at,
        ):
            if stamp is not None:
                query_time(stamp)
        if (
            self.event_type not in {"ADD", "CORRECTION", "CANCEL", "REMOVE"}
            or self.revision_number < 1
            or self.version != "od08.membership/v1"
            or self.effective_convention not in {"SOURCE_DATE", "EXPLICIT_TIMESTAMP", "UNKNOWN"}
        ):
            raise ValueError("MEMBERSHIP_VERSION")
        from zoneinfo import ZoneInfo

        if (
            self.effective_at is not None
            and self.effective_at.astimezone(ZoneInfo("Asia/Kolkata")).date()
            != self.claim.valid_from
        ):
            raise ValueError("EFFECTIVE_DATE_TIMESTAMP_MISMATCH")
        if (
            self.removal_effective_at is not None
            and self.removal_effective_at.astimezone(ZoneInfo("Asia/Kolkata")).date()
            != self.claim.valid_to
        ):
            raise ValueError("EFFECTIVE_REMOVAL_MISMATCH")
        if self.effective_convention == "EXPLICIT_TIMESTAMP" and self.effective_at is None:
            raise ValueError("EXPLICIT_EFFECTIVE_TIME_REQUIRED")
        if (
            self.effective_at is not None
            and self.removal_effective_at is not None
            and self.effective_at >= self.removal_effective_at
        ):
            raise ValueError("EFFECTIVE_TIME_INTERVAL")


@dataclass(frozen=True)
class CoverageTransition:
    revision_id: str
    member_identity: str
    event_type: str
    effective_date: date
    effective_at: datetime | None = None


@dataclass(frozen=True)
class UniverseCoverage:
    coverage_id: str
    universe_id: str
    source_id: str
    artifact_identity: str
    methodology_version: str
    valid_from: date
    valid_to: date
    known_from: datetime | None
    known_to: datetime | None
    state: str
    expected_member_identities: tuple[str, ...]
    evidence: Evidence
    independent_reference_identity: str
    granularity: str = "SNAPSHOT"
    expected_count: int | None = None
    transitions: tuple[CoverageTransition, ...] = ()
    ending_member_identities: tuple[str, ...] = ()
    ending_reference: str | None = None
    snapshot_identity: str = "declared-reference"
    version: str = "od08.coverage/v1"
    temporal_precision: str = "DATE"
    snapshot_at: datetime | None = None

    def __post_init__(self) -> None:
        if any(
            type(v) is not tuple
            for v in (
                self.expected_member_identities,
                self.transitions,
                self.ending_member_identities,
            )
        ):
            raise ValueError("IMMUTABLE_COVERAGE_REQUIRED")
        intervals(self.valid_from, self.valid_to, self.known_from, self.known_to)
        if (
            self.state
            not in {
                "COMPLETE_VERIFIED",
                "COMPLETE_FOR_DECLARED_NON_MARKET_SCOPE",
                "PARTIAL",
                "PROVISIONAL",
                "UNKNOWN",
                "CONFLICTING",
                "SOURCE_BLOCKED",
            }
            or self.granularity not in {"SNAPSHOT", "COMPLETE_CHANGE_HISTORY"}
            or self.version != "od08.coverage/v1"
        ):
            raise ValueError("COVERAGE_CONTRACT")
        if len(set(self.expected_member_identities)) != len(self.expected_member_identities):
            raise ValueError("DUPLICATE_REFERENCE_IDENTITY")


@dataclass(frozen=True)
class AvailabilityPolicy:
    policy_version: str = "availability-v1"
    mode: str = "STRICT"
    bound: datetime | None = None
    evidence: Evidence | None = None
    semantics_reference: str | None = None


@dataclass(frozen=True)
class AvailabilityObservation:
    observation_id: str
    observation_type: str
    listing_id: str
    session_date: date
    economic_effective_time: datetime | None
    observed_at: datetime | None
    published_at: datetime | None
    known_from: datetime | None
    known_to: datetime | None
    ingested_at: datetime | None
    source_id: str
    artifact_identity: str
    evidence: Evidence
    interval_completed_at: datetime | None = None
    volume: Decimal | None = None
    turnover: Decimal | None = None
    currency: str | None = None
    price_unit: str | None = None
    price_basis: str | None = None
    volume_basis: str | None = None
    record_identity: str | None = None
    adjustment_binding: AdjustmentBinding | None = None
    price_value: Decimal | None = None
    adjustment: BoundResult | None = None
    adjustment_pin: PinnedCalculation | None = None
    version: str = "od08.availability/v1"

    def __post_init__(self) -> None:
        for v in (self.observation_id, self.listing_id, self.source_id, self.artifact_identity):
            text(v)
        intervals(self.session_date, None, self.known_from, self.known_to)
        for stamp in (
            self.economic_effective_time,
            self.observed_at,
            self.published_at,
            self.ingested_at,
            self.interval_completed_at,
        ):
            if stamp is not None:
                query_time(stamp)
        for number in (self.volume, self.turnover, self.price_value):
            if number is not None and (
                type(number) is not Decimal or not number.is_finite() or number < 0
            ):
                raise ValueError("OBSERVATION_NUMBER")


@dataclass(frozen=True)
class LiquidityPolicy:
    policy_version: str
    lookback_sessions: int
    minimum_completed_sessions: int
    minimum_average_volume: Decimal
    minimum_median_turnover: Decimal
    minimum_observation_coverage: Decimal
    currency: str
    price_unit: str
    price_basis: str
    volume_basis: str

    def __post_init__(self) -> None:
        for value in (
            self.minimum_average_volume,
            self.minimum_median_turnover,
            self.minimum_observation_coverage,
        ):
            from omegadata.adjustments.contracts import number

            number(value, zero=True)
        if (
            type(self.lookback_sessions) is not int
            or type(self.minimum_completed_sessions) is not int
        ):
            raise ValueError("LIQUIDITY_BUDGET")
        if not 1 <= self.minimum_completed_sessions <= self.lookback_sessions <= 366 or not Decimal(
            0
        ) <= self.minimum_observation_coverage <= Decimal(1):
            raise ValueError("LIQUIDITY_BUDGET")
        for v in (
            self.minimum_average_volume,
            self.minimum_median_turnover,
            self.minimum_observation_coverage,
        ):
            if type(v) is not Decimal or not v.is_finite() or v < 0:
                raise ValueError("LIQUIDITY_NUMBER")


@dataclass(frozen=True)
class ObservationScope:
    universe_id: str
    listings: tuple[str, ...]
    observation_types: tuple[str, ...]
    sessions: tuple[date, ...]
    source_scope: tuple[str, ...]
    price_basis: str
    volume_basis: str
    explicitly_excluded_ids: tuple[str, ...] = ()
    version: str = "od08.observation-scope/v2"

    def __post_init__(self) -> None:
        if self.version != "od08.observation-scope/v2" or any(
            type(v) is not tuple or len(v) > 10000
            for v in (
                self.listings,
                self.observation_types,
                self.sessions,
                self.source_scope,
                self.explicitly_excluded_ids,
            )
        ):
            raise ValueError("OBSERVATION_SCOPE_BUDGET")


@dataclass(frozen=True)
class EligibilityPolicy:
    policy_version: str
    view: str = "MEMBERSHIP"
    require_observations: bool = False
    liquidity_policy: LiquidityPolicy | None = None
    required_profile: str = "PRICE_RETURN"
    required_basis: str = "BACKWARD_ADJUSTED"
    require_adjustment: bool = False
    availability_policy: AvailabilityPolicy = AvailabilityPolicy()
    observation_contract_version: str = "v1"
    observation_scope: ObservationScope | None = None

    def __post_init__(self) -> None:
        text(self.policy_version)
        if self.view not in {"MEMBERSHIP", "RESEARCH", "LIQUIDITY", "EXECUTION"}:
            raise ValueError("CONSUMER_VIEW")


@dataclass(frozen=True)
class UniverseContext:
    source_snapshot_id: str
    definition: UniverseDefinition
    memberships: tuple[MembershipRevision, ...]
    coverage: tuple[UniverseCoverage, ...]
    identity: MemoryIdentityRepository
    calendar: VerifiedCalendar
    observations: tuple[AvailabilityObservation, ...] = ()
    authority: EvidenceAuthority | None = field(default=None, repr=False, compare=False)
    mode: Policy = "STRICT"
    calendar_version: str | None = None
    version: str = "od08.context/v1"

    def __post_init__(self) -> None:
        if (
            self.mode not in {"STRICT", "CANARY_ONLY"}
            or self.version != "od08.context/v1"
            or type(self.identity) is not MemoryIdentityRepository
            or type(self.calendar) is not VerifiedCalendar
        ):
            raise ValueError("CONTEXT_VERSION")
        for v in (self.memberships, self.coverage, self.observations):
            if type(v) is not tuple or len(v) > 10000:
                raise ValueError("IMMUTABLE_RESOURCE_BUDGET")


@dataclass(frozen=True)
class MemberDecision:
    revision_id: str
    security_id: str | None
    listing_id: str | None
    status: str
    reasons: tuple[str, ...]
    evidence_id: str
    identity_resolution_digest: str
    membership_state: str
    research_eligibility: str = "NOT_REQUESTED"
    liquidity_eligibility: str = "NOT_REQUESTED"
    tradability_state: str = "UNKNOWN"
    execution_eligibility: bool = False


@dataclass(frozen=True)
class UniverseSnapshot:
    universe_id: str
    definition_version: str
    valid_at: date | datetime
    known_at: datetime
    source_snapshot_id: str
    selected_revision_ids: tuple[str, ...]
    decisions: tuple[MemberDecision, ...]
    member_identities: tuple[str, ...]
    included_member_ids: tuple[str, ...]
    coverage_state: str
    reconciliation_json: str
    upstream_bindings: str
    decision_digest: str
    policy_version: str
    availability_policy_version: str
    liquidity_policy_version: str | None
    financial_accepted: bool = field(default=False, init=False)
    execution_accepted: bool = field(default=False, init=False)
    version: str = "od08.snapshot/v1"

    @property
    def accounted_count(self) -> int:
        return len(self.decisions)

    @property
    def canonical_json(self) -> str:
        return canonical(self)

    @property
    def snapshot_digest(self) -> str:
        return digest(self)

    @property
    def universe_snapshot_id(self) -> str:
        return self.snapshot_digest


@dataclass(frozen=True)
class RankingCandidate:
    member_identity: str
    metric: Decimal
    observation: AvailabilityObservation
