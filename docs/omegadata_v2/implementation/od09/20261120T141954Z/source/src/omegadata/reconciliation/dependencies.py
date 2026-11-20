"""Typed downstream replay evidence, independent from a completion status string."""

from dataclasses import dataclass
from datetime import datetime

from omegadata.adjustments.bound_chain import calculate_bound_chain
from omegadata.adjustments.bound_contracts import BoundResult, PinnedCalculation
from omegadata.universe.contracts import (
    AvailabilityObservation,
    EligibilityPolicy,
    UniverseContext,
    UniverseSnapshot,
)
from omegadata.universe.observation_binding import validate_binding
from omegadata.universe.snapshots import get_universe_as_of


@dataclass(frozen=True)
class UpstreamProof:
    kind: str
    old_output_id: str
    source_revision_digest: str
    source_observation: AvailabilityObservation
    payload: BoundResult | UniverseSnapshot
    context: PinnedCalculation | UniverseContext
    policy: EligibilityPolicy | None = None

    @property
    def output_identity(self) -> str:
        if isinstance(self.payload, BoundResult):
            return self.payload.output_digest
        return self.payload.universe_snapshot_id


def verify_upstream(proof: UpstreamProof, cutoff: datetime) -> bool:
    try:
        if (
            proof.kind == "ADJUSTMENT"
            and type(proof.payload) is BoundResult
            and type(proof.context) is PinnedCalculation
        ):
            o = proof.source_observation
            return bool(
                proof.context.context.known_at <= cutoff
                and o.adjustment == proof.payload
                and o.adjustment_pin == proof.context
                and validate_binding(o, o.adjustment_binding, cutoff).startswith("ELIGIBLE")
                and calculate_bound_chain(proof.context).canonical_json
                == proof.payload.canonical_json
            )
        if (
            proof.kind == "UNIVERSE"
            and type(proof.payload) is UniverseSnapshot
            and type(proof.context) is UniverseContext
            and type(proof.policy) is EligibilityPolicy
        ):
            x = proof.context
            snapshot = proof.payload
            return bool(
                snapshot.known_at <= cutoff
                and proof.policy.view != "MEMBERSHIP"
                and proof.source_observation in x.observations
                and get_universe_as_of(
                    x, snapshot.valid_at, snapshot.known_at, proof.policy, x.source_snapshot_id
                ).canonical_json
                == snapshot.canonical_json
            )
        return False
    except (ValueError, TypeError, ArithmeticError):
        return False
