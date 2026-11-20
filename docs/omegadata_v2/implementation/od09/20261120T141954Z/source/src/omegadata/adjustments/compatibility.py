"""Read-only opt-in legacy inspection, never implicit economic promotion."""

from dataclasses import dataclass
from typing import Any

from omegadata.adjustments.contracts import canonical


@dataclass(frozen=True)
class LegacyActionObservation:
    record_id: str
    action_type: str
    parameters: str
    known_from: None = None
    status: str = "BLOCKED_EVIDENCE"
    reason: str = "LEGACY_CONFIRMATION_NOT_AUTHENTIC_KNOWLEDGE_EVIDENCE"


def legacy_action(row: Any) -> LegacyActionObservation:
    return LegacyActionObservation(
        str(row.id), str(row.action_type), canonical(row.parameters or {})
    )
