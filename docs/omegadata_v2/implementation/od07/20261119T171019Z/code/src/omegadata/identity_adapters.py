"""Opt-in OD06 adapters. Legacy source readers and economic consumers unchanged."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Generic, Literal, TypeVar

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from omegadata.db.models import InstrumentMaster, SymbolMap, UniverseMembership
from omegadata.identity import (
    Evidence,
    IdentityRepository,
    Policy,
    Resolution,
    intervals,
    legacy_exclusive_end,
    query_time,
    text,
)
from omegadata.parsers.contracts import ParsedBar, ParseResult

T = TypeVar("T")
FieldState = Literal["PRESENT", "ABSENT", "UNVERIFIED", "CONFLICTING", "FORBIDDEN"]


@dataclass(frozen=True)
class FinancialField(Generic[T]):
    state: FieldState
    value: T | None

    def __post_init__(self) -> None:
        if self.state not in {"PRESENT", "ABSENT", "UNVERIFIED", "CONFLICTING", "FORBIDDEN"}:
            raise ValueError("FIELD_STATE")
        if (
            self.state == "ABSENT"
            and self.value is not None
            or self.state == "PRESENT"
            and self.value is None
        ):
            raise ValueError("FIELD_VALUE_STATE")


@dataclass(frozen=True)
class IdentityIntake:
    parser_result: ParseResult
    original_row: ParsedBar | None
    known_from: FinancialField[datetime]
    effective_at: FinancialField[datetime]
    ingested_at: FinancialField[datetime]
    source_authentication_status: str = "UNVERIFIED"
    source_rights_status: str = "NOT_ESTABLISHED"
    financial_eligible: bool = field(default=False, init=False)
    version: str = "od06.intake/v1"

    @property
    def fields(self) -> tuple[tuple[str, FinancialField[object]], ...]:
        """Portable handoff fields, with epistemic status independent of value presence."""
        r, row = self.parser_result, self.original_row
        from omegadata.parsers.schema_catalog import supported_formats

        profile = next(
            (
                p
                for p in supported_formats()
                if p["source_id"] == r.source_key
                and p["format_id"] == r.format_id
                and p["parser_version"] == r.parser_version
            ),
            None,
        )
        values: dict[str, object | None] = {
            "source_id": r.source_key,
            "format_era": r.format_id,
            "parser_version": r.parser_version,
            "schema_version": profile["schema_version"] if profile else None,
            "exchange": row.exchange if row else None,
            "source_venue": profile["source_venue"] if profile else None,
            "trade_date": row.trade_date if row else None,
            "symbol_as_reported": row.symbol if row else None,
            "series": row.series if row else None,
            "isin_if_available": row.isin if row else None,
            "instrument_attributes": None,
            "source_artifact_identity": r.raw_sha256,
            "source_row_ordinal": row.source_row_index if row else None,
            "original_lexemes": row.price_lexemes if row else None,
            "data_quality_status": r.state,
            "reference_classification": r.reference_classification,
            "source_authentication_status": "UNVERIFIED",
            "source_rights_status": None,
            "known_from": None,
            "effective_at": None,
            "ingested_at": None,
        }
        code_metadata = {
            "parser_version",
            "schema_version",
            "source_artifact_identity",
            "data_quality_status",
            "reference_classification",
            "source_row_ordinal",
        }
        return tuple(
            (
                name,
                FinancialField(
                    "FORBIDDEN"
                    if name == "source_rights_status"
                    else "ABSENT"
                    if value is None
                    else "PRESENT"
                    if name in code_metadata
                    else "UNVERIFIED",
                    value,
                ),
            )
            for name, value in sorted(values.items())
        )


def intake(result: ParseResult, row: ParsedBar | None) -> IdentityIntake:
    """Retain upstream objects verbatim. Never infer availability from trade date."""
    if result.state != "PARSED_UNVERIFIED" or row is not None and row not in result.rows:
        raise ValueError("PARSER_INPUT_QUARANTINED_OR_ROW_NOT_IN_RESULT")
    return IdentityIntake(
        result,
        row,
        FinancialField("ABSENT", None),
        FinancialField("ABSENT", None),
        FinancialField("ABSENT", None),
    )


@dataclass(frozen=True)
class MembershipClaim:
    membership_id: str
    index_name: str
    symbol: str
    series: str
    exchange: str
    valid_from: date
    valid_to: date | None
    known_from: datetime | None
    known_to: datetime | None
    evidence: Evidence
    status: str = "SOURCE_BACKED_UNVERIFIED"
    supersedes_membership_id: str | None = None

    def __post_init__(self) -> None:
        for value in (self.membership_id, self.index_name, self.symbol, self.series, self.exchange):
            text(value)
        intervals(self.valid_from, self.valid_to, self.known_from, self.known_to)
        if self.status not in {
            "OFFICIAL_VERIFIED",
            "SOURCE_BACKED_UNVERIFIED",
            "RECONSTRUCTED_PROVISIONAL",
            "CONFLICTING",
            "UNKNOWN",
        }:
            raise ValueError("MEMBERSHIP_STATUS")


@dataclass(frozen=True)
class StrictUniverse:
    resolved_entries: tuple[tuple[MembershipClaim, Resolution], ...]
    unresolved_memberships: tuple[MembershipClaim, ...]
    ambiguous_identifiers: tuple[MembershipClaim, ...]
    source_blocked_entries: tuple[MembershipClaim, ...]
    selected_count: int
    coverage_status: str
    financial_eligible: bool = field(default=False, init=False)
    authoritative_coverage: bool = field(default=False, init=False)

    @property
    def accounted_count(self) -> int:
        return sum(
            map(
                len,
                (
                    self.resolved_entries,
                    self.unresolved_memberships,
                    self.ambiguous_identifiers,
                    self.source_blocked_entries,
                ),
            )
        )


def membership_revision_ends(claims: tuple[MembershipClaim, ...]) -> dict[str, datetime]:
    if len({c.membership_id for c in claims}) != len(claims):
        raise ValueError("DUPLICATE_MEMBERSHIP")
    by_id = {c.membership_id: c for c in claims}
    ends: dict[str, datetime] = {}
    for claim in claims:
        if claim.supersedes_membership_id is not None:
            old = by_id.get(claim.supersedes_membership_id)
            if (
                old is None
                or old.membership_id in ends
                or old.known_from is None
                or claim.known_from is None
                or claim.known_from <= old.known_from
                or (old.index_name, old.exchange, old.valid_from, old.valid_to)
                != (claim.index_name, claim.exchange, claim.valid_from, claim.valid_to)
            ):
                raise ValueError("INVALID_MEMBERSHIP_SUPERSESSION")
            ends[old.membership_id] = claim.known_from
    return ends


def strict_universe(
    claims: tuple[MembershipClaim, ...],
    repository: IdentityRepository,
    index_name: str,
    valid_at: date,
    known_at: datetime,
    evidence_policy: Policy = "STRICT",
) -> StrictUniverse:
    query_time(known_at)
    if evidence_policy not in {"STRICT", "CANARY_ONLY"}:
        raise ValueError("EVIDENCE_POLICY")
    if len({c.membership_id for c in claims}) != len(claims):
        raise ValueError("DUPLICATE_MEMBERSHIP")
    ends = membership_revision_ends(claims)
    selected = tuple(
        sorted(
            (
                c
                for c in claims
                if c.index_name == index_name
                and c.valid_from <= valid_at
                and (c.valid_to is None or valid_at < c.valid_to)
                and (c.known_from is None or c.known_from <= known_at)
                and (c.known_to is None or known_at < c.known_to)
                and (c.membership_id not in ends or known_at < ends[c.membership_id])
            ),
            key=lambda c: c.membership_id,
        )
    )
    resolved, unresolved, ambiguous, blocked = [], [], [], []
    for claim in selected:
        if claim.evidence.permission != "PERMITTED":
            blocked.append(claim)
            continue
        if (
            claim.known_from is None
            or claim.status != "OFFICIAL_VERIFIED"
            or not claim.evidence.eligible(evidence_policy)
        ):
            unresolved.append(claim)
            continue
        result = repository.resolve_listing(
            claim.exchange, claim.symbol, claim.series, valid_at, known_at, evidence_policy
        )
        if result.state == "RESOLVED":
            resolved.append((claim, result))
        elif result.state in {"AMBIGUOUS", "CONFLICTING"}:
            ambiguous.append(claim)
        elif result.state == "SOURCE_BLOCKED":
            blocked.append(claim)
        else:
            unresolved.append(claim)
    complete = not (unresolved or ambiguous or blocked)
    return StrictUniverse(
        tuple(resolved),
        tuple(unresolved),
        tuple(ambiguous),
        tuple(blocked),
        len(selected),
        "COMPLETE" if complete else "INCOMPLETE",
    )


@dataclass(frozen=True)
class LegacyMembershipObservation:
    membership_id: int
    isin_as_reported: str
    master_present: bool
    status: str
    reason: str
    known_from: None = None
    authoritative: bool = False


def legacy_universe_inventory(
    session: Session, index_name: str, valid_at: date
) -> tuple[LegacyMembershipObservation, ...]:
    """Read-only opt-in companion to get_universe; accounts for missing masters.

    Legacy added_date/updated_at are NOT evidence of knowledge. No current active
    or delisting filter is applied. All existing rows remain unverified here.
    """
    rows = session.scalars(
        select(UniverseMembership)
        .where(
            UniverseMembership.index_name == index_name,
            UniverseMembership.effective_date <= valid_at,
            or_(
                UniverseMembership.removal_effective.is_(None),
                UniverseMembership.removal_effective > valid_at,
            ),
        )
        .order_by(UniverseMembership.id)
    ).all()
    return tuple(
        LegacyMembershipObservation(
            row.id,
            row.isin,
            session.get(InstrumentMaster, row.isin) is not None,
            "RECONSTRUCTED_PROVISIONAL"
            if row.source == "RECONSTRUCTED"
            else "SOURCE_BACKED_UNVERIFIED",
            "KNOWLEDGE_AND_IDENTITY_EVIDENCE_NOT_ESTABLISHED",
        )
        for row in rows
    )


def source_backfill(raw_root: Path) -> None:
    """Refuse before any source-directory enumeration or open."""
    raise PermissionError("SOURCE_DEPENDENT_BACKFILL_BLOCKED")


def engineering_gate(results: Mapping[str, int | None]) -> str:
    """Consume a COMPLETE externally enumerated engineering command set only.

    Financial, incident, platform and production gates are evaluated separately.
    """
    if any(code is not None and code != 0 for code in results.values()):
        return "FAIL"
    required = {"focused", "adoption", "A", "ruff", "mypy", "pip", "compile", "containment"}
    if set(results) != required or any(code is None for code in results.values()):
        return "BLOCKED"
    return "PASS"


@dataclass(frozen=True)
class LegacySymbolObservation:
    mapping_id: int
    isin_as_reported: str
    exchange: str
    symbol_as_reported: str
    valid_from: date
    valid_to_exclusive: date | None
    known_from: None = None
    authoritative: bool = False
    reason: str = "LEGACY_KNOWLEDGE_AND_SERIES_UNKNOWN"


def legacy_symbol_inventory(
    session: Session, exchange: str, symbol: str, valid_at: date
) -> tuple[LegacySymbolObservation, ...]:
    """All matches, inclusive legacy end converted explicitly; no first-row choice.

    No issuer/security/listing is fabricated from ISIN. Caller must supply typed,
    evidence-reviewed claims to the new repository; this view is not such a claim.
    """
    rows = session.scalars(
        select(SymbolMap)
        .where(
            SymbolMap.exchange == exchange,
            SymbolMap.symbol == symbol,
            SymbolMap.valid_from <= valid_at,
            or_(SymbolMap.valid_to.is_(None), SymbolMap.valid_to >= valid_at),
        )
        .order_by(SymbolMap.id)
    ).all()
    return tuple(
        LegacySymbolObservation(
            row.id,
            row.isin,
            str(row.exchange),
            row.symbol,
            row.valid_from,
            legacy_exclusive_end(row.valid_to),
        )
        for row in rows
    )
