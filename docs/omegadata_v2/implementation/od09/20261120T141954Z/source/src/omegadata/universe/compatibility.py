"""OD08 read-only integration with the existing strict/legacy inventory contracts."""

from datetime import date

from sqlalchemy.orm import Session

from omegadata.identity_adapters import (
    LegacyMembershipObservation,
    legacy_universe_inventory,
    source_backfill,
)
from omegadata.universe.contracts import UniverseContext
from omegadata.universe.temporal import get_membership_history


def legacy_inventory(
    session: Session, universe_id: str, valid_at: date
) -> tuple[LegacyMembershipObservation, ...]:
    return legacy_universe_inventory(session, universe_id, valid_at)


def source_dependent_backfill() -> None:
    from pathlib import Path

    source_backfill(Path("UNUSED_NO_SOURCE_TRAVERSAL"))


def membership_history(context: UniverseContext, event_id: str) -> tuple[str, ...]:
    return tuple(r.revision_id for r in get_membership_history(context, event_id))
