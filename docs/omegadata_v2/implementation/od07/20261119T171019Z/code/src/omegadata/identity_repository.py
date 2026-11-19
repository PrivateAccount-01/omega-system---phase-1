"""OD06 additive, append-only SQLite repository. Disposable development only.

Legacy ORM tables and operational databases are never migrated. Each write uses
BEGIN IMMEDIATE and a single commit; unique-parent constraints serialize revisions.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import (
    Column,
    ForeignKey,
    Index,
    MetaData,
    String,
    Table,
    create_engine,
    event,
    inspect,
    select,
)
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.pool import StaticPool

from omegadata.identity import (
    Evidence,
    IdentifierClaim,
    Issuer,
    LifecycleEvent,
    Listing,
    MemoryIdentityRepository,
    Policy,
    Resolution,
    Security,
    query_time,
    revision_ends,
    validate_events,
)
from omegadata.identity_adapters import (
    MembershipClaim,
    StrictUniverse,
    membership_revision_ends,
    strict_universe,
)
from omegadata.identity_authority import EvidenceAuthority, canonical
from omegadata.session_calendar import CoverageClaim, SessionClaim, VerifiedCalendar

VERSION = "od06.store/v1"
M = MetaData()
version_table = Table("od06_schema", M, Column("version", String, primary_key=True))
identities = Table(
    "od06_identity_id",
    M,
    Column("id", String, primary_key=True),
    Column("kind", String, nullable=False),
)


def payload_columns() -> list[Column[Any]]:
    return [Column("payload", String, nullable=False), Column("digest", String, nullable=False)]


issuers = Table(
    "od06_issuer",
    M,
    Column("id", ForeignKey(identities.c.id), primary_key=True),
    *payload_columns(),
)
securities = Table(
    "od06_security",
    M,
    Column("id", ForeignKey(identities.c.id), primary_key=True),
    Column("issuer", ForeignKey(issuers.c.id)),
    *payload_columns(),
)
listings = Table(
    "od06_listing",
    M,
    Column("id", ForeignKey(identities.c.id), primary_key=True),
    Column("security", ForeignKey(securities.c.id)),
    Column("exchange", String, nullable=False),
    *payload_columns(),
)
evidence = Table("od06_evidence", M, Column("id", String, primary_key=True), *payload_columns())
claims = Table(
    "od06_claim",
    M,
    Column("id", String, primary_key=True),
    Column("listing", ForeignKey(listings.c.id), nullable=False),
    Column("evidence", ForeignKey(evidence.c.id), nullable=False),
    Column("parent", ForeignKey("od06_claim.id"), unique=True),
    Column("exchange", String, nullable=False),
    Column("symbol", String, nullable=False),
    Column("series", String, nullable=False),
    Column("valid_from", String, nullable=False),
    Column("valid_to", String),
    Column("known_from", String),
    Column("known_to", String),
    *payload_columns(),
)
Index(
    "od06_claim_lookup",
    claims.c.exchange,
    claims.c.symbol,
    claims.c.series,
    claims.c.valid_from,
    claims.c.known_from,
)
events = Table(
    "od06_event",
    M,
    Column("id", String, primary_key=True),
    Column("evidence", ForeignKey(evidence.c.id), nullable=False),
    Column("parent", ForeignKey("od06_event.id"), unique=True),
    *payload_columns(),
)
event_links = Table(
    "od06_event_identity",
    M,
    Column("event", ForeignKey(events.c.id), primary_key=True),
    Column("identity", ForeignKey(identities.c.id), primary_key=True),
)
sessions = Table(
    "od06_session",
    M,
    Column("id", String, primary_key=True),
    Column("evidence", ForeignKey(evidence.c.id), nullable=False),
    Column("parent", ForeignKey("od06_session.id"), unique=True),
    Column("exchange", String, nullable=False),
    Column("session_date", String, nullable=False),
    Column("calendar_version", String, nullable=False),
    *payload_columns(),
)
Index("od06_claim_listing_history", claims.c.listing, claims.c.known_from)
Index(
    "od06_session_lookup", sessions.c.exchange, sessions.c.session_date, sessions.c.calendar_version
)
coverage = Table(
    "od06_calendar_coverage",
    M,
    Column("id", String, primary_key=True),
    Column("evidence", ForeignKey(evidence.c.id), nullable=False),
    *payload_columns(),
)
memberships = Table(
    "od06_membership",
    M,
    Column("id", String, primary_key=True),
    Column("evidence", ForeignKey(evidence.c.id), nullable=False),
    Column("parent", ForeignKey("od06_membership.id"), unique=True),
    *payload_columns(),
)


def decode(kind: type[Any], raw: str) -> Any:
    obj = json.loads(raw)
    for k in ("valid_from", "valid_to", "session_date"):
        if obj.get(k) is not None:
            obj[k] = date.fromisoformat(obj[k])
    for k in (
        "known_from",
        "known_to",
        "published_at",
        "effective_at",
        "ingested_at",
        "opens_at",
        "closes_at",
    ):
        if obj.get(k) is not None:
            obj[k] = datetime.fromisoformat(obj[k])
    if "evidence" in obj:
        obj["evidence"] = Evidence(**obj["evidence"])
    if "affected_identity_ids" in obj:
        obj["affected_identity_ids"] = tuple(obj["affected_identity_ids"])
    return kind(**obj)


class PersistentRepository:
    def __init__(
        self, url: str, *, disposable_root: Path, authority: EvidenceAuthority | None = None
    ) -> None:
        parsed = make_url(url)
        if parsed.drivername not in {"sqlite", "sqlite+pysqlite"}:
            raise ValueError("DEVELOPMENT_SQLITE_ONLY")
        self._memory = parsed.database in {None, "", ":memory:"}
        if not self._memory:
            p = Path(str(parsed.database))
            root = disposable_root.resolve(strict=True)
            if (
                not p.is_absolute()
                or ".." in p.parts
                or p.is_symlink()
                or not p.resolve().is_relative_to(root)
            ):
                raise ValueError("DISPOSABLE_DATABASE_REQUIRED")
            for parent in p.parents:
                if parent.is_symlink():
                    raise ValueError("DATABASE_PATH_REDIRECTED")
        self.url = url
        self.authority = authority
        self.engine = create_engine(
            url,
            connect_args={"check_same_thread": False, "timeout": 5},
            **({"poolclass": StaticPool} if self._memory else {}),
        )

        @event.listens_for(self.engine, "connect")
        def configure(dbapi_connection: Any, connection_record: Any) -> None:
            dbapi_connection.execute("PRAGMA foreign_keys=ON")
            dbapi_connection.execute("PRAGMA busy_timeout=5000")

        existing = set(inspect(self.engine).get_table_names())
        if existing and existing != set(M.tables):
            self.close()
            raise ValueError("NOT_AN_OD06_DISPOSABLE_SCHEMA")
        self.migrate()

    @contextmanager
    def transaction(self) -> Iterator[Connection]:
        with self.engine.connect() as conn:
            conn.exec_driver_sql("BEGIN IMMEDIATE")
            try:
                yield conn
                conn.commit()
            except BaseException:
                conn.rollback()
                raise

    def migrate(self) -> None:
        with self.transaction() as conn:
            M.create_all(conn)
            versions = conn.scalars(select(version_table.c.version)).all()
            if not versions:
                conn.execute(version_table.insert().values(version=VERSION))
            elif versions != [VERSION]:
                raise ValueError("SCHEMA_VERSION_MISMATCH")
            for table in M.tables.values():
                for operation in ("UPDATE", "DELETE"):
                    name = table.name + "_" + operation.lower()
                    conn.exec_driver_sql(
                        f"CREATE TRIGGER IF NOT EXISTS {name} BEFORE {operation} ON {table.name} BEGIN SELECT RAISE(ABORT,'OD06_APPEND_ONLY'); END"
                    )

    @property
    def schema_version(self) -> str:
        with self.engine.connect() as conn:
            return str(conn.scalar(select(version_table.c.version)))

    def rollback_empty_schema(self) -> None:
        with self.transaction() as conn:
            if any(
                conn.execute(select(t).limit(1)).first() is not None
                for t in M.tables.values()
                if t is not version_table
            ):
                raise ValueError("NONEMPTY_HISTORY_ROLLBACK_FORBIDDEN")
            M.drop_all(conn)

    def close(self) -> None:
        self.engine.dispose()

    def reconnect(self) -> None:
        if not self._memory:
            self.engine.dispose()
        if self.schema_version != VERSION:
            raise ValueError("SCHEMA_VERSION_MISMATCH")

    def _rows(
        self, conn: Connection, table: Table, kind: type[Any], statement: Any = None
    ) -> tuple[Any, ...]:
        rows = conn.execute(
            select(table).order_by(table.c.id) if statement is None else statement
        ).mappings()
        result = []
        for row in rows:
            if hashlib.sha256(row["payload"].encode()).hexdigest() != row["digest"]:
                raise ValueError("PERSISTED_RECORD_CHANGED")
            item = decode(kind, row["payload"])
            if canonical(item) != row["payload"]:
                raise ValueError("PERSISTED_RECORD_NONCANONICAL")
            result.append(item)
        return tuple(result)

    def _put(
        self,
        conn: Connection,
        table: Table,
        key: str,
        value: Any,
        extra: dict[str, Any],
        idempotent: bool = False,
    ) -> bool:
        body = canonical(value)
        digest = hashlib.sha256(body.encode()).hexdigest()
        old = conn.execute(select(table).where(table.c.id == key)).mappings().first()
        if old:
            if idempotent and old["payload"] == body and old["digest"] == digest:
                return False
            raise ValueError("DUPLICATE_OR_CHANGED_RECORD")
        conn.execute(table.insert().values(id=key, payload=body, digest=digest, **extra))
        return True

    def _evidence(self, conn: Connection, value: Evidence) -> None:
        self._put(conn, evidence, value.evidence_id, value, {}, True)

    def _snapshot(self, conn: Connection) -> MemoryIdentityRepository:
        return MemoryIdentityRepository(
            self._rows(conn, issuers, Issuer),
            self._rows(conn, securities, Security),
            self._rows(conn, listings, Listing),
            self._rows(conn, claims, IdentifierClaim),
            self.authority,
        )

    def append_entities(
        self,
        issuer_rows: tuple[Issuer, ...],
        security_rows: tuple[Security, ...],
        listing_rows: tuple[Listing, ...],
    ) -> None:
        with self.transaction() as conn:
            before = self._snapshot(conn)
            MemoryIdentityRepository(
                (*before.issuers, *issuer_rows),
                (*before.securities, *security_rows),
                (*before.listings, *listing_rows),
                before.claims,
            )
            operations: list[tuple[str, Table, Any, str]] = [
                ("issuer", issuers, issuer_rows, "issuer_id"),
                ("security", securities, security_rows, "security_id"),
                ("listing", listings, listing_rows, "listing_id"),
            ]
            for kind, table, rows, key in operations:
                for value in rows:
                    identity = getattr(value, key)
                    conn.execute(identities.insert().values(id=identity, kind=kind))
                    extra = (
                        {"issuer": value.issuer_id}
                        if kind == "security"
                        else {"security": value.security_id, "exchange": value.exchange}
                        if kind == "listing"
                        else {}
                    )
                    self._put(conn, table, identity, value, extra)

    def append_identity_claim(
        self,
        claim: IdentifierClaim,
        *,
        idempotent: bool = False,
        _interrupt_after_insert: bool = False,
    ) -> None:
        with self.transaction() as conn:
            old = conn.execute(
                select(claims.c.payload).where(claims.c.id == claim.claim_id)
            ).scalar_one_or_none()
            if old is not None:
                if idempotent and old == canonical(claim):
                    return
                raise ValueError("DUPLICATE_CLAIM")
            snapshot = self._snapshot(conn)
            replace(snapshot, claims=(*snapshot.claims, claim))
            self._evidence(conn, claim.evidence)
            self._put(
                conn,
                claims,
                claim.claim_id,
                claim,
                {
                    "listing": claim.listing_id,
                    "evidence": claim.evidence.evidence_id,
                    "parent": claim.supersedes_claim_id,
                    "exchange": claim.exchange,
                    "symbol": claim.symbol,
                    "series": claim.series,
                    "valid_from": claim.valid_from.isoformat(),
                    "valid_to": claim.valid_to.isoformat() if claim.valid_to else None,
                    "known_from": claim.known_from.isoformat() if claim.known_from else None,
                    "known_to": claim.known_to.isoformat() if claim.known_to else None,
                },
            )
            if _interrupt_after_insert:
                raise RuntimeError("NON_MARKET_CONTROLLED_TRANSACTION_INTERRUPTION")

    def append_identity_correction(
        self,
        claim: IdentifierClaim,
        *,
        idempotent: bool = False,
        _interrupt_after_insert: bool = False,
    ) -> None:
        if not claim.supersedes_claim_id:
            raise ValueError("CORRECTION_PARENT_REQUIRED")
        self.append_identity_claim(
            claim, idempotent=idempotent, _interrupt_after_insert=_interrupt_after_insert
        )

    def get_identity_history(
        self, listing_id: str, *, version: str = VERSION
    ) -> tuple[IdentifierClaim, ...]:
        if version != VERSION:
            raise ValueError("QUERY_VERSION_UNSUPPORTED")
        with self.engine.connect() as conn:
            rows = self._rows(
                conn,
                claims,
                IdentifierClaim,
                select(claims).where(claims.c.listing == listing_id).order_by(claims.c.id),
            )
        return tuple(
            sorted(
                rows,
                key=lambda c: (
                    c.valid_from,
                    c.known_from.isoformat() if c.known_from else "",
                    c.claim_id,
                ),
            )
        )

    def get_claim_revisions(self, claim_id: str) -> tuple[IdentifierClaim, ...]:
        with self.engine.connect() as conn:
            rows = self._rows(conn, claims, IdentifierClaim)
        by_id = {c.claim_id: c for c in rows}
        if claim_id not in by_id:
            raise LookupError("CLAIM_UNKNOWN")
        current = by_id[claim_id]
        while current.supersedes_claim_id:
            current = by_id[current.supersedes_claim_id]
        family = [current]
        while True:
            child = next((c for c in rows if c.supersedes_claim_id == current.claim_id), None)
            if child is None:
                break
            family.append(child)
            current = child
        return tuple(family)

    def serialize_history(self) -> str:
        with self.engine.connect() as conn:
            return canonical(self._rows(conn, claims, IdentifierClaim))

    def resolve_listing(
        self,
        exchange: str,
        symbol: str,
        series: str,
        valid_at: date,
        known_at: datetime,
        evidence_policy: Policy = "STRICT",
        *,
        version: str = VERSION,
    ) -> Resolution:
        query_time(known_at)
        if version != VERSION:
            raise ValueError("QUERY_VERSION_UNSUPPORTED")
        with self.engine.connect() as conn:
            selected = self._rows(
                conn,
                claims,
                IdentifierClaim,
                select(claims)
                .where(
                    claims.c.exchange == exchange,
                    claims.c.symbol == symbol,
                    claims.c.series == series,
                    claims.c.valid_from <= valid_at.isoformat(),
                    (claims.c.valid_to.is_(None)) | (claims.c.valid_to > valid_at.isoformat()),
                )
                .order_by(claims.c.id),
            )
            # Load only histories for candidate listings. Preserve original records
            # for authority hashing; derived temporal closure stays inside resolver.
            relevant_listing_ids = {c.listing_id for c in selected}
            reduced = (
                self._rows(
                    conn,
                    claims,
                    IdentifierClaim,
                    select(claims)
                    .where(claims.c.listing.in_(relevant_listing_ids))
                    .order_by(claims.c.id),
                )
                if relevant_listing_ids
                else ()
            )
            ls = self._rows(
                conn,
                listings,
                Listing,
                select(listings)
                .where(listings.c.id.in_({c.listing_id for c in selected}))
                .order_by(listings.c.id),
            )
            ss = self._rows(
                conn,
                securities,
                Security,
                select(securities)
                .where(securities.c.id.in_({listing.security_id for listing in ls}))
                .order_by(securities.c.id),
            )
            ii = self._rows(
                conn,
                issuers,
                Issuer,
                select(issuers)
                .where(issuers.c.id.in_({s.issuer_id for s in ss}))
                .order_by(issuers.c.id),
            )
            result = MemoryIdentityRepository(ii, ss, ls, reduced, self.authority).resolve_listing(
                exchange, symbol, series, valid_at, known_at, evidence_policy
            )
            if result.state == "RESOLVED":
                lifecycle = self._rows(conn, events, LifecycleEvent)
                associated = [e for e in lifecycle if result.listing_id in e.affected_identity_ids]
                if any(e.known_from is None or e.effective_at is None for e in associated):
                    return Resolution(
                        "QUARANTINED", result.claim_ids, reason="LIFECYCLE_AVAILABILITY_UNKNOWN"
                    )
                superseded = {
                    e.supersedes_event_id
                    for e in lifecycle
                    if e.known_from is not None and e.known_from <= known_at
                }
                relevant = [
                    e
                    for e in lifecycle
                    if result.listing_id in e.affected_identity_ids
                    and e.event_id not in superseded
                    and e.known_from is not None
                    and e.known_from <= known_at
                    and e.effective_at is not None
                    and e.effective_at.astimezone(ZoneInfo("Asia/Kolkata")).date() <= valid_at
                ]
                if relevant:
                    effective = max(e.effective_at for e in relevant)
                    latest = [e for e in relevant if e.effective_at == effective]
                    expected = {
                        "LISTING": "LISTED",
                        "RELISTING": "LISTED",
                        "SUSPENSION": "SUSPENDED",
                        "DELISTING": "DELISTED",
                    }
                    if any(
                        expected.get(e.event_type, result.lifecycle) != result.lifecycle
                        for e in latest
                    ):
                        return Resolution(
                            "QUARANTINED", result.claim_ids, reason="LIFECYCLE_CLAIM_CONTRADICTION"
                        )
            return result

    def validate_identity_consistency(self) -> tuple[str, ...]:
        with self.engine.connect() as conn:
            rows = self._snapshot(conn).claims
        ends = revision_ends(rows)
        issues = []
        for i, a in enumerate(rows):
            for b in rows[i + 1 :]:
                if (a.exchange, a.symbol, a.series) != (b.exchange, b.symbol, b.series):
                    continue
                ae = ends.get(a.claim_id) or a.known_to
                be = ends.get(b.claim_id) or b.known_to
                if (
                    (a.valid_to is None or b.valid_from < a.valid_to)
                    and (b.valid_to is None or a.valid_from < b.valid_to)
                    and (
                        a.known_from is None
                        or b.known_from is None
                        or ((ae is None or b.known_from < ae) and (be is None or a.known_from < be))
                    )
                ):
                    issues.append("OVERLAPPING_CLAIMS:" + a.claim_id + ":" + b.claim_id)
        return tuple(sorted(issues))

    def append_event(self, value: LifecycleEvent, *, idempotent: bool = False) -> None:
        with self.transaction() as conn:
            old = self._rows(conn, events, LifecycleEvent)
            duplicate = next((e for e in old if e.event_id == value.event_id), None)
            if duplicate is not None:
                if idempotent and canonical(duplicate) == canonical(value):
                    return
                raise ValueError("DUPLICATE_EVENT")
            validate_events((*old, value))
            self._evidence(conn, value.evidence)
            self._put(
                conn,
                events,
                value.event_id,
                value,
                {"evidence": value.evidence.evidence_id, "parent": value.supersedes_event_id},
                idempotent,
            )
            for identity in value.affected_identity_ids:
                conn.execute(event_links.insert().values(event=value.event_id, identity=identity))

    def append_session(self, value: SessionClaim, *, idempotent: bool = False) -> None:
        with self.transaction() as conn:
            old = self._rows(conn, sessions, SessionClaim)
            if not any(c.claim_id == value.claim_id for c in old):
                VerifiedCalendar((*old, value))
            self._evidence(conn, value.evidence)
            self._put(
                conn,
                sessions,
                value.claim_id,
                value,
                {
                    "evidence": value.evidence.evidence_id,
                    "parent": value.supersedes_claim_id,
                    "exchange": value.exchange,
                    "session_date": value.session_date.isoformat(),
                    "calendar_version": value.calendar_version,
                },
                idempotent,
            )

    def append_coverage(self, value: CoverageClaim, *, idempotent: bool = False) -> None:
        with self.transaction() as conn:
            self._evidence(conn, value.evidence)
            self._put(
                conn,
                coverage,
                value.coverage_id,
                value,
                {"evidence": value.evidence.evidence_id},
                idempotent,
            )

    def calendar(self) -> VerifiedCalendar:
        with self.engine.connect() as conn:
            return VerifiedCalendar(
                self._rows(conn, sessions, SessionClaim),
                self._rows(conn, coverage, CoverageClaim),
                self.authority,
            )

    def append_membership(self, value: MembershipClaim, *, idempotent: bool = False) -> None:
        with self.transaction() as conn:
            old = self._rows(conn, memberships, MembershipClaim)
            if not any(c.membership_id == value.membership_id for c in old):
                membership_revision_ends((*old, value))
            self._evidence(conn, value.evidence)
            self._put(
                conn,
                memberships,
                value.membership_id,
                value,
                {"evidence": value.evidence.evidence_id, "parent": value.supersedes_membership_id},
                idempotent,
            )

    def universe(
        self,
        index_name: str,
        valid_at: date,
        known_at: datetime,
        evidence_policy: Policy = "STRICT",
    ) -> StrictUniverse:
        with self.engine.connect() as conn:
            return strict_universe(
                self._rows(conn, memberships, MembershipClaim),
                self._snapshot(conn),
                index_name,
                valid_at,
                known_at,
                evidence_policy,
            )

    def native_foreign_key_probe(self) -> None:
        with self.transaction() as conn:
            conn.execute(
                securities.insert().values(
                    id="UNREGISTERED_CANARY", issuer="MISSING", payload="{}", digest="x"
                )
            )

    def native_mutation_probe(self, operation: str) -> None:
        with self.transaction() as conn:
            if operation == "update":
                conn.execute(claims.update().values(symbol="MUTATION_CANARY"))
            elif operation == "delete":
                conn.execute(claims.delete())
            else:
                raise ValueError("PROBE_OPERATION")
