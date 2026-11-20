"""Only non-market storage experiments; invoked after native boundary proof."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def run_process(config: dict[str, Any]) -> int:
    import od05x_isolated_runner as boundary

    boundary.assert_boundary()
    from decimal import Decimal

    from test_od10_canonical_storage import commit, database, query, record

    from omegadata.canonical_storage.contracts import StorageError

    output = Path("/work/job")
    output.mkdir()
    shared = Path("/work/shared")
    role = config["od10_role"]
    tick = time.monotonic()
    start = datetime.now(UTC).isoformat()
    if role["mode"] == "reader":
        from omegadata.canonical_storage.store import CanonicalStore

        db = CanonicalStore(shared / "store", disposable_root=shared, read_only=True)
    else:
        db = database(shared)
    result: dict[str, Any] = {
        "mode": role["mode"],
        "start_utc": start,
        "python": sys.version,
        "pid_in_namespace": os.getpid(),
        "boundary": boundary.assert_boundary(),
        "financial_observations": 0,
    }
    if role["mode"] == "initial":
        v = commit(db)
        (shared / "initial.json").write_text(json.dumps({"version": v, "manifest": db.manifest(v)}))
        result["version"] = v
    else:
        initial = json.loads((shared / "initial.json").read_bytes())
        v = initial["version"]
        if role["mode"] in {"attempt", "recover"}:

            def fault(at: str) -> None:
                if role["mode"] == "attempt" and at == role["phase"]:
                    (shared / "reached.json").write_text(
                        json.dumps(
                            {
                                "phase": at,
                                "original_verified": db.verify(v)["verified"],
                                "operation_visible": db.operation_version("process-interrupted"),
                            }
                        )
                    )
                    while True:
                        time.sleep(0.01)

            old = db.operation_version("process-interrupted")
            new = commit(db, op="process-interrupted", parent=v, hook=fault)
            result.update(
                old_version=v,
                new_version=new,
                retry_recognized=old == new,
                old_bytes_preserved=db.manifest(v) == initial["manifest"],
                old_query_rows=len(query(db, v).rows),
                new_query_rows=len(query(db, new).rows),
                orphans=db.orphans(),
            )
            if (
                result["old_query_rows"] != 1
                or result["new_query_rows"] != 1
                or not result["old_bytes_preserved"]
            ):
                raise ValueError("RECOVERY_NOT_REPRODUCIBLE")
        elif role["mode"] == "reader":
            result.update(
                old_rows=len(query(db, v).rows),
                operation_visible=db.operation_version("process-interrupted"),
                old_bytes_preserved=db.manifest(v) == initial["manifest"],
            )
            if result["old_rows"] != 1 or not result["old_bytes_preserved"]:
                raise ValueError("PARTIAL_READER_VISIBILITY")
        elif role["mode"] == "race":
            name = role["name"]
            (shared / ("ready-" + name + ".json")).write_text("{}")
            deadline = time.monotonic() + 30
            while not (shared / "go.json").exists():
                if time.monotonic() > deadline:
                    raise TimeoutError("CONTROL_BARRIER_TIMEOUT")
                time.sleep(0.01)
            try:
                r = (record(value=Decimal(role["value"])),)
                result["version"] = commit(db, r, role["operation"], v)
                result["outcome"] = "COMMITTED"
            except StorageError as error:
                result.update(outcome="REFUSED", reason=error.reason_code)
            result.update(old_bytes_preserved=db.manifest(v) == initial["manifest"])
    result.update(
        exit_code=0, end_utc=datetime.now(UTC).isoformat(), elapsed_seconds=time.monotonic() - tick
    )
    (output / "result.json").write_text(json.dumps(result, indent=2))
    db.close()
    return 0


def run(config: dict[str, Any]) -> int:
    import od05x_isolated_runner as boundary

    boundary.assert_boundary()
    output = Path("/work/job")
    output.mkdir()
    result = {
        "job": "od10perf",
        "exit_code": 0,
        "python": sys.version,
        "boundary": boundary.assert_boundary(),
        "duckdb_available": importlib.util.find_spec("duckdb") is not None,
        "scale_class": "NON_MARKET_BOOKKEEPING_ONLY",
        "financial_observations": 0,
        "measurements": [],
    }
    # A bounded scale ladder; actual results determine whether a larger tier is safe.
    import resource

    import pyarrow as pa
    from test_od10_canonical_storage import commit, database, query, record

    from omegadata.canonical_storage.query import aggregate_scalar

    for size in (1000, 10000, 100000):
        root = output / ("scale-" + str(size))
        root.mkdir()
        db = database(root)
        tick = time.perf_counter()
        rows = tuple(
            record(
                observation_id="control-" + str(i),
                observation_revision_id="revision-" + str(i),
                listing_id="CONTROL-" + str(i % 100),
            )
            for i in range(size)
        )
        build = time.perf_counter() - tick
        tick = time.perf_counter()
        version = commit(db, rows, "benchmark-" + str(size))
        write = time.perf_counter() - tick
        tick = time.perf_counter()
        check = db.verify(version)
        validation = time.perf_counter() - tick
        tick = time.perf_counter()
        out = query(db, version, listing_ids=("CONTROL-0",))
        latency = time.perf_counter() - tick
        expected = size // 100
        if len(out.rows) != expected or aggregate_scalar(out.rows)["sum_exact"] != (
            __import__("fractions").Fraction(5 * expected, 4).numerator,
            __import__("fractions").Fraction(5 * expected, 4).denominator,
        ):
            raise ValueError("INDEPENDENT_QUERY_ROWS_OR_VALUES")
        files = list((root / "store/objects").iterdir())
        bytes_on_disk = sum(p.stat().st_size for p in files)
        result["measurements"].append(
            {
                "records": size,
                "build_seconds": build,
                "write_and_commit_seconds": write,
                "verify_seconds": validation,
                "filtered_query_seconds": latency,
                "expected_filtered_rows": expected,
                "actual_filtered_rows": len(out.rows),
                "objects": len(files),
                "parquet_bytes": bytes_on_disk,
                "catalog_bytes": (root / "store/catalog/catalog.sqlite").stat().st_size,
                "maximum_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                "files_scanned": out.files_scanned,
                "files_verified": out.files_verified,
                "manifest_digest": check["manifest_digest"],
                "pyarrow": pa.__version__,
            }
        )
        db.close()
    (output / "result.json").write_text(json.dumps(result, indent=2))
    return 0


def detail(config: dict[str, Any]) -> int:
    """Bounded 1,000-row technology/metadata measurements, never financial replay."""
    import hashlib

    import od05x_isolated_runner as boundary
    import pyarrow as pa
    import pyarrow.parquet as pq
    from sqlalchemy import text
    from test_od10_canonical_storage import D, K, commit, database, query, record

    from omegadata.canonical_storage import schema
    from omegadata.canonical_storage.contracts import Query
    from omegadata.canonical_storage.store import CanonicalStore
    from omegadata.identity import Listing

    boundary.assert_boundary()
    output = Path("/work/job")
    output.mkdir()
    root = output / "detail"
    root.mkdir()
    db = database(root)
    rows = tuple(
        record(observation_id="control-" + str(i), observation_revision_id="revision-" + str(i))
        for i in range(1000)
    )

    def timed(call):
        tick = time.perf_counter()
        value = call()
        return value, time.perf_counter() - tick

    v, write = timed(lambda: commit(db, rows))
    manifest, manifest_seconds = timed(lambda: db.manifest(v))
    e = manifest["file_entries"][0]
    raw, read_seconds = timed(lambda: db._read(e["relative_path"]))
    _, checksum_seconds = timed(lambda: hashlib.sha256(raw).hexdigest())
    full, read_query = timed(lambda: query(db, v))
    assert len(full.rows) == 1000
    ref = db.pin_domain(
        "instrument_identity_revisions",
        "control-listing",
        Listing("00001", "control-security", "CANARY-X"),
        K,
    )
    joined, join_seconds = timed(
        lambda: db.query_join(
            query=Query(
                v, "control-dataset", D, D.replace(day=D.day + 1), K, "RAW_UNADJUSTED", "AUDIT"
            ),
            references=(ref,),
            join_key="listing_id",
        )
    )
    assert len(joined["joined"]) == 1000 and all(
        r["status"] == "MATCHED_UNVERIFIED" for r in joined["joined"]
    )
    converted, conversion = timed(
        lambda: db.convert_version(v, "canonical/v2", "schema-conversion")
    )
    db.close()
    db, restart = timed(
        lambda: CanonicalStore(root / "store", disposable_root=root, read_only=True)
    )
    restored, replay = timed(lambda: query(db, v))
    assert restored.rows == full.rows
    assert db.manifest(converted)["parent_dataset_version_id"] == v
    with db.engine.connect() as con:
        plans = [
            tuple(row)
            for row in con.execute(
                text(
                    "EXPLAIN QUERY PLAN SELECT version FROM dataset_dependency WHERE kind=:kind AND identity=:identity"
                ),
                {"kind": "source", "identity": "control"},
            ).fetchall()
        ]
    table = schema.to_table(rows, "canonical/v1")
    variants = []
    for compression in ("zstd", "snappy"):
        for group in (256, 8192):
            buf = pa.BufferOutputStream()
            _, elapsed = timed(
                lambda buf=buf, compression=compression, group=group: pq.write_table(
                    table, buf, compression=compression, row_group_size=group
                )
            )
            data = buf.getvalue()
            decoded = pq.read_table(pa.BufferReader(data))
            assert schema.from_table(decoded) == rows
            variants.append(
                {
                    "compression": compression,
                    "row_group_size": group,
                    "bytes": len(data),
                    "write_seconds": elapsed,
                    "logical_roundtrip": True,
                }
            )
    parquet = pq.ParquetFile(pa.BufferReader(raw))
    uncompressed = sum(
        parquet.metadata.row_group(g).total_byte_size
        for g in range(parquet.metadata.num_row_groups)
    )
    result = {
        "job": "od10detail",
        "exit_code": 0,
        "boundary": boundary.assert_boundary(),
        "financial_observations": 0,
        "records": 1000,
        "write_commit_seconds": write,
        "full_read_query_seconds": read_query,
        "read_rows_per_second": 1000 / read_query,
        "write_rows_per_second": 1000 / write,
        "manifest_seconds": manifest_seconds,
        "file_read_seconds": read_seconds,
        "checksum_seconds": checksum_seconds,
        "schema_conversion_seconds": conversion,
        "join_seconds": join_seconds,
        "restart_seconds": restart,
        "historical_replay_seconds": replay,
        "compression_ratio_uncompressed_to_file": uncompressed / len(raw),
        "variants": variants,
        "dependency_query_plan": plans,
        "catalog_bytes": (root / "store/catalog/catalog.sqlite").stat().st_size,
        "duckdb": "NOT_INSTALLED_NO_PROVISIONING",
        "atomicity_scope": "SQLITE_READER_VISIBILITY",
        "row_group_choice": "8192/zstd bounds small-file overhead; measured alternatives retained, no universal optimality claim",
    }
    (output / "result.json").write_text(json.dumps(result, indent=2))
    db.close()
    return 0
