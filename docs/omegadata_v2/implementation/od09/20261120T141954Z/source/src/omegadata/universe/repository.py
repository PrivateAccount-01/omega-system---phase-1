"""Additive, append-only SQLAlchemy store in explicitly owned disposable SQLite.
Reuse OD06 transaction/path conventions and OD07 typed payload encoding.
No operational DB migration, raw-source reads, cleanup, or same-process tamper claim.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import fields, is_dataclass, replace
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from sqlalchemy import (
    Column,
    ForeignKey,
    Index,
    MetaData,
    String,
    Table,
    create_engine,
    event,
    exists,
    func,
    inspect,
    or_,
    select,
)
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.pool import StaticPool

from omegadata import identity as identity
from omegadata import session_calendar as cal
from omegadata.adjustments import bound_contracts as bc
from omegadata.adjustments import contracts as ac
from omegadata.adjustments.repository import TYPES as OLD_TYPES
from omegadata.adjustments.repository import encode as encode_scalar
from omegadata.identity_adapters import MembershipClaim
from omegadata.identity_authority import EvidenceAuthority
from omegadata.universe import contracts as c
from omegadata.universe.snapshots import get_universe_as_of
from omegadata.universe.temporal import business_day, validate_revisions

M = MetaData()
schema = Table("od08_schema", M, Column("version", String, primary_key=True))


def payload() -> list[Column[Any]]:
    return [Column("payload", String, nullable=False), Column("digest", String, nullable=False)]


definitions = Table(
    "od08_definition",
    M,
    Column("id", String, primary_key=True),
    Column("universe", String, nullable=False),
    *payload(),
)
members = Table(
    "od08_membership",
    M,
    Column("id", String, primary_key=True),
    Column("definition", ForeignKey(definitions.c.id), nullable=False),
    Column("universe", String, nullable=False),
    Column("event", String, nullable=False),
    Column("parent", ForeignKey("od08_membership.id"), unique=True),
    Column("valid_from", String, nullable=False),
    Column("valid_to", String),
    Column("known_from", String),
    Column("known_to", String),
    Column("effective_at", String),
    Column("removal_at", String),
    *payload(),
)
coverages = Table(
    "od08_coverage",
    M,
    Column("id", String, primary_key=True),
    Column("definition", ForeignKey(definitions.c.id), nullable=False),
    *payload(),
)
observations = Table(
    "od08_availability",
    M,
    Column("id", String, primary_key=True),
    Column("definition", ForeignKey(definitions.c.id), nullable=False),
    *payload(),
)
policies = Table("od08_policy", M, Column("id", String, primary_key=True), *payload())
contexts = Table(
    "od08_context",
    M,
    Column("id", String, primary_key=True),
    Column("definition", ForeignKey(definitions.c.id), nullable=False),
    Column("policy", ForeignKey(policies.c.id), nullable=False),
    *payload(),
)
snapshots = Table(
    "od08_snapshot",
    M,
    Column("id", String, primary_key=True),
    Column("context", ForeignKey(contexts.c.id), nullable=False),
    *payload(),
)
decisions = Table(
    "od08_decision",
    M,
    Column("snapshot", ForeignKey(snapshots.c.id), primary_key=True),
    Column("revision", ForeignKey(members.c.id), primary_key=True),
    *payload(),
)
Index("od08_membership_query", members.c.universe, members.c.valid_from, members.c.known_from)
Index("od08_membership_history", members.c.event, members.c.known_from)
TYPES: dict[str, Any] = {
    **OLD_TYPES,
    **{
        v.__name__: v
        for v in [
            c.UniverseDefinition,
            c.MembershipRevision,
            c.CoverageTransition,
            c.UniverseCoverage,
            c.AvailabilityPolicy,
            c.AvailabilityObservation,
            c.LiquidityPolicy,
            c.EligibilityPolicy,
            c.UniverseContext,
            c.MemberDecision,
            c.UniverseSnapshot,
            c.RankingCandidate,
            identity.Issuer,
            identity.Security,
            identity.Listing,
            identity.IdentifierClaim,
            identity.MemoryIdentityRepository,
            cal.SessionClaim,
            cal.CoverageClaim,
            cal.VerifiedCalendar,
            MembershipClaim,
            ac.Raw,
            ac.Context,
            ac.Policy,
            ac.Result,
            ac.Link,
            ac.Factor,
            bc.RawObservation,
            bc.ParameterSet,
            bc.HistorySnapshot,
            bc.BasisPolicy,
            bc.ExecutionConstraints,
            bc.PinnedCalculation,
            bc.BoundResult,
        ]
    },
}


def encode(v: Any) -> Any:
    if type(v) is EvidenceAuthority:
        return {"authority_snapshot_digest": v.snapshot_digest()}
    if is_dataclass(v) and not isinstance(v, type):
        return {
            "type": type(v).__name__,
            "values": {f.name: encode(getattr(v, f.name)) for f in fields(v)},
        }
    if isinstance(v, (tuple, list)):
        return [encode(a) for a in v]
    if isinstance(v, dict):
        return {n: encode(a) for n, a in v.items()}
    return encode_scalar(v)


def decode(v: Any, authority: EvidenceAuthority | None = None) -> Any:
    if isinstance(v, list):
        return tuple(decode(a, authority) for a in v)
    if not isinstance(v, dict):
        return v
    if set(v) == {"authority_snapshot_digest"}:
        candidate = authority or EvidenceAuthority.unconfigured()
        if candidate.snapshot_digest() != v["authority_snapshot_digest"]:
            raise ValueError("EXACT_AUTHORITY_OBJECT_REQUIRED")
        return candidate
    if set(v) == {"date"}:
        return date.fromisoformat(v["date"])
    if set(v) == {"datetime"}:
        return datetime.fromisoformat(v["datetime"])
    if set(v) == {"decimal"}:
        return Decimal(v["decimal"])
    if set(v) == {"type", "values"}:
        kind = TYPES[v["type"]]
        allowed = {f.name for f in fields(kind) if f.init}
        return kind(**{n: decode(a, authority) for n, a in v["values"].items() if n in allowed})
    return {n: decode(a, authority) for n, a in v.items()}


def pack(v: Any) -> str:
    return ac.canonical(encode(v))


def unpack(v: str, authority: EvidenceAuthority | None = None) -> Any:
    return decode(json.loads(v), authority)


def sqltime(v: date | datetime | None) -> str | None:
    return str(ac.normalized(v)) if v is not None else None


class UniverseRepository:
    def __init__(
        self, url: str, *, disposable_root: Path, authority: EvidenceAuthority | None = None
    ) -> None:
        parsed = make_url(url)
        if parsed.drivername not in {"sqlite", "sqlite+pysqlite"}:
            raise ValueError("DEVELOPMENT_SQLITE_ONLY")
        if parsed.database not in {None, "", ":memory:"}:
            path = Path(str(parsed.database))
            root = disposable_root.resolve(strict=True)
            if (
                not path.is_absolute()
                or ".." in path.parts
                or path.is_symlink()
                or not path.resolve().is_relative_to(root)
                or any(p.is_symlink() for p in path.parents)
            ):
                raise ValueError("DISPOSABLE_DATABASE_REQUIRED")
        self.authority = authority
        self.engine = create_engine(
            url,
            poolclass=StaticPool if parsed.database in {None, "", ":memory:"} else None,
            connect_args={"check_same_thread": False, "timeout": 5},
        )

        @event.listens_for(self.engine, "connect")
        def setup(dbapi: Any, record: Any) -> None:
            dbapi.execute("PRAGMA foreign_keys=ON")

        existing = set(inspect(self.engine).get_table_names())
        if existing and existing != set(M.tables):
            raise ValueError("OWNED_SCHEMA_REQUIRED")
        with self.engine.begin() as con:
            M.create_all(con)
            versions = con.execute(select(schema.c.version)).scalars().all()
            if versions and versions != ["od08.store/v1"]:
                raise ValueError("SCHEMA_VERSION_UNSUPPORTED")
            if not versions:
                con.execute(schema.insert().values(version="od08.store/v1"))
            for table in M.tables.values():
                for op in ("UPDATE", "DELETE"):
                    con.exec_driver_sql(
                        f"CREATE TRIGGER IF NOT EXISTS {table.name}_{op.lower()} BEFORE {op} ON {table.name} BEGIN SELECT RAISE(ABORT,'APPEND_ONLY'); END"
                    )

    @contextmanager
    def transaction(self) -> Iterator[Connection]:
        with self.engine.connect() as con:
            con.exec_driver_sql("BEGIN IMMEDIATE")
            try:
                yield con
                con.commit()
            except BaseException:
                con.rollback()
                raise

    def close(self) -> None:
        self.engine.dispose()

    def _put(self, con: Connection, table: Table, key: str, value: Any, **extra: Any) -> None:
        body = pack(value)
        old = con.scalar(select(table.c.payload).where(table.c.id == key))
        if old is not None:
            if old != body:
                raise ValueError("IMMUTABLE_RECORD_ID_REUSED")
            return
        con.execute(
            table.insert().values(
                id=key, payload=body, digest=hashlib.sha256(body.encode()).hexdigest(), **extra
            )
        )

    def _rows(self, con: Connection, table: Table, event_id: str | None = None) -> tuple[Any, ...]:
        stmt = select(table.c.payload, table.c.digest).order_by(table.c.id)
        if event_id is not None:
            stmt = stmt.where(table.c.event == event_id)
        rows = con.execute(stmt).all()
        for body, pin in rows:
            if hashlib.sha256(body.encode()).hexdigest() != pin:
                raise ValueError("PERSISTED_PAYLOAD_CHANGED")
        return tuple(unpack(body, self.authority) for body, pin in rows)

    def append_definition(self, value: c.UniverseDefinition) -> str:
        key = ac.digest(value)
        with self.transaction() as con:
            self._put(con, definitions, key, value, universe=value.universe_id)
        return key

    def _definition_key(self, con: Connection, universe_id: str, key: str | None) -> str:
        keys = (
            con.execute(select(definitions.c.id).where(definitions.c.universe == universe_id))
            .scalars()
            .all()
        )
        if key is not None and key in keys:
            return key
        if key is None and len(keys) == 1:
            return str(keys[0])
        raise ValueError("EXACT_DEFINITION_REQUIRED")

    def append_membership(
        self, value: c.MembershipRevision, definition_key: str | None = None
    ) -> None:
        with self.transaction() as con:
            key = self._definition_key(con, value.universe_id, definition_key)
            old = tuple(
                r
                for r in self._rows(con, members, value.event_id)
                if r.universe_id == value.universe_id
            )
            existing = next((r for r in old if r.revision_id == value.revision_id), None)
            if existing is None:
                validate_revisions((*old, value))
            self._put(
                con,
                members,
                value.revision_id,
                value,
                definition=key,
                universe=value.universe_id,
                event=value.event_id,
                parent=value.claim.supersedes_membership_id,
                valid_from=sqltime(value.claim.valid_from),
                valid_to=sqltime(value.claim.valid_to),
                known_from=sqltime(value.claim.known_from),
                known_to=sqltime(value.claim.known_to),
                effective_at=sqltime(value.effective_at),
                removal_at=sqltime(value.removal_effective_at),
            )

    def seed_context(self, x: c.UniverseContext, policy: c.EligibilityPolicy) -> None:
        key = self.append_definition(x.definition)
        for r in sorted(x.memberships, key=lambda r: (r.revision_number, r.revision_id)):
            self.append_membership(r, key)
        with self.transaction() as con:
            self._put(con, policies, policy.policy_version, policy)
            for v in x.coverage:
                self._put(con, coverages, v.coverage_id, v, definition=key)
            for o in x.observations:
                self._put(con, observations, o.observation_id, o, definition=key)

    def _selected_sql(
        self, con: Connection, universe_id: str, day: date | datetime, cutoff: datetime
    ) -> tuple[str, ...]:
        child = members.alias("successor")
        k = sqltime(cutoff)
        point = day
        day = business_day(point)
        successor = exists(
            select(child.c.id).where(child.c.parent == members.c.id, child.c.known_from <= k)
        )
        stmt = (
            select(members.c.id)
            .where(
                members.c.universe == universe_id,
                members.c.valid_from <= sqltime(day),
                or_(
                    members.c.valid_to.is_(None),
                    members.c.valid_to > sqltime(day),
                    (members.c.valid_to == sqltime(day)) & members.c.removal_at.is_not(None),
                ),
                or_(members.c.known_from.is_(None), members.c.known_from <= k),
                or_(members.c.known_to.is_(None), members.c.known_to > k),
                ~successor,
            )
            .order_by(members.c.id)
        )
        if isinstance(point, datetime):
            stmt = stmt.where(
                or_(members.c.effective_at.is_(None), members.c.effective_at <= sqltime(point)),
                or_(members.c.removal_at.is_(None), members.c.removal_at > sqltime(point)),
            )
        return tuple(con.execute(stmt).scalars())

    def pin_context(
        self,
        context_id: str,
        x: c.UniverseContext,
        day: date | datetime,
        cutoff: datetime,
        policy: c.EligibilityPolicy,
    ) -> None:
        # Future-known inputs are not allowed to change an earlier pinned decision.
        kept = tuple(
            r for r in x.memberships if r.claim.known_from is None or r.claim.known_from <= cutoff
        )
        clean = replace(
            x,
            memberships=kept,
            coverage=tuple(v for v in x.coverage if v.known_from is None or v.known_from <= cutoff),
            observations=tuple(
                v for v in x.observations if v.known_from is None or v.known_from <= cutoff
            ),
            authority=None,
            identity=replace(x.identity, authority=None),
            calendar=replace(x.calendar, authority=None),
        )
        expected = get_universe_as_of(x, day, cutoff, policy, x.source_snapshot_id)
        envelope = {
            "context": clean,
            "day": day,
            "cutoff": cutoff,
            "policy": policy,
            "expected": expected.canonical_json,
            "authority_digest": (x.authority or EvidenceAuthority.unconfigured()).snapshot_digest(),
        }
        with self.transaction() as con:
            self._reconcile(con, x, day, cutoff, policy, expected)
            self._put(
                con,
                contexts,
                context_id,
                envelope,
                definition=ac.digest(x.definition),
                policy=policy.policy_version,
            )

    def _reconcile(
        self,
        con: Connection,
        x: c.UniverseContext,
        day: date | datetime,
        cutoff: datetime,
        p: c.EligibilityPolicy,
        out: c.UniverseSnapshot,
    ) -> None:
        if (
            self._selected_sql(con, x.definition.universe_id, day, cutoff)
            != out.selected_revision_ids
        ):
            raise ValueError("INDEPENDENT_SQL_SELECTED_MEMBERS_MISMATCH")
        selected = set(out.selected_revision_ids)
        if (
            len(out.decisions) != len(selected)
            or {v.revision_id for v in out.decisions} != selected
            or out.decision_digest != ac.digest(out.decisions)
        ):
            raise ValueError("INDEPENDENT_DECISION_ACCOUNTING")
        allrows = self._rows(con, members)
        stored = {
            r.revision_id: r
            for r in allrows
            if r.universe_id == x.definition.universe_id
            and (r.claim.known_from is None or r.claim.known_from <= cutoff)
        }
        supplied = {
            r.revision_id: r
            for r in x.memberships
            if r.universe_id == x.definition.universe_id
            and (r.claim.known_from is None or r.claim.known_from <= cutoff)
        }
        if pack(stored) != pack(supplied):
            raise ValueError("MEMBERSHIP_LEDGER_OMITTED_OR_CHANGED")
        if con.scalar(
            select(definitions.c.payload).where(definitions.c.id == ac.digest(x.definition))
        ) != pack(x.definition) or con.scalar(
            select(policies.c.payload).where(policies.c.id == p.policy_version)
        ) != pack(p):
            raise ValueError("DEFINITION_OR_POLICY_NOT_PINNED")
        persisted_coverage = {
            v.coverage_id: v
            for v in self._rows(con, coverages)
            if v.universe_id == x.definition.universe_id
            and (v.known_from is None or v.known_from <= cutoff)
        }
        supplied_coverage = {
            v.coverage_id: v
            for v in x.coverage
            if v.universe_id == x.definition.universe_id
            and (v.known_from is None or v.known_from <= cutoff)
        }
        if pack(persisted_coverage) != pack(supplied_coverage):
            raise ValueError("COVERAGE_LEDGER_OMITTED_OR_CHANGED")
        if p.view != "MEMBERSHIP" and (
            p.require_observations or p.liquidity_policy is not None or p.require_adjustment
        ):
            listing_scope = {d.listing_id for d in out.decisions if d.listing_id is not None}
            scope = p.observation_scope
            if scope is not None and (
                scope.universe_id != x.definition.universe_id
                or not set(scope.listings).issubset(listing_scope)
            ):
                raise ValueError("OBSERVATION_SET_SCOPE")

            windows: dict[str, set[date]] = {}
            if p.liquidity_policy is not None and scope is None:
                for listing in listing_scope:
                    exchange = next(
                        d.claim.exchange for d in x.memberships if d.listing_id == listing
                    )
                    needed: set[date] = set()
                    current = business_day(day)
                    for _ in range(3660):
                        if (
                            x.calendar.coverage_status(exchange, current, cutoff, x.mode)
                            != "COMPLETE"
                        ):
                            raise ValueError("OBSERVATION_SET_WINDOW_UNVERIFIED")
                        session = x.calendar.query(
                            exchange, current, cutoff, x.mode, calendar_version=x.calendar_version
                        )
                        if session.status in {"AUTHORITATIVE_SESSION", "VERIFIED_SPECIAL_SESSION"}:
                            close = session.claims[0].closes_at
                            if close is None:
                                raise ValueError("OBSERVATION_SET_COMPLETION_UNKNOWN")
                            if close <= cutoff:
                                needed.add(current)
                        elif session.status != "KNOWN_CLOSURE":
                            raise ValueError("OBSERVATION_SET_SESSION_UNKNOWN")
                        if len(needed) == p.liquidity_policy.lookback_sessions:
                            break
                        current -= timedelta(days=1)
                    if len(needed) != p.liquidity_policy.lookback_sessions:
                        raise ValueError("OBSERVATION_SET_WINDOW_BUDGET")
                    windows[listing] = needed

            def relevant(o: c.AvailabilityObservation) -> bool:
                if (
                    o.listing_id not in listing_scope
                    or o.source_id not in x.definition.source_scope
                    or o.session_date > business_day(day)
                    or o.known_from is not None
                    and o.known_from > cutoff
                ):
                    return False
                if windows and o.session_date not in windows.get(o.listing_id, set()):
                    return False
                if scope is not None:
                    return (
                        o.listing_id in scope.listings
                        and o.observation_type in scope.observation_types
                        and o.session_date in scope.sessions
                        and o.source_id in scope.source_scope
                        and o.observation_id not in scope.explicitly_excluded_ids
                    )
                return True

            stored_obs = {o.observation_id: o for o in self._rows(con, observations) if relevant(o)}
            supplied_obs = {o.observation_id: o for o in x.observations if relevant(o)}
            if len(supplied_obs) != sum(relevant(o) for o in x.observations) or pack(
                stored_obs
            ) != pack(supplied_obs):
                raise ValueError("OBSERVATION_SET_OMITTED_DUPLICATE_OR_CHANGED")
        inputs_to_check: list[tuple[Table, tuple[Any, ...], str]] = [
            (coverages, x.coverage, "coverage_id"),
            (observations, x.observations, "observation_id"),
        ]
        for table, items, idname in inputs_to_check:
            for value in items:
                lower = value.known_from
                if lower is not None and lower > cutoff:
                    continue
                if con.scalar(
                    select(table.c.payload).where(table.c.id == getattr(value, idname))
                ) != pack(value):
                    raise ValueError("UPSTREAM_EVIDENCE_NOT_PINNED")
        if out.financial_accepted or out.execution_accepted:
            raise ValueError("FINANCIAL_PROMOTION_NOT_AUTHORIZED")
        for d in out.decisions:
            row = stored[d.revision_id]
            if (
                row.security_id is not None
                and d.security_id is not None
                and d.security_id != row.security_id
            ):
                raise ValueError("MEMBER_IDENTITY_CHANGED")

    def _context_payload(self, con: Connection, context_id: str) -> str:
        row = con.execute(
            select(contexts.c.payload, contexts.c.digest).where(contexts.c.id == context_id)
        ).first()
        if row is None:
            raise ValueError("PINNED_CONTEXT_REQUIRED")
        if hashlib.sha256(row[0].encode()).hexdigest() != row[1]:
            raise ValueError("CONTEXT_STORAGE_CHANGED")
        return str(row[0])

    def admit_snapshot(self, context_id: str, out: c.UniverseSnapshot) -> None:
        with self.transaction() as con:
            envelope = self._context_payload(con, context_id)
            data = unpack(envelope, self.authority)
            x = data["context"]
            cutoff = data["cutoff"]
            day = data["day"]
            policy = data["policy"]
            if out.canonical_json != data["expected"]:
                raise ValueError("SNAPSHOT_DOES_NOT_MATCH_PINNED_CONTEXT")
            self._reconcile(con, x, day, cutoff, policy, out)
            self._put(con, snapshots, out.universe_snapshot_id, out, context=context_id)
            for decision in out.decisions:
                body = pack(decision)
                old = con.scalar(
                    select(decisions.c.payload).where(
                        decisions.c.snapshot == out.universe_snapshot_id,
                        decisions.c.revision == decision.revision_id,
                    )
                )
                if old is None:
                    con.execute(
                        decisions.insert().values(
                            snapshot=out.universe_snapshot_id,
                            revision=decision.revision_id,
                            payload=body,
                            digest=ac.digest(decision),
                        )
                    )
                elif old != body:
                    raise ValueError("IMMUTABLE_DECISION_CHANGED")

    def get_snapshot(self, snapshot_id: str) -> str:
        with self.engine.connect() as con:
            row = con.execute(
                select(snapshots.c.payload, snapshots.c.digest).where(snapshots.c.id == snapshot_id)
            ).first()
            if row is None:
                raise LookupError(snapshot_id)
            if hashlib.sha256(row[0].encode()).hexdigest() != row[1]:
                raise ValueError("SNAPSHOT_STORAGE_CHANGED")
            result = cast(c.UniverseSnapshot, unpack(row[0]))
            if result.universe_snapshot_id != snapshot_id:
                raise ValueError("SNAPSHOT_DIGEST_CHANGED")
            return result.canonical_json

    def replay_context(self, context_id: str) -> c.UniverseSnapshot:
        with self.engine.connect() as con:
            body = self._context_payload(con, context_id)
        data = unpack(body, self.authority)
        x = data["context"]
        authority = self.authority or EvidenceAuthority.unconfigured()
        if authority.snapshot_digest() != data["authority_digest"]:
            raise ValueError("AUTHORITY_STATE_CHANGED")
        x = replace(
            x,
            authority=self.authority,
            identity=replace(x.identity, authority=self.authority),
            calendar=replace(x.calendar, authority=self.authority),
        )
        result = get_universe_as_of(
            x, data["day"], data["cutoff"], data["policy"], x.source_snapshot_id
        )
        if result.canonical_json != data["expected"]:
            raise ValueError("REPLAY_NOT_REPRODUCIBLE")
        return result

    def query_plan(
        self, universe_id: str, day: date | datetime, cutoff: datetime
    ) -> tuple[str, ...]:
        with self.engine.connect() as con:
            rows = con.exec_driver_sql(
                "EXPLAIN QUERY PLAN SELECT id FROM od08_membership WHERE universe=? AND valid_from<=? AND (known_from IS NULL OR known_from<=?)",
                (universe_id, sqltime(day), sqltime(cutoff)),
            ).all()
        return tuple(str(r[-1]) for r in rows)

    def rollback_empty(self) -> None:
        with self.transaction() as con:
            if any(
                con.scalar(select(func.count()).select_from(t))
                for t in M.tables.values()
                if t is not schema
            ):
                raise ValueError("NONEMPTY_ROLLBACK_REFUSED")
            M.drop_all(con)
