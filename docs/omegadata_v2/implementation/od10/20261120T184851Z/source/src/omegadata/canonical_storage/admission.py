"""Typed upstream pins and independent source scope. Labels confer no authority."""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime
from typing import Any

from omegadata.adjustments.bound_contracts import BoundResult, PinnedCalculation
from omegadata.canonical_storage.contracts import StorageError, fingerprint, timestamp
from omegadata.reconciliation.contracts import ComparisonContext, Observation, ReconciliationResult
from omegadata.reconciliation.dependencies import UpstreamProof, verify_upstream
from omegadata.reconciliation.engine import reconcile_context
from omegadata.universe.contracts import UniverseSnapshot
from omegadata.universe.snapshots import get_universe_as_of


@dataclass(frozen=True)
class SourceBinding:
    source_id: str
    artifact: str
    record: str | None
    publisher: str | None
    symbol: str
    series: str
    lineage_root: str | None
    field_semantics: str
    record_digest: str

    @classmethod
    def from_observation(cls, o: Observation) -> SourceBinding:
        return cls(
            o.source_id,
            o.source_artifact_identity,
            o.source_record_identity,
            o.publisher_identity,
            o.symbol_as_reported,
            o.series_as_reported,
            o.source_lineage_root,
            o.field_name,
            fingerprint(o),
        )


@dataclass(frozen=True)
class AdmissionResult:
    input_digest: str
    result_digests: tuple[str, ...]
    coverage_state: str
    financial_eligible: bool = False
    authority_status: str = "UNVERIFIED"


class ProvenanceLedger:
    """Explicit immutable code-only pins, never a financial authority registry."""

    def __init__(self) -> None:
        self.records: dict[tuple[str, str, str], Any] = {}
        self.observations: dict[str, Observation] = {}

    def pin(
        self,
        domain: str,
        identity: str,
        payload: Any,
        known_from: datetime | None,
        *,
        context: Any = None,
    ) -> tuple[str, str, str]:
        from omegadata.canonical_storage.schema import DOMAINS

        timestamp(known_from)
        if domain not in DOMAINS or not is_dataclass(payload) or isinstance(payload, type):
            raise StorageError("UPSTREAM_TYPED_RECORD_REQUIRED")
        from omegadata import identity as i
        from omegadata import session_calendar as c
        from omegadata.adjustments.contracts import Action
        from omegadata.identity_adapters import MembershipClaim
        from omegadata.parsers.contracts import ParsedBar, ParseRequest, ParseResult
        from omegadata.reconciliation.anomalies import AnomalyRecord
        from omegadata.reconciliation.reviews import (
            CorrectionRevision,
            ReprocessCompletion,
            ReprocessRequest,
            ReviewRevision,
        )
        from omegadata.universe.contracts import MemberDecision, MembershipRevision

        allowed = {
            "source_observations": (ParseRequest, ParseResult, ParsedBar, Observation),
            "instrument_identity_revisions": (
                i.Issuer,
                i.Security,
                i.Listing,
                i.IdentifierClaim,
                i.MemoryIdentityRepository,
            ),
            "listing_lifecycle": (i.LifecycleEvent,),
            "session_calendar": (c.SessionClaim, c.CoverageClaim, c.VerifiedCalendar),
            "corporate_action_revisions": (Action,),
            "adjustment_results": (BoundResult,),
            "universe_membership_revisions": (MembershipClaim, MembershipRevision),
            "universe_snapshots": (UniverseSnapshot,),
            "universe_member_decisions": (MemberDecision,),
            "reconciliation_results": (ReconciliationResult,),
            "anomaly_records": (AnomalyRecord,),
            "review_revisions": (ReviewRevision,),
            "correction_revisions": (CorrectionRevision,),
            "reprocess_requests": (ReprocessRequest,),
            "reprocess_completions": (ReprocessCompletion,),
        }
        if type(payload) not in allowed.get(domain, ()):
            raise StorageError("UPSTREAM_TYPE_DOMAIN_MISMATCH")
        if domain == "universe_snapshots":
            if context is None or type(payload) is not UniverseSnapshot:
                raise StorageError("UNIVERSE_CONTEXT_REQUIRED")
            x, p = context
            if (
                get_universe_as_of(
                    x, payload.valid_at, payload.known_at, p, x.source_snapshot_id
                ).canonical_json
                != payload.canonical_json
            ):
                raise StorageError("UNIVERSE_REPLAY_MISMATCH")
        if domain == "adjustment_results":
            if known_from is None or type(payload) is not BoundResult:
                raise StorageError("ADJUSTMENT_CONTEXT_REQUIRED")
            verify_proof(context, known_from)
            if context.payload != payload:
                raise StorageError("ADJUSTMENT_CONTEXT_MISMATCH")
        ref = (domain, identity, fingerprint((payload, known_from)))
        for old in self.records:
            if old[:2] == ref[:2] and old != ref:
                raise StorageError("IMMUTABLE_UPSTREAM_ID")
        self.records[ref] = payload
        return ref

    def get(self, ref: tuple[str, str, str]) -> Any:
        try:
            return self.records[ref]
        except KeyError as error:
            raise StorageError("UPSTREAM_PIN_MISSING") from error

    def financial_eligible(self, ref: tuple[str, str, str]) -> bool:
        self.get(ref)
        return False

    def pin_observations(self, rows: tuple[Observation, ...]) -> None:
        for o in rows:
            if type(o) is not Observation:
                raise StorageError("OBSERVATION_CONTRACT")
            old = self.observations.get(o.observation_id)
            if old is not None and old != o:
                raise StorageError("IMMUTABLE_SOURCE_REVISION")
            self.observations[o.observation_id] = o

    def verify_source(self, o: Observation, binding: SourceBinding) -> None:
        if (
            SourceBinding.from_observation(o) != binding
            or self.observations.get(o.observation_id) != o
        ):
            raise StorageError("SOURCE_METADATA_OR_FIELD_SEMANTIC_MISMATCH")


def verify_proof(proof: UpstreamProof | None, cutoff: datetime) -> None:
    if type(proof) is not UpstreamProof or not verify_upstream(proof, cutoff):
        raise StorageError("BOUND_UPSTREAM_PROOF_REQUIRED")


def admit_comparison(
    context: ComparisonContext,
    results: tuple[ReconciliationResult, ...],
    ledger: ProvenanceLedger,
    required_ids: tuple[str, ...],
    complete: bool,
) -> AdmissionResult:
    if type(context) is not ComparisonContext or len(set(required_ids)) != len(required_ids):
        raise StorageError("COMPARISON_SCOPE_INVALID")
    supplied = context.left + context.right
    # Scope is independently declared against the persisted ledger, not result.inputs.
    eligible = set()
    for identity in required_ids:
        observation = ledger.observations.get(identity)
        known = observation.availability.known_from if observation is not None else None
        if known is not None and known <= context.known_at:
            eligible.add(identity)
    if any(identity not in ledger.observations for identity in required_ids):
        raise StorageError("REQUIRED_SOURCE_SCOPE_MISSING")
    ids = {o.observation_id for o in supplied}
    if complete and ids != eligible or not ids <= eligible:
        raise StorageError("INCOMPLETE_REQUIRED_COMPARISON_SCOPE")
    for o in supplied:
        ledger.verify_source(
            o, SourceBinding.from_observation(ledger.observations[o.observation_id])
        )
    expected = reconcile_context(context)
    if expected != results:
        raise StorageError("RECONCILIATION_REPLAY_MISMATCH")
    return AdmissionResult(
        fingerprint(context),
        tuple(v.result_digest for v in results),
        "COMPLETE_DECLARED_SCOPE" if complete else "PARTIAL",
    )


def admit_derived(row: Any, proof: UpstreamProof) -> None:
    if type(proof.context) is not PinnedCalculation or type(proof.payload) is not BoundResult:
        raise StorageError("DERIVED_ADJUSTMENT_PROOF_REQUIRED")
    cutoff = proof.context.context.known_at if proof.kind == "ADJUSTMENT" else None
    if cutoff is None:
        raise StorageError("DERIVED_ADJUSTMENT_PROOF_REQUIRED")
    verify_proof(proof, cutoff)
    a = proof.source_observation
    p = proof.context
    bound = proof.payload
    expected = (
        bound.calculation.adjusted_volume
        if row.field_semantics == "VOLUME"
        else bound.adjusted_price
    )
    raw = p.raw.raw
    if (
        row.observation_id,
        row.source_artifact_identity,
        row.source_record_identity,
        row.security_id,
        row.listing_id,
        row.exchange,
        row.session_date,
        row.currency,
        row.value,
    ) != (
        a.observation_id,
        a.artifact_identity,
        a.record_identity,
        raw.security_id,
        raw.listing_id,
        raw.exchange,
        a.session_date,
        a.currency,
        expected,
    ):
        raise StorageError("DERIVED_OBSERVATION_BINDING")
    if (
        (row.volume_basis if row.field_semantics == "VOLUME" else row.price_basis)
        != p.policy.adjustment_basis
        or row.known_from is None
        or row.known_from < cutoff
    ):
        raise StorageError("DERIVED_BASIS_OR_KNOWLEDGE")
    if not set(derived_lineage(proof)) <= set(row.lineage):
        raise StorageError("DERIVED_LINEAGE_REQUIRED")


def derived_lineage(proof: UpstreamProof) -> tuple[tuple[str, str, str], ...]:
    from omegadata.adjustments.contracts import digest

    if (
        type(proof) is not UpstreamProof
        or proof.kind != "ADJUSTMENT"
        or type(proof.context) is not PinnedCalculation
        or type(proof.payload) is not BoundResult
    ):
        raise StorageError("DERIVED_ADJUSTMENT_PROOF_REQUIRED")
    p = proof.context
    return (
        ("raw_observation", p.raw.observation_id, digest(p.raw)),
        ("adjustment_context", p.snapshot_id, digest(p)),
        ("adjustment_result", proof.payload.output_digest, proof.payload.output_digest),
        ("action_history", digest(p.history), digest(p.history)),
        ("parameter_availability", digest(p.parameters), digest(p.parameters)),
    )


@dataclass(frozen=True)
class ComparisonScope:
    scope_id: str
    source_ids: tuple[str, ...]
    listing_ids: tuple[str, ...]
    field_names: tuple[str, ...]
    session_from: Any
    session_to: Any
    known_from: datetime
    version: str = "od10.comparison-scope/v1"

    def __post_init__(self) -> None:
        from omegadata.canonical_storage.contracts import token

        token(self.scope_id)
        timestamp(self.known_from)
        if (
            self.known_from is None
            or self.session_to <= self.session_from
            or self.version != "od10.comparison-scope/v1"
        ):
            raise StorageError("COMPARISON_SCOPE_INVALID")
        for values in (self.source_ids, self.listing_ids, self.field_names):
            if (
                type(values) is not tuple
                or not 1 <= len(values) <= 1000
                or len(values) != len(set(values))
            ):
                raise StorageError("COMPARISON_SCOPE_RESOURCE_LIMIT")


def strict_comparison_admission(
    scope: ComparisonScope,
    context: ComparisonContext,
    results: tuple[ReconciliationResult, ...],
    ledger: ProvenanceLedger,
    *,
    complete: bool,
) -> AdmissionResult:
    if scope.known_from > context.known_at:
        raise StorageError("COMPARISON_SCOPE_FUTURE")
    selected = []
    for o in ledger.observations.values():
        a = o.availability
        if (
            o.source_id not in scope.source_ids
            or o.listing_id not in scope.listing_ids
            or o.field_name not in scope.field_names
            or not scope.session_from <= o.session_date < scope.session_to
        ):
            continue
        if a.known_from is None:
            raise StorageError("COMPARISON_AVAILABILITY_UNKNOWN")
        if a.known_from <= context.known_at and (
            a.known_to is None or context.known_at < a.known_to
        ):
            selected.append(o.observation_id)
    admitted = admit_comparison(context, results, ledger, tuple(sorted(selected)), complete)
    return AdmissionResult(
        admitted.input_digest,
        admitted.result_digests,
        "COMPLETE_REQUIRED_LEDGER_SET" if complete else "PARTIAL_REQUIRED_SET",
    )


def code_only_payload_admission(payload: Any, context: Any) -> None:
    """No source payload is copied on the strength of caller supplied rights labels.

    Only explicit non-market structural inputs or metadata-only parser receipts
    belong to this execution. Authentic payload admission requires a separately
    authorized source-purpose capability and is deliberately unavailable here.
    """
    from omegadata.identity import Evidence
    from omegadata.parsers.contracts import ParsedBar, ParseResult

    pending = [(payload, 0), (context, 0)]
    seen: set[int] = set()
    while pending:
        value, depth = pending.pop()
        if id(value) in seen:
            continue
        seen.add(id(value))
        if len(seen) > 25000 or depth > 32:
            raise StorageError("UPSTREAM_PAYLOAD_RESOURCE_LIMIT")
        if type(value) is Evidence and (
            value.permission == "DENIED" or value.classification != "NON_MARKET_CANARY"
        ):
            raise StorageError("SOURCE_PAYLOAD_AUTHORITY_REQUIRED")
        if type(value) is ParsedBar or (type(value) is ParseResult and value.rows):
            raise StorageError("SOURCE_PAYLOAD_AUTHORITY_REQUIRED")
        if is_dataclass(value) and not isinstance(value, type):
            pending.extend((getattr(value, f.name), depth + 1) for f in fields(value))
        elif isinstance(value, (tuple, list)):
            pending.extend((item, depth + 1) for item in value)
        elif isinstance(value, dict):
            pending.extend((item, depth + 1) for item in value.values())
