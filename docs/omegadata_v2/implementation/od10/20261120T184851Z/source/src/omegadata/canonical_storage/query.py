"""Bounded Arrow scanning over catalog manifests only; no arbitrary SQL or paths."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date
from fractions import Fraction
from typing import Any

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.dataset as ds  # type: ignore[import-untyped]

from omegadata.canonical_storage import schema
from omegadata.canonical_storage.contracts import Query, QueryResult, StorageError


def query_dataset(store: Any, q: Query) -> QueryResult:
    if type(q) is not Query:
        raise StorageError("QUERY_CONTRACT")
    m = store.manifest(q.dataset_version_id)
    if m["dataset_id"] != q.dataset_id:
        raise StorageError("DATASET_SCOPE_MISMATCH")
    if m["price_basis"] != q.price_basis:
        raise StorageError("PRICE_BASIS_MISMATCH")
    if m["consumer_profile"] != q.consumer_profile or q.consumer_profile != "AUDIT":
        raise StorageError("SOURCE_SCOPE_BLOCKED")
    if len(m["file_entries"]) > q.maximum_files:
        raise StorageError("QUERY_RESOURCE_LIMIT")
    captured: dict[str, bytes] = {}
    store.verify(q.dataset_version_id, _captured=captured)
    rows = []
    excluded = []
    scanned = 0
    for e in m["file_entries"]:
        if (
            date.fromisoformat(e["maximum_trade_date"]) < q.valid_from
            or date.fromisoformat(e["minimum_trade_date"]) >= q.valid_to
        ):
            continue
        if q.exchange and not e["partition_identity"].startswith(q.exchange + "/"):
            continue
        raw = captured[e["relative_path"]]
        scanned += 1
        predicate = (ds.field("trade_date") >= pa.scalar(q.valid_from)) & (
            ds.field("trade_date") < pa.scalar(q.valid_to)
        )
        if q.exchange:
            predicate = predicate & (ds.field("exchange") == q.exchange)
        if q.security_ids is not None:
            predicate = predicate & ds.field("security_id").isin(q.security_ids)
        if q.listing_ids is not None:
            predicate = predicate & ds.field("listing_id").isin(q.listing_ids)
        # Row-group predicates operate on the exact bytes already fully integrity checked.
        # No path is reopened after verification; filesystem races cannot swap the fragment.
        fmt = ds.ParquetFileFormat()
        fragment = fmt.make_fragment(pa.BufferReader(raw))
        dataset = ds.FileSystemDataset([fragment], schema.get_schema(m["schema_version"]), fmt)
        selected = dataset.scanner(filter=predicate, use_threads=False).to_table()
        for r in schema.from_table(selected):
            reason = None
            if r.known_from is None:
                reason = "AVAILABILITY_UNKNOWN"
            elif (
                r.known_from > q.known_at
                or r.published_at is not None
                and r.published_at > q.known_at
                or r.observed_at is not None
                and r.observed_at > q.known_at
            ):
                reason = "FUTURE_INFORMATION"
            elif r.known_to is not None and q.known_at >= r.known_to:
                reason = "SUPERSEDED_KNOWLEDGE"
            if reason:
                excluded.append({"revision": r.observation_revision_id, "reason": reason})
                continue
            item = asdict(r)
            if q.columns is not None:
                if any(n not in item for n in q.columns):
                    raise StorageError("QUERY_PROJECTION_UNSUPPORTED")
                item = {n: item[n] for n in q.columns}
            rows.append(item)
            if len(rows) > q.maximum_rows:
                raise StorageError("QUERY_RESOURCE_LIMIT")
    return QueryResult(
        tuple(rows), tuple(excluded), scanned, len(m["file_entries"]), q.dataset_version_id
    )


def aggregate_scalar(rows: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    if len(rows) > 100000:
        raise StorageError("QUERY_RESOURCE_LIMIT")
    values = [Fraction(r["value"]) for r in rows if r.get("value") is not None]
    total = sum(values, Fraction(0))
    return {
        "count": len(values),
        "missing": len(rows) - len(values),
        "sum_exact": (total.numerator, total.denominator),
        "mean_exact": ((total / len(values)).numerator, (total / len(values)).denominator)
        if values
        else None,
    }
