"""Version-pinned local storage. SQLite visibility, immutable files, recoverable orphans."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Connection

from omegadata.canonical_storage import schema
from omegadata.canonical_storage.contracts import (
    DatasetDefinition,
    Observation,
    Query,
    QueryResult,
    StorageError,
    fingerprint,
    timestamp,
    token,
)

DDL = (
    "CREATE TABLE IF NOT EXISTS comparison_scope(id TEXT PRIMARY KEY,payload TEXT NOT NULL,digest TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS source_observation_index(id TEXT PRIMARY KEY,source TEXT NOT NULL,listing TEXT NOT NULL,field TEXT NOT NULL,session TEXT NOT NULL,known_from TEXT)",
    "CREATE INDEX IF NOT EXISTS source_scope_lookup ON source_observation_index(source,listing,field,session,known_from)",
    "CREATE TABLE IF NOT EXISTS reference_dependency(child_kind TEXT NOT NULL,child_identity TEXT NOT NULL,child_digest TEXT NOT NULL,parent_kind TEXT NOT NULL,parent_identity TEXT NOT NULL,parent_digest TEXT NOT NULL,FOREIGN KEY(child_kind,child_identity) REFERENCES typed_reference(kind,identity),PRIMARY KEY(child_kind,child_identity,parent_kind,parent_identity,parent_digest))",
    "CREATE INDEX IF NOT EXISTS metadata_dependency_reverse ON reference_dependency(parent_kind,parent_identity)",
    "CREATE TABLE IF NOT EXISTS schema_version(id TEXT PRIMARY KEY,fingerprint TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS dataset_definition(id TEXT PRIMARY KEY,dataset TEXT NOT NULL,payload TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS dataset_version(id TEXT PRIMARY KEY,dataset TEXT NOT NULL,parent TEXT REFERENCES dataset_version(id),generation INTEGER NOT NULL,definition TEXT NOT NULL REFERENCES dataset_definition(id),payload TEXT NOT NULL,digest TEXT NOT NULL,UNIQUE(dataset,generation))",
    "CREATE TABLE IF NOT EXISTS physical_file(id TEXT PRIMARY KEY,payload TEXT NOT NULL,digest TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS partition_reference(version TEXT REFERENCES dataset_version(id) NOT NULL,partition TEXT NOT NULL,file TEXT REFERENCES physical_file(id) NOT NULL,PRIMARY KEY(version,partition))",
    "CREATE TABLE IF NOT EXISTS commit_operation(id TEXT PRIMARY KEY,input_digest TEXT NOT NULL,version TEXT NOT NULL REFERENCES dataset_version(id))",
    "CREATE TABLE IF NOT EXISTS dataset_dependency(version TEXT NOT NULL REFERENCES dataset_version(id),kind TEXT NOT NULL,identity TEXT NOT NULL,digest TEXT NOT NULL,PRIMARY KEY(version,kind,identity,digest))",
    "CREATE INDEX IF NOT EXISTS dependency_reverse ON dataset_dependency(kind,identity,version)",
    "CREATE TABLE IF NOT EXISTS version_selection_event(sequence INTEGER PRIMARY KEY AUTOINCREMENT,dataset TEXT NOT NULL,version TEXT NOT NULL REFERENCES dataset_version(id),reason TEXT NOT NULL,at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS typed_reference(kind TEXT NOT NULL,identity TEXT NOT NULL,payload TEXT NOT NULL,digest TEXT NOT NULL,known_from TEXT,PRIMARY KEY(kind,identity))",
    "CREATE TABLE IF NOT EXISTS catalog_schema(version TEXT PRIMARY KEY)",
)
TABLES = (
    "comparison_scope",
    "source_observation_index",
    "reference_dependency",
    "schema_version",
    "dataset_definition",
    "dataset_version",
    "physical_file",
    "partition_reference",
    "commit_operation",
    "dataset_dependency",
    "version_selection_event",
    "typed_reference",
    "catalog_schema",
)


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def safe_ancestors(path: Path) -> None:
    if not path.is_absolute() or ".." in path.parts:
        raise StorageError("STORAGE_PATH_UNSAFE")
    for p in (*reversed(path.parents), path):
        if p.is_symlink():
            raise StorageError("STORAGE_LINK_ESCAPE")


def safe_fd(root: Path, name: str, flags: int) -> int:
    if not re.fullmatch(r"(objects|manifests)/[a-f0-9-]+\.(parquet|json)", name):
        raise StorageError("MANIFEST_PATH_UNSAFE")
    safe_ancestors(root)
    directory, leaf = name.split("/")
    parent = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        child = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        try:
            return os.open(f"/proc/self/fd/{child}/{leaf}", flags | os.O_NOFOLLOW, 0o600)
        finally:
            os.close(child)
    finally:
        os.close(parent)


class CanonicalStore:
    def __init__(self, root: Path, *, disposable_root: Path, read_only: bool = False) -> None:
        safe_ancestors(disposable_root)
        if (
            not root.is_absolute()
            or not root.is_relative_to(disposable_root)
            or not disposable_root.is_relative_to(Path("/work"))
        ):
            raise StorageError("OWNED_DISPOSABLE_STORAGE_REQUIRED")
        safe_ancestors(root)
        self.read_only = read_only
        if read_only and not root.is_dir():
            raise StorageError("UNKNOWN_STORAGE_ROOT")
        if not read_only:
            root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.root = root
        owner = root / "owner.json"
        if not owner.exists() and any(root.iterdir()):
            raise StorageError("STORAGE_OWNERSHIP_UNKNOWN")
        try:
            if read_only:
                raise FileExistsError
            with owner.open("x") as f:
                f.write('{"schema":"od10.disposable/v1"}')
        except FileExistsError:
            if owner.is_symlink() or owner.read_text() != '{"schema":"od10.disposable/v1"}':
                raise StorageError("STORAGE_OWNERSHIP_MISMATCH") from None
        for name in ("objects", "manifests", "staging", "catalog"):
            safe_ancestors(root / name)
            if not read_only:
                (root / name).mkdir(mode=0o700, exist_ok=True)
        path = root / "catalog/catalog.sqlite"
        safe_ancestors(path)
        self.engine = create_engine(
            ("sqlite:///" + str(path)) if read_only else "sqlite:///" + str(path),
            connect_args={"check_same_thread": False, "timeout": 15},
        )

        @event.listens_for(self.engine, "connect")
        def setup(con: Any, record: Any) -> None:
            con.execute("PRAGMA foreign_keys=ON")
            con.execute("PRAGMA busy_timeout=15000")
            con.execute("PRAGMA synchronous=FULL")
            if read_only:
                con.execute("PRAGMA query_only=ON")

        if read_only:
            with self.engine.connect() as con:
                if list(con.exec_driver_sql("SELECT version FROM catalog_schema").scalars()) != [
                    "od10.catalog/v1"
                ]:
                    raise StorageError("CATALOG_SCHEMA_UNSUPPORTED")
            return
        with self.transaction() as con:
            for ddl in DDL:
                con.exec_driver_sql(ddl)
            con.exec_driver_sql(
                "INSERT OR IGNORE INTO catalog_schema(version) VALUES ('od10.catalog/v1')"
            )
            if list(con.exec_driver_sql("SELECT version FROM catalog_schema").scalars()) != [
                "od10.catalog/v1"
            ]:
                raise StorageError("CATALOG_SCHEMA_UNSUPPORTED")
            for table in TABLES:
                for operation in ("UPDATE", "DELETE"):
                    con.exec_driver_sql(
                        f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_{operation} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT,'IMMUTABLE_HISTORY'); END"
                    )

    @contextmanager
    def transaction(self) -> Iterator[Connection]:
        if self.read_only:
            raise StorageError("READ_ONLY_CATALOG")
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

    def domain_registry(self) -> dict[str, str]:
        return dict(schema.DOMAINS)

    def operation_version(self, operation_id: str) -> str | None:
        with self.engine.connect() as con:
            return con.execute(
                text("SELECT version FROM commit_operation WHERE id=:id"), {"id": operation_id}
            ).scalar()

    def _read(self, name: str, limit: int = 256_000_000) -> bytes:
        try:
            fd = safe_fd(self.root, name, os.O_RDONLY)
            with os.fdopen(fd, "rb") as f:
                before = os.fstat(f.fileno())
                if (
                    not stat.S_ISREG(before.st_mode)
                    or before.st_nlink != 1
                    or before.st_size > limit
                ):
                    raise StorageError("MANIFEST_FILE_UNSAFE")
                raw = f.read(limit + 1)
                after = os.fstat(f.fileno())
            if (before.st_ino, before.st_size, before.st_mtime_ns, before.st_nlink) != (
                after.st_ino,
                after.st_size,
                after.st_mtime_ns,
                after.st_nlink,
            ) or len(raw) != before.st_size:
                raise StorageError("MANIFEST_INPUT_CHANGED")
            return raw
        except OSError as error:
            raise StorageError("MANIFEST_INTEGRITY_FAILURE") from error

    def _install(self, name: str, raw: bytes) -> None:
        fd = safe_fd(self.root, name, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "wb") as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        fsync_dir((self.root / name).parent)

    def verify_file(self, entry: dict[str, Any]) -> Any:
        return self._verified_file(entry)[0]

    def _verified_file(self, entry: dict[str, Any]) -> tuple[Any, bytes]:
        try:
            if (
                type(entry["row_count"]) is not int
                or not 1 <= entry["row_count"] <= 100000
                or type(entry["byte_length"]) is not int
                or not 1 <= entry["byte_length"] <= 256000000
                or not re.fullmatch(r"objects/[a-f0-9]{32}\.parquet", entry["relative_path"])
                or entry["file_id"] != entry["relative_path"].split("/")[1].split(".")[0]
                or not re.fullmatch(r"[a-f0-9]{64}", entry["sha256"])
            ):
                raise StorageError("MANIFEST_FILE_CONTRACT")
            raw = self._read(entry["relative_path"])
            if len(raw) != entry["byte_length"] or digest(raw) != entry["sha256"]:
                raise StorageError("MANIFEST_INTEGRITY_FAILURE")
            table = pq.read_table(pa.BufferReader(raw))
            version = (table.schema.metadata or {}).get(b"canonical_schema", b"").decode()
            if (
                table.num_rows != entry["row_count"]
                or schema.schema_fingerprint(version) != entry["schema_fingerprint"]
                or not table.schema.equals(schema.get_schema(version), check_metadata=True)
            ):
                raise StorageError("MANIFEST_SCHEMA_OR_ROW_COUNT")
            rows = schema.from_table(table)
            partitions = {
                r.exchange + "/" + r.trade_date.strftime("%Y-%m") for r in rows if r.exchange
            }
            known = [
                r.known_from.astimezone(UTC).isoformat() for r in rows if r.known_from is not None
            ]
            expected = {
                "minimum_trade_date": min(r.trade_date for r in rows).isoformat(),
                "maximum_trade_date": max(r.trade_date for r in rows).isoformat(),
                "minimum_known_from": min(known) if known else None,
                "maximum_known_from": max(known) if known else None,
                "content_classification": "NON_MARKET_STRUCTURAL_CONTROL",
                "compression": "zstd",
            }
            parquet = pq.ParquetFile(pa.BufferReader(raw))
            compressions = {
                parquet.metadata.row_group(g).column(c).compression.lower()
                for g in range(parquet.metadata.num_row_groups)
                for c in range(parquet.metadata.num_columns)
            }
            if (
                partitions != {entry["partition_identity"]}
                or compressions != {"zstd"}
                or any(entry[k] != v for k, v in expected.items())
                or any(
                    r.observation_classification != expected["content_classification"] for r in rows
                )
            ):
                raise StorageError("MANIFEST_SEMANTIC_MISMATCH")
            return table, raw
        except (pa.ArrowException, KeyError, ValueError, TypeError) as error:
            if isinstance(error, StorageError):
                raise
            raise StorageError("MANIFEST_INTEGRITY_FAILURE") from error

    def manifest(self, version: str) -> dict[str, Any]:
        with self.engine.connect() as con:
            row = con.execute(
                text("SELECT payload,digest FROM dataset_version WHERE id=:id"), {"id": version}
            ).first()
        if row is None:
            raise StorageError("UNKNOWN_DATASET_VERSION")
        if digest(row[0].encode()) != row[1]:
            raise StorageError("MANIFEST_INTEGRITY_FAILURE")
        m = json.loads(row[0])
        if not isinstance(m, dict):
            raise StorageError("MANIFEST_CONTRACT")
        raw = self._read(m["manifest_relative_path"], 8_000_000)
        if raw != row[0].encode():
            raise StorageError("MANIFEST_INTEGRITY_FAILURE")
        return m

    def verify(self, version: str, *, _captured: dict[str, bytes] | None = None) -> dict[str, Any]:
        m = self.manifest(version)
        seen = set()
        rows = 0
        if m["dataset_version_id"] != version or m["storage_commit_state"] != "STORAGE_COMMITTED":
            raise StorageError("MANIFEST_VERSION_MISMATCH")
        for e in m["file_entries"]:
            if e["partition_identity"] in seen or e["dataset_version_id"] != version:
                raise StorageError("DUPLICATE_PARTITION")
            seen.add(e["partition_identity"])
            table, raw = self._verified_file(e)
            rows += table.num_rows
            if _captured is not None:
                _captured[e["relative_path"]] = raw
        if rows != m["total_rows"] or len(seen) != m["total_partitions"]:
            raise StorageError("MANIFEST_ACCOUNTING")
        return {
            "verified": True,
            "rows": rows,
            "partitions": len(seen),
            "manifest_digest": fingerprint(m),
        }

    def commit(
        self,
        definition: DatasetDefinition,
        rows: tuple[Observation, ...],
        *,
        operation_id: str,
        parent_version: str | None = None,
        expected_partitions: tuple[str, ...],
        hook: Callable[[str], None] | None = None,
        proofs: tuple[Any, ...] = (),
    ) -> str:
        if self.read_only:
            raise StorageError("READ_ONLY_CATALOG")
        token(operation_id)
        schema.get_schema(definition.schema_version)
        if (
            definition.domain not in schema.DOMAINS
            or schema.DOMAINS[definition.domain] != "PARQUET_DATASET"
        ):
            raise StorageError("DOMAIN_STORAGE_MISMATCH")
        if (definition.domain == "adjustment_results") != (definition.layer == "DERIVED"):
            raise StorageError("DOMAIN_LAYER_MISMATCH")
        if type(rows) is not tuple or not 1 <= len(rows) <= 100000:
            raise StorageError("WRITE_RESOURCE_LIMIT")
        if len({r.observation_revision_id for r in rows}) != len(rows):
            raise StorageError("DUPLICATE_OBSERVATION_REVISION")
        rows = tuple(sorted(rows, key=lambda r: r.observation_revision_id))
        for r in rows:
            if (
                r.source_rights_state != "NON_MARKET_CONTROL"
                or r.observation_classification != "NON_MARKET_STRUCTURAL_CONTROL"
            ):
                raise StorageError("SOURCE_SCOPE_BLOCKED")
            if (
                r.source_id not in definition.source_scope
                or r.price_basis != definition.price_basis
                or r.consumer_profile != definition.consumer_profile
            ):
                raise StorageError("SOURCE_OR_BASIS_SCOPE")
            adjusted = (
                (r.volume_basis not in {None, "RAW"})
                if r.field_semantics == "VOLUME"
                else r.price_basis != "RAW_UNADJUSTED"
            )
            if (definition.layer == "DERIVED") != adjusted:
                raise StorageError("RAW_DERIVED_SEPARATION")
            if r.field_semantics == "VOLUME" and definition.volume_basis != r.volume_basis:
                raise StorageError("VOLUME_BASIS_MISMATCH")
            if definition.layer == "DERIVED":
                from omegadata.canonical_storage.admission import admit_derived

                matching = [
                    p for p in proofs if p.source_observation.observation_id == r.observation_id
                ]
                if len(matching) != 1:
                    raise StorageError("DERIVED_BOUND_PROOF_REQUIRED")
                admit_derived(r, matching[0])
                proof = matching[0]
                self.pin_domain(
                    "adjustment_results",
                    proof.payload.output_digest,
                    proof.payload,
                    r.known_from,
                    context=proof,
                )
        request = fingerprint((definition, rows, operation_id, parent_version, expected_partitions))
        version = uuid.uuid4().hex

        def fault(at: str) -> None:
            if hook:
                hook(at)

        with self.engine.connect() as con:
            old = con.execute(
                text("SELECT input_digest,version FROM commit_operation WHERE id=:id"),
                {"id": operation_id},
            ).first()
        if old:
            if old[0] != request:
                raise StorageError("OPERATION_ID_CONTENT_CHANGED")
            self.verify(old[1])
            return str(old[1])
        parts: dict[str, list[Observation]] = {}
        for r in rows:
            if r.exchange is None:
                raise StorageError("PARTITION_IDENTITY_UNKNOWN")
            key = r.exchange + "/" + r.trade_date.strftime("%Y-%m")
            parts.setdefault(key, []).append(r)
        if (
            type(expected_partitions) is not tuple
            or len(set(expected_partitions)) != len(expected_partitions)
            or set(parts) != set(expected_partitions)
            or len(parts) > 64
        ):
            raise StorageError("PARTITION_ACCOUNTING")
        attempt = self.root / "staging" / uuid.uuid4().hex
        attempt.mkdir(mode=0o700)
        staged = []
        fault("before_write")
        for i, (partition, subset) in enumerate(sorted(parts.items())):
            table = schema.to_table(tuple(subset), definition.schema_version)
            p = attempt / (str(i) + ".parquet")
            with p.open("xb") as f:
                f.write(b"PAR1")
                f.flush()
                fault("during_file_write")
            pq.write_table(
                table, p, compression="zstd", row_group_size=8192, version="2.6", store_schema=True
            )
            with p.open("rb") as verify_stream:
                os.fsync(verify_stream.fileno())
            fault("after_file_write_before_validation")
            raw = p.read_bytes()
            decoded = schema.from_table(pq.read_table(pa.BufferReader(raw)))
            if decoded != tuple(subset):
                raise StorageError("STAGED_ROUNDTRIP_MISMATCH")
            path = "objects/" + uuid.uuid4().hex + ".parquet"
            known = [
                r.known_from.astimezone(UTC).isoformat() for r in subset if r.known_from is not None
            ]
            entry = {
                "file_id": path.split("/")[1].split(".")[0],
                "relative_path": path,
                "sha256": digest(raw),
                "byte_length": len(raw),
                "row_count": len(subset),
                "schema_fingerprint": schema.schema_fingerprint(definition.schema_version),
                "partition_identity": partition,
                "dataset_version_id": version,
                "minimum_trade_date": min(r.trade_date for r in subset).isoformat(),
                "maximum_trade_date": max(r.trade_date for r in subset).isoformat(),
                "minimum_known_from": min(known) if known else None,
                "maximum_known_from": max(known) if known else None,
                "compression": "zstd",
                "writer_version": "pyarrow/" + pa.__version__ + "/od10/v1",
                "content_classification": "NON_MARKET_STRUCTURAL_CONTROL",
            }
            staged.append((entry, raw))
        fault("after_validation_before_install")
        with self.transaction() as con:
            old = con.execute(
                text("SELECT input_digest,version FROM commit_operation WHERE id=:id"),
                {"id": operation_id},
            ).first()
            if old:
                if old[0] != request:
                    raise StorageError("OPERATION_ID_CONTENT_CHANGED")
                return str(old[1])
            parent = con.execute(
                text(
                    "SELECT id,generation FROM dataset_version WHERE dataset=:d ORDER BY generation DESC LIMIT 1"
                ),
                {"d": definition.dataset_id},
            ).first()
            if (str(parent[0]) if parent else None) != parent_version:
                raise StorageError("COMPETING_PARENT_VERSION")
            if parent_version:
                self.verify(parent_version)
                prior = self.manifest(parent_version)
                original = {
                    r.observation_revision_id: r
                    for e in prior["file_entries"]
                    for r in schema.from_table(self.verify_file(e))
                }
                for r in rows:
                    if r.supersedes_revision_id:
                        previous = original.get(r.supersedes_revision_id)
                        if (
                            previous is None
                            or previous.observation_id != r.observation_id
                            or previous.known_from is None
                            or r.known_from is None
                            or r.known_from <= previous.known_from
                        ):
                            raise StorageError("REVISION_LINEAGE_INVALID")
            for entry, raw in staged:
                self._install(entry["relative_path"], raw)
                self.verify_file(entry)
            fault("after_install_before_catalog_commit")
            deps = sorted({v for r in rows for v in r.lineage})
            m = {
                "dataset_version_id": version,
                "parent_dataset_version_id": parent_version,
                "dataset_id": definition.dataset_id,
                "domain": definition.domain,
                "layer": definition.layer,
                "schema_version": definition.schema_version,
                "schema_fingerprint": schema.schema_fingerprint(definition.schema_version),
                "partitioning_version": definition.partitioning_version,
                "writer_version": "pyarrow/" + pa.__version__ + "/od10/v1",
                "manifest_relative_path": "manifests/" + uuid.uuid4().hex + ".json",
                "manifest_version": "od10.manifest/v1",
                "source_scope": list(definition.source_scope),
                "price_basis": definition.price_basis,
                "consumer_profile": definition.consumer_profile,
                "volume_basis": definition.volume_basis,
                "valid_time_scope": [
                    min(r.trade_date for r in rows).isoformat(),
                    max(r.trade_date for r in rows).isoformat(),
                ],
                "file_entries": [e for e, raw in staged],
                "total_rows": len(rows),
                "total_partitions": len(staged),
                "upstream_references": [list(v) for v in deps],
                "source_rights_state": "NON_MARKET_CONTROL",
                "coverage_state": definition.coverage_state,
                "dependency_coverage_state": "UNKNOWN"
                if deps
                else "COMPLETE_FOR_DECLARED_NON_MARKET_SCOPE",
                "anomaly_state": "UNVERIFIED",
                "financial_acceptance_state": "BLOCKED_REAL_DATA",
                "publication_state": "NOT_AUTHORIZED",
                "storage_commit_state": "STORAGE_COMMITTED",
                "commit_operation_id": operation_id,
            }
            payload = canonical(m)
            self._install(m["manifest_relative_path"], payload.encode())
            sd = schema.schema_fingerprint(definition.schema_version)
            con.execute(
                text("INSERT OR IGNORE INTO schema_version VALUES (:id,:f)"),
                {"id": definition.schema_version, "f": sd},
            )
            actual = con.execute(
                text("SELECT fingerprint FROM schema_version WHERE id=:id"),
                {"id": definition.schema_version},
            ).scalar()
            if actual != sd:
                raise StorageError("SCHEMA_FINGERPRINT_MISMATCH")
            dd = fingerprint(definition)
            con.execute(
                text("INSERT OR IGNORE INTO dataset_definition VALUES (:id,:d,:p)"),
                {"id": dd, "d": definition.dataset_id, "p": canonical(asdict(definition))},
            )
            con.execute(
                text("INSERT INTO dataset_version VALUES (:id,:d,:parent,:g,:definition,:p,:h)"),
                {
                    "id": version,
                    "d": definition.dataset_id,
                    "parent": parent_version,
                    "g": parent[1] + 1 if parent else 1,
                    "definition": dd,
                    "p": payload,
                    "h": digest(payload.encode()),
                },
            )
            for e, _raw in staged:
                con.execute(
                    text("INSERT INTO physical_file VALUES (:id,:p,:h)"),
                    {"id": e["file_id"], "p": canonical(e), "h": e["sha256"]},
                )
                con.execute(
                    text("INSERT INTO partition_reference VALUES (:v,:p,:f)"),
                    {"v": version, "p": e["partition_identity"], "f": e["file_id"]},
                )
            for kind, identity, h in deps:
                con.execute(
                    text("INSERT INTO dataset_dependency VALUES (:v,:k,:i,:h)"),
                    {"v": version, "k": kind, "i": identity, "h": h},
                )
            con.execute(
                text("INSERT INTO commit_operation VALUES (:id,:h,:v)"),
                {"id": operation_id, "h": request, "v": version},
            )
            fault("during_catalog_transaction")
        fault("after_catalog_commit_before_acknowledgement")
        self.verify(version)
        return version

    def query(self, query: Query) -> QueryResult:
        from omegadata.canonical_storage.query import query_dataset

        return query_dataset(self, query)

    def select_version(self, dataset: str, version: str, reason: str, at: datetime) -> None:
        timestamp(at)
        token(reason)
        self.verify(version)
        if self.manifest(version)["dataset_id"] != dataset:
            raise StorageError("VERSION_SELECTION_SCOPE")
        with self.transaction() as con:
            con.execute(
                text(
                    "INSERT INTO version_selection_event(dataset,version,reason,at) VALUES (:d,:v,:r,:t)"
                ),
                {"d": dataset, "v": version, "r": reason, "t": at.isoformat()},
            )

    def selected_version(self, dataset: str) -> str | None:
        with self.engine.connect() as con:
            return con.execute(
                text(
                    "SELECT version FROM version_selection_event WHERE dataset=:d ORDER BY sequence DESC LIMIT 1"
                ),
                {"d": dataset},
            ).scalar()

    def convert_version(self, old: str, new_schema: str, operation_id: str) -> str:
        m = self.manifest(old)
        schema.classify_change(m["schema_version"], new_schema)
        rows = tuple(
            replace(r, canonical_schema_version=new_schema)
            for e in m["file_entries"]
            for r in schema.from_table(self.verify_file(e))
        )
        definition = DatasetDefinition(
            m["dataset_id"],
            m["domain"],
            m["layer"],
            new_schema,
            m["price_basis"],
            m["consumer_profile"],
            tuple(m["source_scope"]),
            m["coverage_state"],
        )
        return self.commit(
            definition,
            rows,
            operation_id=operation_id,
            parent_version=old,
            expected_partitions=tuple(e["partition_identity"] for e in m["file_entries"]),
        )

    def impact(
        self, kind: str, identity: str, known_at: datetime, *, maximum_nodes: int = 10000
    ) -> dict[str, Any]:
        timestamp(known_at)
        if known_at is None or type(maximum_nodes) is not int or not 1 <= maximum_nodes <= 10000:
            raise StorageError("DEPENDENCY_RESOURCE_LIMIT")
        pending = [(kind, identity)]
        seen = set()
        versions = set()
        with self.engine.connect() as con:
            while pending:
                node = pending.pop()
                if node in seen:
                    continue
                seen.add(node)
                if len(seen) > maximum_nodes:
                    raise StorageError("DEPENDENCY_RESOURCE_LIMIT")
                found = (
                    con.execute(
                        text(
                            "SELECT DISTINCT version FROM dataset_dependency WHERE kind=:k AND identity=:i LIMIT :n"
                        ),
                        {"k": node[0], "i": node[1], "n": maximum_nodes + 1},
                    )
                    .scalars()
                    .all()
                )
                if len(found) > maximum_nodes:
                    raise StorageError("DEPENDENCY_RESOURCE_LIMIT")
                for v in found:
                    m = self.manifest(v)
                    known = [
                        e["minimum_known_from"]
                        for e in m["file_entries"]
                        if e["minimum_known_from"]
                    ]
                    if known and min(datetime.fromisoformat(t) for t in known) <= known_at:
                        versions.add(v)
                children = con.execute(
                    text(
                        "SELECT d.child_kind,d.child_identity,r.known_from FROM reference_dependency d JOIN typed_reference r ON r.kind=d.child_kind AND r.identity=d.child_identity WHERE d.parent_kind=:k AND d.parent_identity=:i LIMIT :n"
                    ),
                    {"k": node[0], "i": node[1], "n": maximum_nodes + 1},
                ).fetchall()
                if len(children) > maximum_nodes:
                    raise StorageError("DEPENDENCY_RESOURCE_LIMIT")
                pending.extend(
                    (r[0], r[1])
                    for r in children
                    if r[2] is not None and datetime.fromisoformat(r[2]) <= known_at
                )
        return {
            "dataset_versions": sorted(versions),
            "visited_reference_nodes": len(seen),
            "coverage_state": "DEPENDENCY_UNKNOWN",
            "classification": "ALL_REGISTERED_HISTORY_RETAINED",
            "automatic_reprocess": False,
        }

    def orphans(self) -> dict[str, Any]:
        with self.engine.connect() as con:
            committed = {
                json.loads(v)["relative_path"]
                for v in con.execute(text("SELECT payload FROM physical_file")).scalars()
            }
            manifests = {
                json.loads(v)["manifest_relative_path"]
                for v in con.execute(text("SELECT payload FROM dataset_version")).scalars()
            }
        objects = {p.relative_to(self.root).as_posix() for p in (self.root / "objects").iterdir()}
        ms = {p.relative_to(self.root).as_posix() for p in (self.root / "manifests").iterdir()}
        return {
            "uncommitted_objects": sorted(objects - committed),
            "uncommitted_manifests": sorted(ms - manifests),
            "attempts": sorted(p.name for p in (self.root / "staging").iterdir()),
            "promotion": "NEVER_AUTOMATIC",
            "cleanup_performed": False,
        }

    def pin_domain(
        self,
        domain: str,
        identity: str,
        payload: Any,
        known_from: datetime | None,
        *,
        context: Any = None,
        dependencies: tuple[tuple[str, str, str], ...] = (),
    ) -> tuple[str, str, str]:
        from omegadata.canonical_storage.admission import (
            ProvenanceLedger,
            code_only_payload_admission,
        )
        from omegadata.universe.repository import encode

        code_only_payload_admission(payload, context)

        if len(dependencies) > 128 or len(set(dependencies)) != len(dependencies):
            raise StorageError("DEPENDENCY_RESOURCE_LIMIT")
        if domain == "reconciliation_results":
            from omegadata.reconciliation.engine import reconcile_context

            if not isinstance(context, tuple) or len(context) != 2:
                raise StorageError("COMPARISON_CONTEXT_REQUIRED")
            scope_id, comparison = context
            replay = reconcile_context(comparison)
            self.admit_comparison_scope(scope_id, comparison, replay, complete=True)
            if payload not in replay:
                raise StorageError("RECONCILIATION_REPLAY_MISMATCH")
        ref = ProvenanceLedger().pin(domain, identity, payload, known_from, context=context)
        body = canonical(
            {
                "payload": encode(payload),
                "context": encode(context),
                "known_from": known_from.isoformat() if known_from is not None else None,
                "dependencies": encode(tuple(sorted(dependencies))),
                "financial_acceptance": "NOT_AUTHORIZED",
                "version": "od10.reference/v1",
            }
        )
        ref = (domain, identity, digest(body.encode()))
        with self.transaction() as con:
            old = con.execute(
                text("SELECT payload,digest FROM typed_reference WHERE kind=:k AND identity=:i"),
                {"k": domain, "i": identity},
            ).first()
            if old:
                if old[0] != body or old[1] != ref[2]:
                    raise StorageError("IMMUTABLE_UPSTREAM_ID")
            else:
                con.execute(
                    text("INSERT INTO typed_reference VALUES (:k,:i,:p,:h,:t)"),
                    {
                        "k": domain,
                        "i": identity,
                        "p": body,
                        "h": ref[2],
                        "t": known_from.astimezone(UTC).isoformat()
                        if known_from is not None
                        else None,
                    },
                )
            from omegadata.reconciliation.contracts import Observation as SourceObservation

            if type(payload) is SourceObservation and domain == "source_observations":
                o = payload
                if o.observation_id != identity:
                    raise StorageError("SOURCE_OBSERVATION_IDENTITY")
                con.execute(
                    text(
                        "INSERT OR IGNORE INTO source_observation_index VALUES (:id,:s,:l,:f,:d,:k)"
                    ),
                    {
                        "id": o.observation_id,
                        "s": o.source_id,
                        "l": o.listing_id,
                        "f": o.field_name,
                        "d": o.session_date.isoformat(),
                        "k": o.availability.known_from.astimezone(UTC).isoformat()
                        if o.availability.known_from
                        else None,
                    },
                )
            for kind, parent, h in dependencies:
                if (kind, parent) == (domain, identity):
                    raise StorageError("DEPENDENCY_SELF_CYCLE")
                con.execute(
                    text("INSERT OR IGNORE INTO reference_dependency VALUES (:k,:i,:d,:p,:j,:h)"),
                    {"k": domain, "i": identity, "d": ref[2], "p": kind, "j": parent, "h": h},
                )
        return ref

    def read_domain(self, ref: tuple[str, str, str], known_at: datetime) -> Any:
        from omegadata.parsers.contracts import ParsedBar, ParseRequest, ParseResult
        from omegadata.reconciliation.repository import TYPES as reconciliation_types
        from omegadata.universe.repository import TYPES, decode

        timestamp(known_at)
        TYPES.update(reconciliation_types)
        for cls in (ParseResult, ParsedBar, ParseRequest):
            TYPES[cls.__name__] = cls
        with self.engine.connect() as con:
            row = con.execute(
                text(
                    "SELECT payload,digest,known_from FROM typed_reference WHERE kind=:k AND identity=:i"
                ),
                {"k": ref[0], "i": ref[1]},
            ).first()
        if row is None or row[1] != ref[2]:
            raise StorageError("UPSTREAM_PIN_MISSING_OR_CHANGED")
        if row[2] is None:
            raise StorageError("AVAILABILITY_UNKNOWN")
        if datetime.fromisoformat(row[2]) > known_at:
            raise StorageError("FUTURE_INFORMATION")
        body = json.loads(row[0])
        payload = decode(body["payload"])
        if digest(row[0].encode()) != ref[2]:
            raise StorageError("UPSTREAM_REFERENCE_INTEGRITY")
        return payload

    def query_join(
        self,
        *,
        query: Query,
        references: tuple[tuple[str, str, str], ...],
        join_key: str | None = None,
    ) -> dict[str, Any]:
        if len(references) > 1000 or len(set(references)) != len(references):
            raise StorageError("QUERY_RESOURCE_LIMIT")
        if join_key not in {None, "listing_id", "security_id"}:
            raise StorageError("QUERY_JOIN_KEY_UNSUPPORTED")
        rows = self.query(query)
        metadata = tuple(self.read_domain(ref, query.known_at) for ref in references)
        joined = []
        if join_key is not None:
            for row in rows.rows:
                key = row.get(join_key)
                matches = [
                    m for m in metadata if key is not None and getattr(m, join_key, None) == key
                ]
                joined.append(
                    {
                        "observation": row,
                        "metadata": matches[0] if len(matches) == 1 else tuple(matches),
                        "status": "MATCHED_UNVERIFIED"
                        if len(matches) == 1
                        else "AMBIGUOUS"
                        if matches
                        else "UNRESOLVED",
                    }
                )
        return {
            "rows": rows.rows,
            "joined": tuple(joined),
            "excluded": rows.excluded,
            "metadata": metadata,
            "join_mode": "EXPLICIT_IMMUTABLE_REFERENCE_CONTEXT",
            "financial_eligible": False,
        }

    def rollback_empty(self) -> None:
        with self.transaction() as con:
            if (
                any(
                    con.exec_driver_sql("SELECT count(*) FROM " + t).scalar()
                    for t in TABLES
                    if t != "catalog_schema"
                )
                or any((self.root / "objects").iterdir())
                or any((self.root / "manifests").iterdir())
            ):
                raise StorageError("NONEMPTY_ROLLBACK_REFUSED")
            for t in (
                "reference_dependency",
                "source_observation_index",
                "comparison_scope",
                "version_selection_event",
                "dataset_dependency",
                "commit_operation",
                "partition_reference",
                "typed_reference",
                "dataset_version",
                "physical_file",
                "dataset_definition",
                "schema_version",
                "catalog_schema",
            ):
                con.exec_driver_sql("DROP TABLE " + t)

    def pin_source_observations(self, rows: tuple[Any, ...]) -> None:
        from omegadata.reconciliation.contracts import Observation as SourceObservation

        for o in rows:
            if type(o) is not SourceObservation:
                raise StorageError("OBSERVATION_CONTRACT")
            self.pin_domain("source_observations", o.observation_id, o, o.availability.known_from)

    def pin_comparison_scope(self, scope: Any) -> None:
        from omegadata.canonical_storage.admission import ComparisonScope
        from omegadata.universe.repository import pack

        if type(scope) is not ComparisonScope:
            raise StorageError("COMPARISON_SCOPE_REQUIRED")
        body = pack(scope)
        h = fingerprint(scope)
        with self.transaction() as con:
            old = con.execute(
                text("SELECT payload FROM comparison_scope WHERE id=:id"), {"id": scope.scope_id}
            ).scalar()
            if old is not None and old != body:
                raise StorageError("IMMUTABLE_SCOPE_ID")
            con.execute(
                text("INSERT OR IGNORE INTO comparison_scope VALUES (:id,:p,:h)"),
                {"id": scope.scope_id, "p": body, "h": h},
            )

    def admit_comparison_scope(
        self, scope_id: str, context: Any, results: tuple[Any, ...], *, complete: bool
    ) -> Any:
        from sqlalchemy import bindparam

        from omegadata.canonical_storage.admission import (
            ComparisonScope,
            ProvenanceLedger,
            strict_comparison_admission,
        )
        from omegadata.universe.repository import TYPES, unpack

        TYPES["ComparisonScope"] = ComparisonScope
        with self.engine.connect() as con:
            stored = con.execute(
                text("SELECT payload,digest FROM comparison_scope WHERE id=:id"), {"id": scope_id}
            ).first()
            if stored is None:
                raise StorageError("COMPARISON_SCOPE_MISSING")
            scope = unpack(stored[0])
            if fingerprint(scope) != stored[1]:
                raise StorageError("COMPARISON_SCOPE_INTEGRITY")
            stmt = text(
                "SELECT i.id,r.payload FROM source_observation_index i JOIN typed_reference r ON r.kind=:kind AND r.identity=i.id WHERE i.source IN :sources AND i.listing IN :listings AND i.field IN :fields AND i.session>=:start AND i.session<:end AND (i.known_from IS NULL OR i.known_from<=:cutoff) LIMIT 10001"
            ).bindparams(
                bindparam("sources", expanding=True),
                bindparam("listings", expanding=True),
                bindparam("fields", expanding=True),
            )
            found = con.execute(
                stmt,
                {
                    "kind": "source_observations",
                    "sources": scope.source_ids,
                    "listings": scope.listing_ids,
                    "fields": scope.field_names,
                    "start": scope.session_from.isoformat(),
                    "end": scope.session_to.isoformat(),
                    "cutoff": context.known_at.astimezone(UTC).isoformat(),
                },
            ).fetchall()
        if len(found) > 10000:
            raise StorageError("COMPARISON_SCOPE_RESOURCE_LIMIT")
        ledger = ProvenanceLedger()
        from omegadata.reconciliation.repository import TYPES as registered
        from omegadata.universe.repository import decode

        TYPES.update(registered)
        ledger.pin_observations(tuple(decode(json.loads(row[1])["payload"]) for row in found))
        return strict_comparison_admission(scope, context, results, ledger, complete=complete)
