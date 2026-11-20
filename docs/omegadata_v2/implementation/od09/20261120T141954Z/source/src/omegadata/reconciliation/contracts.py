"""Immutable reconciliation inputs. No caller label can grant financial authority."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from omegadata.adjustments.contracts import number
from omegadata.identity import intervals, query_time, text
from omegadata.universe.contracts import AvailabilityObservation, UniverseContext
from omegadata.universe.repository import pack

VERSION = "od09.reconciliation/v1"


def fingerprint(value: Any) -> str:
    return hashlib.sha256(pack(value).encode()).hexdigest()


@dataclass(frozen=True)
class Observation:
    availability: AvailabilityObservation
    security_id: str | None
    exchange: str
    symbol_as_reported: str
    series_as_reported: str
    publisher_identity: str | None
    parser_version: str
    schema_version: str
    source_row_ordinal: int
    field_name: str
    value: Decimal | None
    unit: str
    source_lineage_root: str | None
    observation_interval: str = "DAILY"
    imputed: bool = False
    universe_snapshot_id: str | None = None
    source_rights_decision: str | None = None
    version: str = VERSION

    def __post_init__(self) -> None:
        for v in (
            self.exchange,
            self.parser_version,
            self.schema_version,
            self.field_name,
            self.unit,
        ):
            text(v)
        if (
            type(self.source_row_ordinal) is not int
            or self.source_row_ordinal < 1
            or self.version != VERSION
        ):
            raise ValueError("OBSERVATION_CONTRACT")
        if self.value is not None:
            number(self.value, zero=True)

    @property
    def observation_id(self) -> str:
        return self.availability.observation_id

    @property
    def evidence(self) -> Any:
        return self.availability.evidence

    @property
    def source_id(self) -> str:
        return self.availability.source_id

    @property
    def source_artifact_identity(self) -> str:
        return self.availability.artifact_identity

    @property
    def source_record_identity(self) -> str | None:
        return self.availability.record_identity

    @property
    def listing_id(self) -> str:
        return self.availability.listing_id

    @property
    def session_date(self) -> date:
        return self.availability.session_date

    @property
    def observation_type(self) -> str:
        return self.availability.observation_type


@dataclass(frozen=True)
class TolerancePolicy:
    policy_id: str
    policy_version: str
    source_pair_scope: tuple[str, str]
    comparison_scope: str
    observation_type: str
    field_name: str
    venue_scope: tuple[str, ...]
    metric_definition: str
    warning_threshold: Decimal
    failure_threshold: Decimal
    currency: str
    unit: str
    known_from: datetime
    effective_from: date
    effective_to: date | None
    calibration_state: str
    known_to: datetime | None = None
    calibration_dataset_identity: str | None = None
    calibration_methodology: str | None = None
    calibration_knowledge_cutoff: datetime | None = None
    sample_size: int | None = None
    independent_review_reference: str | None = None
    boundary_convention: str = "PASS_LE_WARN_LT_FAIL_GE"
    liquidity_bucket: str | None = None
    tick_size: Decimal | None = None
    version: str = "od09.tolerance/v1"

    def __post_init__(self) -> None:
        text(self.policy_id)
        text(self.policy_version)
        intervals(self.effective_from, self.effective_to, self.known_from, self.known_to)
        for v in (self.warning_threshold, self.failure_threshold):
            number(v, zero=True)
        if self.tick_size is not None:
            number(self.tick_size)
        if (
            self.warning_threshold > self.failure_threshold
            or type(self.source_pair_scope) is not tuple
            or len(self.source_pair_scope) != 2
            or type(self.venue_scope) is not tuple
        ):
            raise ValueError("TOLERANCE_CONTRACT")
        if self.calibration_knowledge_cutoff is not None:
            query_time(self.calibration_knowledge_cutoff)
        if (
            self.calibration_state
            not in {
                "APPROVED_AUTHENTIC_CALIBRATION",
                "PROVISIONAL_UNCALIBRATED_POLICY",
                "NON_MARKET_MATH_CONTROL",
                "BLOCKED_CALIBRATION",
            }
            or self.version != "od09.tolerance/v1"
            or self.boundary_convention != "PASS_LE_WARN_LT_FAIL_GE"
        ):
            raise ValueError("TOLERANCE_VERSION")


@dataclass(frozen=True)
class ComparisonContext:
    context_id: str
    left: tuple[Observation, ...]
    right: tuple[Observation, ...]
    policy: TolerancePolicy
    universe: UniverseContext
    valid_at: date
    known_at: datetime
    identity_snapshot_digest: str | None = None
    calendar_snapshot_digest: str | None = None
    universe_snapshot_reference: str | None = None
    maximum_matches: int = 10000
    algorithm_version: str = VERSION

    def __post_init__(self) -> None:
        text(self.context_id)
        query_time(self.known_at)
        if (
            type(self.left) is not tuple
            or type(self.right) is not tuple
            or len(self.left) + len(self.right) > 10000
            or type(self.maximum_matches) is not int
            or not 1 <= self.maximum_matches <= 10000
            or self.algorithm_version != VERSION
        ):
            raise ValueError("COMPARISON_BUDGET_OR_VERSION")
        if len({o.observation_id for o in self.left + self.right}) != len(self.left + self.right):
            raise ValueError("DUPLICATE_OBSERVATION_ID")


@dataclass(frozen=True)
class MetricResult:
    metric: str
    status: str
    exact_ratio: tuple[int, int] | None
    decimal_value: Decimal | None
    arithmetic_version: str = "od09.fraction-decimal80/v1"


@dataclass(frozen=True)
class ReconciliationResult:
    reconciliation_id: str
    context_id: str
    left_observation_ids: tuple[str, ...]
    left_observation_digests: tuple[str, ...]
    right_observation_ids: tuple[str, ...]
    right_observation_digests: tuple[str, ...]
    comparable_field: str
    comparability: str
    metric: MetricResult | None
    policy_digest: str
    upstream_context_digest: str
    source_authority_digest: str
    valid_at: date
    known_at: datetime
    outcome: str
    reason_codes: tuple[str, ...]
    algorithm_version: str = VERSION
    financial_eligibility: bool = field(default=False, init=False)
    publication_eligibility: bool = field(default=False, init=False)
    execution_eligibility: bool = field(default=False, init=False)

    @property
    def result_digest(self) -> str:
        return fingerprint(self)


@dataclass(frozen=True)
class EligibilityDecision:
    numerical_confidence: Decimal
    reconciliation_status: str
    source_authority_status: str
    identity_status: str
    availability_status: str
    coverage_status: str
    review_status: str
    reprocess_status: str
    hard_block_reasons: tuple[str, ...]
    financial_eligibility: bool = field(default=False, init=False)
    publication_eligibility: bool = field(default=False, init=False)
    execution_eligibility: bool = field(default=False, init=False)
