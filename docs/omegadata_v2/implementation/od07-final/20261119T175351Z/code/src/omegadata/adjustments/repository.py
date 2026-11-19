"""OD07 additive disposable SQLite persistence, versioned canonical immutable rows.
No legacy schema, production migration, automatic cleanup or original data access.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal, Inexact
from pathlib import Path
from typing import Any

from sqlalchemy import (
    Column,
    ForeignKey,
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

from omegadata.adjustments import contracts as c
from omegadata.adjustments.bound_contracts import (
    BoundResult,
    PinnedCalculation,
    ReferenceObservation,
)
from omegadata.adjustments.temporal import select_revisions
from omegadata.identity import Evidence

M = MetaData()
version = Table("od07_schema", M, Column("version", String, primary_key=True))
actions = Table(
    "od07_action",
    M,
    Column("id", String, primary_key=True),
    Column("parent", ForeignKey("od07_action.id"), unique=True),
    Column("payload", String, nullable=False),
    Column("digest", String, nullable=False),
)
results = Table(
    "od07_result",
    M,
    Column("id", String, primary_key=True),
    Column("payload", String, nullable=False),
    Column("digest", String, nullable=False),
)
links = Table(
    "od07_result_action",
    M,
    Column("result_id", ForeignKey("od07_result.id"), primary_key=True),
    Column("action_id", ForeignKey("od07_action.id"), primary_key=True),
)
contexts = Table(
    "od07_calculation_context",
    M,
    Column("id", String, primary_key=True),
    Column("payload", String, nullable=False),
    Column("digest", String, nullable=False),
)
result_context = Table(
    "od07_result_context",
    M,
    Column("result_id", ForeignKey("od07_result.id"), primary_key=True),
    Column("context_id", ForeignKey("od07_calculation_context.id"), nullable=False),
)
LEGACY_TABLES = {"od07_schema", "od07_action", "od07_result", "od07_result_action"}

TYPES: dict[str, Any] = {
    cls.__name__: cls
    for cls in (
        c.Reference,
        c.Split,
        c.Bonus,
        c.Rights,
        c.Dividend,
        c.Merger,
        c.Demerger,
        c.Conversion,
        c.Lifecycle,
        c.Action,
        Evidence,
    )
}


TYPES["ReferenceObservation"] = ReferenceObservation


def encode(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {
            "type": type(value).__name__,
            "values": {f.name: encode(getattr(value, f.name)) for f in fields(value)},
        }
    if isinstance(value, Decimal):
        return {"decimal": str(value)}
    if isinstance(value, datetime):
        return {"datetime": value.isoformat()}
    if isinstance(value, date):
        return {"date": value.isoformat()}
    return value


def decode(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    if set(value) == {"decimal"}:
        return Decimal(value["decimal"])
    if set(value) == {"datetime"}:
        return datetime.fromisoformat(value["datetime"])
    if set(value) == {"date"}:
        return date.fromisoformat(value["date"])
    if set(value) == {"type", "values"} and value["type"] in TYPES:
        return TYPES[value["type"]](**{k: decode(v) for k, v in value["values"].items()})
    raise ValueError("PERSISTED_TYPE_INVALID")


def packed(action: c.Action) -> str:
    return json.dumps(encode(action), sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


class AdjustmentRepository:
    def __init__(self, url: str, *, disposable_root: Path) -> None:
        parsed = make_url(url)
        if parsed.drivername != "sqlite" or parsed.query:
            raise ValueError("DISPOSABLE_SQLITE_ONLY")
        root = disposable_root.resolve(strict=True)
        if parsed.database not in (None, "", ":memory:"):
            assert parsed.database is not None
            path = Path(parsed.database)
            if not path.is_absolute() or path.is_symlink():
                raise ValueError("DATABASE_PATH_UNSAFE")
            for parent in path.parents:
                if parent.is_symlink():
                    raise ValueError("DATABASE_PATH_UNSAFE")
            if (
                not path.resolve().is_relative_to(root)
                or path.exists()
                and (not path.is_file() or path.stat().st_nlink != 1)
            ):
                raise ValueError("DATABASE_OUTSIDE_DISPOSABLE_ROOT")
        self.engine = create_engine(
            url,
            poolclass=StaticPool if parsed.database in (None, "", ":memory:") else None,
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(self.engine, "connect")
        def configure(dbapi: Any, record: Any) -> None:
            dbapi.execute("PRAGMA foreign_keys=ON")
            dbapi.execute("PRAGMA busy_timeout=5000")

        tables = set(inspect(self.engine).get_table_names())
        if tables and tables not in (LEGACY_TABLES, set(M.tables)):
            self.engine.dispose()
            raise ValueError("UNRELATED_OR_PARTIAL_SCHEMA")
        self.migrate()

    @contextmanager
    def transaction(self) -> Iterator[Connection]:
        with self.engine.connect() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            try:
                yield connection
                connection.commit()
            except BaseException:
                connection.rollback()
                raise

    def migrate(self) -> None:
        with self.transaction() as connection:
            M.create_all(connection)
            old = set(connection.scalars(select(version.c.version)).all())
            if old - {"od07.store/v1", "od07.store/v2"}:
                raise ValueError("STORE_VERSION")
            if not old:
                connection.execute(version.insert().values(version="od07.store/v1"))
            if "od07.store/v2" not in old:
                connection.execute(version.insert().values(version="od07.store/v2"))
            for table in M.tables:
                for operation in ("UPDATE", "DELETE"):
                    connection.exec_driver_sql(
                        f"CREATE TRIGGER IF NOT EXISTS {table}_{operation}_immutable BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT,'OD07_APPEND_ONLY'); END"
                    )

    def rollback_schema(self) -> None:
        with self.transaction() as connection:
            if (
                connection.scalar(select(actions.c.id).limit(1)) is not None
                or connection.scalar(select(results.c.id).limit(1)) is not None
                or connection.scalar(select(contexts.c.id).limit(1)) is not None
            ):
                raise ValueError("POPULATED_HISTORY_ROLLBACK_REFUSED")
            M.drop_all(connection)

    def _all(self, connection: Connection) -> tuple[c.Action, ...]:
        out = []
        for row in connection.execute(select(actions).order_by(actions.c.id)).mappings():
            if sha(row["payload"]) != row["digest"]:
                raise ValueError("PERSISTED_HASH_MISMATCH")
            value = decode(json.loads(row["payload"]))
            if (
                type(value) is not c.Action
                or value.action_id != row["id"]
                or value.supersedes_action_id != row["parent"]
            ):
                raise ValueError("PERSISTED_IDENTITY_MISMATCH")
            out.append(value)
        return tuple(out)

    def append_action(self, action: c.Action) -> None:
        payload = packed(action)
        with self.transaction() as connection:
            old = self._all(connection)
            same = next((a for a in old if a.action_id == action.action_id), None)
            if same is not None:
                if packed(same) != payload:
                    raise ValueError("ACTION_ID_REUSED")
                return
            # Full revision graph is checked independent of which cutoff is queried.
            from datetime import UTC

            select_revisions((*old, action), datetime.max.replace(tzinfo=UTC))
            connection.execute(
                actions.insert().values(
                    id=action.action_id,
                    parent=action.supersedes_action_id,
                    payload=payload,
                    digest=sha(payload),
                )
            )

    def append_result(self, result: c.Result, action_ids: tuple[str, ...]) -> None:
        validate_result(result)
        raw = result.canonical_json
        if (
            result.status != "CALCULATED"
            or set(action_ids)
            != {link.action_revision_id for link in result.adjustment_factor_chain}
            or len(action_ids) != len(set(action_ids))
        ):
            raise ValueError("RESULT_CHAIN_REFERENCES")
        with self.transaction() as connection:
            stored = {a.action_id: a for a in self._all(connection)}
            for link in result.adjustment_factor_chain:
                if (
                    link.action_revision_id not in stored
                    or c.canonical(stored[link.action_revision_id]) != link.input_parameters
                ):
                    raise ValueError("RESULT_ACTION_PAYLOAD_MISMATCH")
                from omegadata.adjustments.factors import factor

                action = stored[link.action_revision_id]
                policy_body = json.loads(result.inputs)["policy"]
                expected = factor(
                    action.action_type,
                    action.parameters,
                    c.Policy(
                        policy_body["profile"], policy_body["direction"], policy_body["version"]
                    ),
                )
                if link.factor != expected:
                    raise ValueError("RESULT_ACTION_FACTOR_MISMATCH")
            old = connection.scalar(
                select(results.c.payload).where(results.c.id == result.output_digest)
            )
            if old is not None:
                if old != raw:
                    raise ValueError("RESULT_ID_REUSED")
                return
            connection.execute(
                results.insert().values(id=result.output_digest, payload=raw, digest=sha(raw))
            )
            for identity in action_ids:
                connection.execute(
                    links.insert().values(result_id=result.output_digest, action_id=identity)
                )

    def get_result(self, identity: str) -> str | None:
        with self.engine.connect() as connection:
            row = (
                connection.execute(select(results).where(results.c.id == identity))
                .mappings()
                .first()
            )
            if row is None:
                return None
            if sha(row["payload"]) != row["digest"] or row["digest"] != identity:
                raise ValueError("PERSISTED_RESULT_HASH")
            return str(row["payload"])

    def action_ids(self) -> tuple[str, ...]:
        with self.engine.connect() as connection:
            return tuple(a.action_id for a in self._all(connection))

    def history(self, root: str) -> tuple[c.Action, ...]:
        with self.engine.connect() as connection:
            all_actions = self._all(connection)
        by_id = {a.action_id: a for a in all_actions}
        if root not in by_id:
            return ()
        result = [by_id[root]]
        while True:
            child = next(
                (a for a in all_actions if a.supersedes_action_id == result[-1].action_id), None
            )
            if child is None:
                break
            result.append(child)
        return tuple(result)

    def pin_context(self, pin: PinnedCalculation) -> str:
        from omegadata.adjustments.admission import pin_context

        return pin_context(self, pin)

    def append_bound_result(
        self, result: BoundResult, context_id: str, *, expected_result_id: str | None = None
    ) -> None:
        from omegadata.adjustments.admission import append_bound_result

        append_bound_result(self, result, context_id, expected_result_id)

    def close(self) -> None:
        self.engine.dispose()


def validate_result(result: c.Result) -> None:
    """Reconcile stored arithmetic/lineage; this is not a financial certification."""
    from decimal import ROUND_HALF_UP, localcontext

    body = json.loads(result.inputs) if result.inputs else {}
    if result.status != "CALCULATED" or not body:
        raise ValueError("RESULT_NOT_CALCULATED")
    raw = body["raw"]
    expected_actions = sorted(
        (
            action
            for action in body["actions"]
            if action["ex_date"] is None
            or raw["trade_date"] < action["ex_date"] <= body["valid_at"]
        ),
        key=lambda action: (
            action["ex_date"] or raw["trade_date"],
            action["sequence"] or 0,
            action["action_id"],
        ),
    )
    if [link.action_revision_id for link in result.adjustment_factor_chain] != [
        action["action_id"] for action in expected_actions
    ]:
        raise ValueError("RESULT_CHAIN_ORDER_MISMATCH")
    policy = c.Policy(
        body["policy"]["profile"], body["policy"]["direction"], body["policy"]["version"]
    )
    with localcontext(c.arithmetic_context()) as math:
        math.prec = 20480
        n = d = vn = vd = Decimal(1)
        for link in result.adjustment_factor_chain:
            if (
                link.consumer_profile != policy.profile
                or link.raw_observation_reference != raw["artifact_id"]
                or link.calculation_version != c.VERSION
            ):
                raise ValueError("RESULT_LINEAGE_MISMATCH")
            # Exact typed action is bound to persistent action rows separately.
            f = link.factor
            if f.status not in {"CALCULATED", "NOT_APPLICABLE"} or any(
                v is None
                for v in (f.numerator, f.denominator, f.volume_numerator, f.volume_denominator)
            ):
                raise ValueError("INVALID_FACTOR")
            assert (
                f.numerator is not None
                and f.denominator is not None
                and f.volume_numerator is not None
                and f.volume_denominator is not None
            )
            n *= f.numerator
            d *= f.denominator
            vn *= f.volume_numerator
            vd *= f.volume_denominator
        math.traps[Inexact] = False
        math.prec = c.PRECISION
        price = Decimal(raw["price"])
        volume = Decimal(raw["volume"])
        expected_price = (
            price
            if policy.profile in {"RAW", "EXECUTION", "VOLUME"}
            else (price * n / d).quantize(policy.price_quantum, rounding=ROUND_HALF_UP)
        )
        expected_volume = (
            volume
            if policy.profile in {"RAW", "EXECUTION"}
            else (volume * vn / vd).quantize(policy.volume_quantum, rounding=ROUND_HALF_UP)
        )
        if (
            result.adjusted_price,
            result.adjusted_volume,
            result.cumulative_factor,
            result.cumulative_volume_factor,
        ) != (expected_price, expected_volume, n / d, vn / vd):
            raise ValueError("RESULT_MATH_MISMATCH")
