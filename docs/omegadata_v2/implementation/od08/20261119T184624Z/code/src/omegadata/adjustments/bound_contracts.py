"""OD07 v2 bound observation/history/basis contracts. No source grants or I/O."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from omegadata.adjustments import contracts as c
from omegadata.adjustments.temporal import select_revisions
from omegadata.identity import Evidence, text

BOUND_VERSION = "od07.bound-calc/v2"


@dataclass(frozen=True)
class ReferenceObservation:
    original: c.Reference
    observation_id: str
    source_record_identity: str
    source_row_ordinal: int
    security_id: str
    listing_id: str
    exchange: str
    symbol_as_reported: str
    series_as_reported: str
    price_unit: str
    price_basis: str
    observation_type: str
    known_to: datetime | None = None
    observed_at: datetime | None = None
    published_at: datetime | None = None
    reference_version: str = "od07.reference/v2"

    @property
    def value(self) -> Decimal:
        return self.original.value

    @property
    def price_value(self) -> Decimal:
        return self.original.value

    @property
    def session_date(self) -> date:
        return self.original.session_date

    @property
    def known_from(self) -> datetime | None:
        return self.original.known_from

    @property
    def artifact_id(self) -> str:
        return self.original.artifact_id

    @property
    def source_artifact_identity(self) -> str:
        return self.original.artifact_id

    @property
    def currency(self) -> str:
        return self.original.currency

    @property
    def evidence(self) -> Evidence | None:
        return self.original.evidence

    @property
    def source_id(self) -> str | None:
        return self.original.source_id

    @property
    def source_evidence_id(self) -> str | None:
        return self.evidence.evidence_id if self.evidence else None


@dataclass(frozen=True)
class RawObservation:
    raw: c.Raw
    observation_id: str
    source_record_identity: str
    source_row_ordinal: int
    price_unit: str
    source_id: str
    version: str = "od07.raw-observation/v2"

    def __post_init__(self) -> None:
        for v in (
            self.observation_id,
            self.source_record_identity,
            self.price_unit,
            self.source_id,
        ):
            text(v)
        if (
            self.version != "od07.raw-observation/v2"
            or type(self.source_row_ordinal) is not int
            or self.source_row_ordinal < 1
        ):
            raise ValueError("RAW_OBSERVATION_IDENTITY")


@dataclass(frozen=True)
class ParameterSet:
    action_revision_id: str
    parameter_revision: str
    parameters_digest: str
    known_from: datetime | None
    known_to: datetime | None
    evidence: Evidence
    version: str = "od07.parameter-availability/v2"

    @classmethod
    def for_action(
        cls, action: c.Action, known_from: datetime | None, evidence: Evidence
    ) -> ParameterSet:
        # Explicit availability assertion, not authority or an inferred fallback.
        return cls(
            action.action_id,
            action.parameter_version,
            c.digest(action.parameters),
            known_from,
            None,
            evidence,
        )


@dataclass(frozen=True)
class HistorySnapshot:
    history_snapshot_id: str
    security_id: str
    listing_id: str | None
    source_scope: tuple[str, ...]
    valid_from: date
    valid_to: date
    known_at: datetime
    actions: tuple[c.Action, ...]
    action_revision_ids: tuple[str, ...]
    selected_revision_digest: str
    history_coverage_state: str
    coverage_reference: Evidence
    source_evidence_version: str
    effective_policy_version: str
    economic_event_ids: tuple[tuple[str, str], ...]
    snapshot_version: str = "od07.action-history/v2"

    @classmethod
    def create(
        cls,
        identity: str,
        security: str,
        listing: str | None,
        sources: tuple[str, ...],
        start: date,
        end: date,
        known: datetime,
        actions: tuple[c.Action, ...],
        state: str,
        evidence: Evidence,
        source_version: str,
        policy_version: str,
    ) -> HistorySnapshot:
        selected = select_revisions(actions, known)
        by_id = {a.action_id: a for a in actions}
        events = []
        for a in selected:
            root = a
            while root.supersedes_action_id is not None:
                root = by_id[root.supersedes_action_id]
            events.append((a.action_id, root.action_id))
        return cls(
            identity,
            security,
            listing,
            sources,
            start,
            end,
            known,
            actions,
            tuple(a.action_id for a in selected),
            c.digest(selected),
            state,
            evidence,
            source_version,
            policy_version,
            tuple(events),
        )


@dataclass(frozen=True)
class BasisPolicy:
    profile: str
    adjustment_basis: str
    basis_date: date
    version: str = "od07.basis-policy/v2"

    def __post_init__(self) -> None:
        if (
            self.version != "od07.basis-policy/v2"
            or self.profile not in {"RAW", "EXECUTION", "PRICE_RETURN", "TOTAL_RETURN", "VOLUME"}
            or self.adjustment_basis
            not in {
                "BACKWARD_ADJUSTED",
                "FORWARD_ADJUSTED",
                "INVERSE_FACTOR_COMPARISON",
                "RAW_UNADJUSTED",
                "TOTAL_RETURN_INDEX",
            }
            or type(self.basis_date) is not date
        ):
            raise ValueError("BASIS_POLICY")
        if self.profile in {"RAW", "EXECUTION"} and self.adjustment_basis != "RAW_UNADJUSTED":
            raise ValueError("RAW_EXECUTION_BASIS_REQUIRED")


@dataclass(frozen=True)
class ExecutionConstraints:
    security_id: str
    listing_id: str
    exchange: str
    session_date: date
    known_from: datetime | None
    evidence: Evidence
    lot_size: int | None = None
    quantity: str | None = None
    quantity_convention: str | None = None
    settlement_policy: str | None = None
    restrictions_status: str = "UNKNOWN"
    version: str = "od07.execution-constraints/v2"


@dataclass(frozen=True)
class PinnedCalculation:
    snapshot_id: str
    raw: RawObservation
    history: HistorySnapshot
    policy: BasisPolicy
    context: c.Context
    parameters: tuple[ParameterSet, ...]
    execution_constraints: ExecutionConstraints | None = None


@dataclass(frozen=True)
class BoundResult:
    calculation: c.Result
    context_bindings: str
    adjustment_basis: str
    basis_date: date
    identity_status: str = "UNKNOWN"
    calendar_status: str = "COVERAGE_UNKNOWN"
    tradability_status: str = "UNKNOWN"
    execution_status: str = "BLOCKED_UNKNOWN_CONSTRAINTS"
    verification_class: str = "NON_MARKET_STRUCTURAL_CONTROL"
    execution_eligibility: bool = field(default=False, init=False)
    publication_eligibility: bool = field(default=False, init=False)
    version: str = BOUND_VERSION

    @property
    def status(self) -> str:
        return self.calculation.status

    @property
    def mathematical_calculation_status(self) -> str:
        return self.calculation.status

    @property
    def adjusted_price(self) -> Decimal | None:
        return self.calculation.adjusted_price

    @property
    def raw_price_basis_preserved(self) -> bool:
        return self.calculation.original_price_basis == "RAW"

    @property
    def canonical_json(self) -> str:
        return c.canonical(self)

    @property
    def output_digest(self) -> str:
        return c.digest(self)
