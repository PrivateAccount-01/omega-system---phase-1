"""OD06 explicit, bitemporal session authority adapter; legacy calendar retained.
No weekdays, hours, holidays or market sessions are generated as source facts.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta

from omegadata.identity import Evidence, Policy, aware, intervals, query_time, text
from omegadata.identity_authority import EvidenceAuthority
from omegadata.track_a.trading_calendar import TradingCalendar


@dataclass(frozen=True)
class SessionClaim:
    claim_id: str
    exchange: str
    session_date: date
    session_type: str
    timezone: str
    calendar_version: str
    evidence: Evidence
    known_from: datetime | None
    known_to: datetime | None
    opens_at: datetime | None = None
    closes_at: datetime | None = None
    supersedes_claim_id: str | None = None
    version: str = "od06.session/v1"

    def __post_init__(self) -> None:
        for value in (self.claim_id, self.exchange, self.calendar_version):
            text(value)
        if self.timezone != "Asia/Kolkata" or self.version != "od06.session/v1":
            raise ValueError("SESSION_VERSION_OR_TIMEZONE")
        if self.session_type not in {"REGULAR", "SPECIAL", "CLOSED"}:
            raise ValueError("SESSION_TYPE")
        intervals(self.session_date, None, self.known_from, self.known_to)
        for moment in (self.opens_at, self.closes_at):
            aware(moment)
            if moment is not None:
                from zoneinfo import ZoneInfo

                if moment.astimezone(ZoneInfo(self.timezone)).date() != self.session_date:
                    raise ValueError("SESSION_LOCAL_DATE")
        if self.session_type == "CLOSED" and (
            self.opens_at is not None or self.closes_at is not None
        ):
            raise ValueError("CLOSED_SESSION_HOURS")
        if (
            self.opens_at is not None
            and self.closes_at is not None
            and self.closes_at <= self.opens_at
        ):
            raise ValueError("SESSION_HOURS")

    @property
    def authority_reference(self) -> str:
        return self.evidence.evidence_id


def revision_ends(claims: tuple[SessionClaim, ...]) -> dict[str, datetime]:
    by_id = {c.claim_id: c for c in claims}
    if len(by_id) != len(claims):
        raise ValueError("DUPLICATE_SESSION_CLAIM")
    ends: dict[str, datetime] = {}
    for c in claims:
        if c.supersedes_claim_id is None:
            continue
        old = by_id.get(c.supersedes_claim_id)
        if (
            old is None
            or old.claim_id in ends
            or c.known_from is None
            or old.known_from is None
            or c.known_from <= old.known_from
            or old.exchange != c.exchange
            or old.session_date != c.session_date
            or old.known_to is not None
            and old.known_to < c.known_from
        ):
            raise ValueError("SESSION_SUPERSESSION")
        ends[old.claim_id] = c.known_from
    return ends


@dataclass(frozen=True)
class SessionResolution:
    status: str
    claims: tuple[SessionClaim, ...] = ()
    financial_eligible: bool = field(default=False, init=False)


@dataclass(frozen=True)
class CoverageClaim:
    coverage_id: str
    exchange: str
    valid_from: date
    valid_to: date
    known_from: datetime | None
    known_to: datetime | None
    evidence: Evidence
    calendar_version: str
    status: str

    def __post_init__(self) -> None:
        for value in (self.coverage_id, self.exchange, self.calendar_version):
            text(value)
        intervals(self.valid_from, self.valid_to, self.known_from, self.known_to)
        if self.status not in {"COMPLETE", "INCOMPLETE", "UNKNOWN"}:
            raise ValueError("COVERAGE_STATUS")


@dataclass(frozen=True)
class VerifiedCalendar:
    claims: tuple[SessionClaim, ...] = ()
    coverage: tuple[CoverageClaim, ...] = ()
    authority: EvidenceAuthority | None = field(default=None, compare=False, repr=False)

    def __post_init__(self) -> None:
        if type(self.claims) is not tuple:
            raise ValueError("IMMUTABLE_CALENDAR_REQUIRED")
        if type(self.coverage) is not tuple or len({c.coverage_id for c in self.coverage}) != len(
            self.coverage
        ):
            raise ValueError("INVALID_COVERAGE_LEDGER")
        if self.authority is not None and type(self.authority) is not EvidenceAuthority:
            raise ValueError("TRUSTED_AUTHORITY_TYPE")
        revision_ends(self.claims)

    def append_correction(self, claim: SessionClaim) -> VerifiedCalendar:
        if claim.supersedes_claim_id is None:
            raise ValueError("SESSION_SUPERSESSION_REQUIRED")
        return replace(self, claims=(*self.claims, claim))

    def query(
        self,
        exchange: str,
        session_date: date,
        known_at: datetime,
        evidence_policy: Policy = "STRICT",
        *,
        calendar_version: str | None = None,
    ) -> SessionResolution:
        query_time(known_at)
        if type(session_date) is not date:
            raise ValueError("DATE_REQUIRED")
        text(exchange)
        if evidence_policy not in {"STRICT", "CANARY_ONLY"}:
            raise ValueError("EVIDENCE_POLICY")
        ends = revision_ends(self.claims)
        selected = tuple(
            sorted(
                (
                    c
                    for c in self.claims
                    if c.exchange == exchange
                    and c.session_date == session_date
                    and (calendar_version is None or c.calendar_version == calendar_version)
                    and (c.known_from is None or c.known_from <= known_at)
                    and (c.known_to is None or known_at < c.known_to)
                    and (c.claim_id not in ends or known_at < ends[c.claim_id])
                ),
                key=lambda c: c.claim_id,
            )
        )
        if not selected:
            return SessionResolution("COVERAGE_UNKNOWN")
        if any(c.evidence.permission != "PERMITTED" for c in selected):
            return SessionResolution("SOURCE_BLOCKED", selected)
        if len(selected) > 1:
            return SessionResolution("CONFLICTING_CALENDAR", selected)
        c = selected[0]
        if c.known_from is None or not (
            c.evidence.eligible(evidence_policy)
            if evidence_policy == "CANARY_ONLY"
            else self.authority is not None and self.authority.check_claim(c, known_at).allowed
        ):
            return SessionResolution("PROVISIONAL", selected)
        status = {
            "REGULAR": "AUTHORITATIVE_SESSION",
            "SPECIAL": "VERIFIED_SPECIAL_SESSION",
            "CLOSED": "KNOWN_CLOSURE",
        }[c.session_type]
        result = SessionResolution(status, selected)
        object.__setattr__(result, "financial_eligible", evidence_policy == "STRICT")
        return result

    def coverage_status(
        self, exchange: str, day: date, known_at: datetime, evidence_policy: Policy = "STRICT"
    ) -> str:
        query_time(known_at)
        selected = tuple(
            c
            for c in self.coverage
            if c.exchange == exchange
            and c.valid_from <= day < c.valid_to
            and c.known_from is not None
            and c.known_from <= known_at
            and (c.known_to is None or known_at < c.known_to)
        )
        if not selected:
            return "UNKNOWN"
        if len(selected) > 1:
            return "CONFLICTING"
        c = selected[0]
        eligible = (
            c.evidence.eligible(evidence_policy)
            if evidence_policy == "CANARY_ONLY"
            else (self.authority is not None and self.authority.check_claim(c, known_at).allowed)
        )
        return c.status if eligible else "UNKNOWN"

    def next_session(
        self,
        exchange: str,
        day: date,
        known_at: datetime,
        evidence_policy: Policy = "STRICT",
        *,
        direction: int = 1,
    ) -> SessionResolution:
        if direction not in {-1, 1}:
            raise ValueError("SESSION_DIRECTION")
        for _ in range(3660):
            day += timedelta(days=direction)
            if self.coverage_status(exchange, day, known_at, evidence_policy) != "COMPLETE":
                raise ValueError("CALENDAR_COVERAGE_REQUIRED")
            result = self.query(exchange, day, known_at, evidence_policy)
            if result.status in {"AUTHORITATIVE_SESSION", "VERIFIED_SPECIAL_SESSION"}:
                return result
            if result.status != "KNOWN_CLOSURE":
                raise ValueError("SESSION_EVIDENCE_REQUIRED")
        raise ValueError("CALENDAR_RESOURCE_LIMIT")

    def previous_session(
        self, exchange: str, day: date, known_at: datetime, evidence_policy: Policy = "STRICT"
    ) -> SessionResolution:
        return self.next_session(exchange, day, known_at, evidence_policy, direction=-1)

    def add_business_days(
        self,
        exchange: str,
        anchor_date: date,
        business_days: int,
        known_at: datetime,
        evidence_policy: Policy = "STRICT",
        *,
        max_calendar_days: int = 3660,
    ) -> date:
        if (
            type(business_days) is not int
            or business_days < 0
            or type(max_calendar_days) is not int
            or not 0 < max_calendar_days <= 3660
        ):
            raise ValueError("ARITHMETIC_BUDGET")
        if (
            evidence_policy == "STRICT"
            and self.coverage_status(exchange, anchor_date, known_at, evidence_policy) != "COMPLETE"
        ):
            raise ValueError("CALENDAR_COVERAGE_REQUIRED")
        anchor = self.query(exchange, anchor_date, known_at, evidence_policy)
        accepted = {"AUTHORITATIVE_SESSION", "VERIFIED_SPECIAL_SESSION", "KNOWN_CLOSURE"}
        if anchor.status not in accepted:
            raise ValueError("CALENDAR_COVERAGE_REQUIRED")
        remaining, current = business_days, anchor_date
        for _ in range(max_calendar_days):
            if not remaining:
                return current
            current += timedelta(days=1)
            if (
                evidence_policy == "STRICT"
                and self.coverage_status(exchange, current, known_at, evidence_policy) != "COMPLETE"
            ):
                raise ValueError("CALENDAR_COVERAGE_REQUIRED")
            session = self.query(exchange, current, known_at, evidence_policy)
            if session.status not in accepted:
                raise ValueError("CALENDAR_COVERAGE_REQUIRED")
            if session.status != "KNOWN_CLOSURE":
                remaining -= 1
        if not remaining:
            return current
        raise ValueError("CALENDAR_RESOURCE_LIMIT")


def legacy_session(calendar: TradingCalendar, exchange: str, candidate: date) -> SessionResolution:
    """Reuse existing coverage checks, never promote config into authenticated truth."""
    if calendar.config_state != "loaded" or not calendar.year_is_covered(exchange, candidate.year):
        return SessionResolution("COVERAGE_UNKNOWN")
    return SessionResolution("PROVISIONAL")
