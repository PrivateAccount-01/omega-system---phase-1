"""OD06 opt-in identity ledger v1. No I/O, ORM migration or source promotion.

All intervals are half-open. IDs use immutable record-system keys, never tickers.
Evidence is supplied by a separately authorized reviewer; this module does not
establish authenticity. CANARY_ONLY is explicitly nonfinancial software testing.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta
from typing import Literal, Protocol
from uuid import NAMESPACE_URL, uuid5

from omegadata.identity_authority import EvidenceAuthority

Policy = Literal["STRICT", "CANARY_ONLY"]
ResolutionState = Literal[
    "RESOLVED", "UNKNOWN", "AMBIGUOUS", "CONFLICTING", "QUARANTINED", "SOURCE_BLOCKED"
]


def text(value: str) -> None:
    if not isinstance(value, str) or not value or value != value.strip() or len(value) > 512:
        raise ValueError("INVALID_IDENTIFIER")
    if any(ord(c) < 32 for c in value):
        raise ValueError("INVALID_IDENTIFIER")


def aware(value: datetime | None) -> None:
    if value is not None and (
        not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None
    ):
        raise ValueError("TIMEZONE_REQUIRED")


def query_time(value: datetime) -> None:
    if not isinstance(value, datetime):
        raise ValueError("KNOWLEDGE_TIME_REQUIRED")
    aware(value)


def intervals(
    valid_from: date, valid_to: date | None, known_from: datetime | None, known_to: datetime | None
) -> None:
    if type(valid_from) is not date or (valid_to is not None and type(valid_to) is not date):
        raise ValueError("DATE_REQUIRED")
    if valid_to is not None and valid_to <= valid_from:
        raise ValueError("INVALID_VALID_INTERVAL")
    aware(known_from)
    aware(known_to)
    if known_to is not None and (known_from is None or known_to <= known_from):
        raise ValueError("INVALID_KNOWLEDGE_INTERVAL")


def record_id(kind: str, immutable_record_key: str) -> str:
    """Caller must persist the immutable ledger key; it is not an official ID."""
    if kind not in {"issuer", "security", "listing", "claim", "event", "evidence"}:
        raise ValueError("ID_KIND")
    text(immutable_record_key)
    return (
        kind
        + "-"
        + str(uuid5(NAMESPACE_URL, "omegadata.identity/v1/" + kind + "/" + immutable_record_key))
    )


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    classification: str
    authentication: str
    permission: str
    review_reference: str | None = None

    def __post_init__(self) -> None:
        text(self.evidence_id)
        if self.classification not in {"NON_MARKET_CANARY", "SOURCE_DOCUMENT", "UNVERIFIED"}:
            raise ValueError("EVIDENCE_CLASS")
        if self.authentication not in {"VERIFIED", "UNVERIFIED", "CONFLICTING"}:
            raise ValueError("EVIDENCE_AUTHENTICATION")
        if self.permission not in {"PERMITTED", "PENDING", "DENIED"}:
            raise ValueError("EVIDENCE_PERMISSION")
        if self.review_reference is not None:
            text(self.review_reference)

    def eligible(self, policy: Policy) -> bool:
        if policy not in {"STRICT", "CANARY_ONLY"}:
            raise ValueError("EVIDENCE_POLICY")
        if (
            self.permission != "PERMITTED"
            or not self.review_reference
            or self.authentication == "CONFLICTING"
        ):
            return False
        if policy == "CANARY_ONLY":
            return self.classification == "NON_MARKET_CANARY"
        return False  # Plain labels cannot establish trusted financial evidence.


@dataclass(frozen=True)
class Issuer:
    issuer_id: str

    def __post_init__(self) -> None:
        text(self.issuer_id)


@dataclass(frozen=True)
class Security:
    security_id: str
    issuer_id: str | None

    def __post_init__(self) -> None:
        text(self.security_id)
        if self.issuer_id is not None:
            text(self.issuer_id)


@dataclass(frozen=True)
class Listing:
    listing_id: str
    security_id: str | None
    exchange: str

    def __post_init__(self) -> None:
        text(self.listing_id)
        text(self.exchange)
        if self.security_id is not None:
            text(self.security_id)


@dataclass(frozen=True)
class IdentifierClaim:
    claim_id: str
    listing_id: str
    exchange: str
    symbol: str
    series: str
    valid_from: date
    valid_to: date | None
    known_from: datetime | None
    known_to: datetime | None
    evidence: Evidence
    isin: str | None = None
    supersedes_claim_id: str | None = None
    lifecycle: str = "LISTED"
    version: str = "od06.identity/v1"

    def __post_init__(self) -> None:
        for value in (self.claim_id, self.listing_id, self.exchange, self.symbol, self.series):
            text(value)
        intervals(self.valid_from, self.valid_to, self.known_from, self.known_to)
        if self.version != "od06.identity/v1" or self.lifecycle not in {
            "LISTED",
            "SUSPENDED",
            "DELISTED",
        }:
            raise ValueError("CLAIM_CONTRACT")
        if self.isin is not None:
            from omegadata.track_b.isin_master import ISINMasterService

            if not ISINMasterService.validate_isin(self.isin):
                raise ValueError("INVALID_ISIN_SYNTAX_NOT_IDENTITY_PROOF")


def revision_ends(records: tuple[IdentifierClaim, ...]) -> dict[str, datetime]:
    """Append-only supersession derives an upper knowledge bound, preserving bytes."""
    by_id = {r.claim_id: r for r in records}
    if len(by_id) != len(records):
        raise ValueError("DUPLICATE_CLAIM_ID")
    ends: dict[str, datetime] = {}
    for r in records:
        if r.supersedes_claim_id is None:
            continue
        old = by_id.get(r.supersedes_claim_id)
        if (
            old is None
            or old.claim_id in ends
            or old.known_from is None
            or r.known_from is None
            or r.known_from <= old.known_from
            or old.listing_id != r.listing_id
            or old.exchange != r.exchange
            or old.valid_from != r.valid_from
            or old.valid_to != r.valid_to
            or (old.known_to is not None and old.known_to < r.known_from)
        ):
            raise ValueError("INVALID_SUPERSESSION")
        ends[old.claim_id] = r.known_from
    return ends


@dataclass(frozen=True)
class Resolution:
    state: ResolutionState
    claim_ids: tuple[str, ...] = ()
    listing_id: str | None = None
    security_id: str | None = None
    issuer_id: str | None = None
    lifecycle: str | None = None
    financial_eligible: bool = field(default=False, init=False)
    reason: str | None = None
    version: str = "od06.resolution/v1"


class IdentityRepository(Protocol):
    def resolve_listing(
        self,
        exchange: str,
        symbol: str,
        series: str,
        valid_at: date,
        known_at: datetime,
        evidence_policy: Policy = "STRICT",
    ) -> Resolution: ...


@dataclass(frozen=True)
class MemoryIdentityRepository:
    issuers: tuple[Issuer, ...] = ()
    securities: tuple[Security, ...] = ()
    listings: tuple[Listing, ...] = ()
    claims: tuple[IdentifierClaim, ...] = ()
    authority: EvidenceAuthority | None = field(default=None, compare=False, repr=False)

    def __post_init__(self) -> None:
        if any(
            type(values) is not tuple
            for values in (self.issuers, self.securities, self.listings, self.claims)
        ):
            raise ValueError("IMMUTABLE_LEDGER_REQUIRED")
        if self.authority is not None and type(self.authority) is not EvidenceAuthority:
            raise ValueError("TRUSTED_AUTHORITY_TYPE")
        ii = {r.issuer_id for r in self.issuers}
        ss = {r.security_id for r in self.securities}
        ll = {r.listing_id for r in self.listings}
        if (
            len(ii) != len(self.issuers)
            or len(ss) != len(self.securities)
            or len(ll) != len(self.listings)
        ):
            raise ValueError("DUPLICATE_ID")
        if ii & ss or ii & ll or ss & ll:
            raise ValueError("IDENTITY_KIND_COLLISION")
        if any(r.issuer_id is not None and r.issuer_id not in ii for r in self.securities):
            raise ValueError("ISSUER_MISSING")
        if any(r.security_id is not None and r.security_id not in ss for r in self.listings):
            raise ValueError("SECURITY_MISSING")
        listing_map = {r.listing_id: r for r in self.listings}
        if any(
            r.listing_id not in ll or listing_map[r.listing_id].exchange != r.exchange
            for r in self.claims
        ):
            raise ValueError("LISTING_MISSING_OR_WRONG_EXCHANGE")
        revision_ends(self.claims)

    def append_correction(self, claim: IdentifierClaim) -> MemoryIdentityRepository:
        if claim.supersedes_claim_id is None:
            raise ValueError("SUPERSESSION_REQUIRED")
        return replace(self, claims=(*self.claims, claim))

    def resolve_listing(
        self,
        exchange: str,
        symbol: str,
        series: str,
        valid_at: date,
        known_at: datetime,
        evidence_policy: Policy = "STRICT",
    ) -> Resolution:
        query_time(known_at)
        for value in (exchange, symbol, series):
            text(value)
        if evidence_policy not in {"STRICT", "CANARY_ONLY"}:
            raise ValueError("EVIDENCE_POLICY")
        if type(valid_at) is not date:
            raise ValueError("DATE_REQUIRED")
        ends = revision_ends(self.claims)
        candidates = tuple(
            sorted(
                (
                    c
                    for c in self.claims
                    if c.exchange == exchange
                    and c.symbol == symbol
                    and c.series == series
                    and c.valid_from <= valid_at
                    and (c.valid_to is None or valid_at < c.valid_to)
                    and (c.known_from is None or c.known_from <= known_at)
                    and (c.known_to is None or known_at < c.known_to)
                    and (c.claim_id not in ends or known_at < ends[c.claim_id])
                ),
                key=lambda c: c.claim_id,
            )
        )
        ids = tuple(c.claim_id for c in candidates)
        if not candidates:
            return Resolution("UNKNOWN")
        if any(c.evidence.permission != "PERMITTED" for c in candidates):
            return Resolution("SOURCE_BLOCKED", ids)
        if any(
            c.known_from is None
            or not (
                c.evidence.eligible(evidence_policy)
                if evidence_policy == "CANARY_ONLY"
                else self.authority is not None and self.authority.check_claim(c, known_at).allowed
            )
            for c in candidates
        ):
            return Resolution("QUARANTINED", ids, reason="KNOWLEDGE_OR_EVIDENCE_UNVERIFIED")
        if len({(c.listing_id, c.isin, c.lifecycle) for c in candidates}) > 1:
            return Resolution("CONFLICTING", ids)
        if len(candidates) > 1:
            return Resolution("AMBIGUOUS", ids)
        c = candidates[0]
        listing = next(r for r in self.listings if r.listing_id == c.listing_id)
        security = next((r for r in self.securities if r.security_id == listing.security_id), None)
        if security is None or security.issuer_id is None:
            return Resolution("QUARANTINED", ids, reason="IDENTITY_LINK_UNRESOLVED")
        result = Resolution(
            "RESOLVED",
            ids,
            listing.listing_id,
            security.security_id,
            security.issuer_id,
            c.lifecycle,
        )
        object.__setattr__(result, "financial_eligible", evidence_policy == "STRICT")
        return result


EVENT_TYPES = frozenset(
    {
        "LISTING",
        "DELISTING",
        "SYMBOL_CHANGE",
        "SERIES_CHANGE",
        "SUSPENSION",
        "RELISTING",
        "CROSS_LISTING",
        "SECURITY_RECLASSIFICATION",
        "ISSUER_CHANGE",
        "MERGER_IDENTITY_TRANSITION",
        "DEMERGER_IDENTITY_TRANSITION",
        "IDENTIFIER_CORRECTION",
        "SOURCE_SUPERSESSION",
    }
)


@dataclass(frozen=True)
class LifecycleEvent:
    event_id: str
    event_type: str
    affected_identity_ids: tuple[str, ...]
    evidence: Evidence
    published_at: datetime | None = None
    effective_at: datetime | None = None
    known_from: datetime | None = None
    ingested_at: datetime | None = None
    supersedes_event_id: str | None = None
    validation_status: str = "UNVERIFIED"
    continuity_review_reference: str | None = None
    version: str = "od06.lifecycle/v1"

    def __post_init__(self) -> None:
        if type(self.affected_identity_ids) is not tuple:
            raise ValueError("IMMUTABLE_EVENT_IDENTITIES")
        text(self.event_id)
        if self.event_type not in EVENT_TYPES or not self.affected_identity_ids:
            raise ValueError("EVENT_TYPE_OR_IDENTITIES")
        for identity in self.affected_identity_ids:
            text(identity)
        if len(set(self.affected_identity_ids)) != len(self.affected_identity_ids):
            raise ValueError("DUPLICATE_AFFECTED_ID")
        for timestamp in (self.published_at, self.effective_at, self.known_from, self.ingested_at):
            aware(timestamp)
        if self.validation_status not in {"UNVERIFIED", "REVIEWED", "CONFLICTING", "QUARANTINED"}:
            raise ValueError("EVENT_VALIDATION_STATUS")
        if self.version != "od06.lifecycle/v1":
            raise ValueError("EVENT_VERSION")

    @property
    def source_reference(self) -> str:
        return self.evidence.evidence_id

    @property
    def source_authentication_state(self) -> str:
        return self.evidence.authentication


def validate_events(events: tuple[LifecycleEvent, ...]) -> tuple[LifecycleEvent, ...]:
    by_id = {e.event_id: e for e in events}
    if len(by_id) != len(events):
        raise ValueError("DUPLICATE_EVENT")
    superseded: set[str] = set()
    for event in events:
        if event.event_type in {"MERGER_IDENTITY_TRANSITION", "DEMERGER_IDENTITY_TRANSITION"} and (
            not event.continuity_review_reference or len(event.affected_identity_ids) < 2
        ):
            raise ValueError("CONTINUITY_REVIEW_REQUIRED")
        if event.supersedes_event_id:
            old = by_id.get(event.supersedes_event_id)
            if (
                old is None
                or old.event_id in superseded
                or old.known_from is None
                or event.known_from is None
                or event.known_from <= old.known_from
                or not set(old.affected_identity_ids) & set(event.affected_identity_ids)
            ):
                raise ValueError("EVENT_SUPERSESSION")
            superseded.add(old.event_id)
    lifecycle = {"LISTING", "DELISTING", "SUSPENSION", "RELISTING"}
    for i, left in enumerate(events):
        for right in events[i + 1 :]:
            if (
                left.effective_at is not None
                and left.effective_at == right.effective_at
                and set(left.affected_identity_ids) & set(right.affected_identity_ids)
                and left.event_type in lifecycle
                and right.event_type in lifecycle
                and left.event_type != right.event_type
                and left.supersedes_event_id != right.event_id
                and right.supersedes_event_id != left.event_id
            ):
                raise ValueError("CONTRADICTORY_LIFECYCLE_EVENTS")
    return tuple(sorted(events, key=lambda e: e.event_id))


def legacy_exclusive_end(inclusive_end: date | None) -> date | None:
    """Explicit conversion; date.max cannot be represented and must be reviewed."""
    return None if inclusive_end is None else inclusive_end + timedelta(days=1)
