"""Pinned Arrow types; exact coefficient/exponent fallback, never silent rounding."""

from __future__ import annotations

import hashlib
from dataclasses import fields
from datetime import UTC
from decimal import Decimal
from typing import Any

import pyarrow as pa  # type: ignore[import-untyped]

from omegadata.canonical_storage.contracts import Observation, StorageError

DOMAINS = {
    n: (
        "PARQUET_DATASET"
        if n in {"source_observations", "adjustment_results"}
        else "TRANSACTIONAL_METADATA"
    )
    for n in (
        "source_observations",
        "instrument_identity_revisions",
        "listing_lifecycle",
        "session_calendar",
        "corporate_action_revisions",
        "adjustment_results",
        "universe_membership_revisions",
        "universe_snapshots",
        "universe_member_decisions",
        "reconciliation_results",
        "anomaly_records",
        "review_revisions",
        "correction_revisions",
        "reprocess_requests",
        "reprocess_completions",
    )
}
TIME = {"known_from", "known_to", "observed_at", "published_at", "ingested_at"}
DATES = {"trade_date", "session_date", "economic_valid_from", "economic_valid_to"}
BOOL = {"financial_eligibility", "publication_eligibility", "execution_eligibility"}


def encode_decimal(value: Decimal | None, kind: str = "RAW") -> dict[str, Any]:
    if value is None:
        return {"coefficient": None, "exponent": None, "fixed": None, "encoding": "NULL"}
    if type(value) is not Decimal or not value.is_finite():
        raise StorageError("NUMERIC_INVALID")
    sign, digits, exponent = value.as_tuple()
    exp = int(exponent)
    if len(digits) > 1000 or not -9999 <= exp <= 9999:
        raise StorageError("PRECISION_RESOURCE_LIMIT")
    coefficient = ("-" if sign else "") + "".join(str(v) for v in digits)
    p, s = (38, 12) if kind == "RAW" else (76, 36)
    # Validate exact rescaling by digit arithmetic, independently of ambient Decimal context.
    scaled = len(digits) + exp + s
    fractional_ok = exp >= -s or all(v == 0 for v in digits[len(digits) + exp + s :])
    fits = (
        not any(digits)
        or fractional_ok
        and scaled <= p
        and (exp + s >= 0 or len(digits) + exp + s >= 0)
    )
    if kind not in {"RAW", "CALCULATION"}:
        raise StorageError("NUMERIC_KIND")
    if kind == "RAW" and not fits:
        raise StorageError("STORAGE_PRECISION_UNSUPPORTED")
    return {
        "coefficient": coefficient,
        "exponent": exp,
        "fixed": value if fits else None,
        "encoding": "COEFFICIENT_EXPONENT/v1",
    }


def decode_decimal(value: dict[str, Any]) -> Decimal | None:
    c = value["coefficient"]
    if c is None:
        return None
    sign = int(c.startswith("-"))
    digits = c[1:] if sign else c
    return Decimal((sign, tuple(int(v) for v in digits), value["exponent"]))


def get_schema(version: str) -> Any:
    if version not in {"canonical/v1", "canonical/v2"}:
        raise StorageError("SCHEMA_VERSION_UNSUPPORTED")
    result = []
    for f in fields(Observation):
        n = f.name
        if n == "value" or n == "source_note" and version == "canonical/v1":
            continue
        t = (
            pa.timestamp("us", tz="UTC")
            if n in TIME
            else pa.date32()
            if n in DATES
            else pa.bool_()
            if n in BOOL
            else pa.int64()
            if n == "source_row_ordinal"
            else pa.list_(pa.field("element", pa.string()))
            if n == "hard_block_reasons"
            else pa.list_(
                pa.field(
                    "element",
                    pa.struct(
                        [("kind", pa.string()), ("identity", pa.string()), ("digest", pa.string())]
                    ),
                )
            )
            if n == "lineage"
            else pa.string()
        )
        result.append(
            pa.field(
                n,
                t,
                nullable=n
                not in {
                    "observation_id",
                    "observation_revision_id",
                    "source_id",
                    "source_artifact_identity",
                    "source_record_identity",
                    "trade_date",
                    "session_date",
                    "field_semantics",
                    "value_state",
                    "numeric_kind",
                },
            )
        )
    result.extend(
        [
            pa.field("value_coefficient", pa.string()),
            pa.field("value_exponent", pa.int16()),
            pa.field("value_fixed", pa.decimal128(38, 12)),
            pa.field("factor_fixed", pa.decimal256(76, 36)),
            pa.field("value_encoding", pa.string(), nullable=False),
        ]
    )
    return pa.schema(
        result,
        metadata={
            b"canonical_schema": version.encode(),
            b"financial_acceptance": b"NOT_AUTHORIZED",
        },
    )


def schema_fingerprint(version: str) -> str:
    return hashlib.sha256(get_schema(version).serialize().to_pybytes()).hexdigest()


def to_table(rows: tuple[Observation, ...], version: str) -> Any:
    schema = get_schema(version)
    out = []
    for r in rows:
        if type(r) is not Observation or r.canonical_schema_version != version:
            raise StorageError("SCHEMA_RECORD_MISMATCH")
        d = {f.name: getattr(r, f.name) for f in fields(r) if f.name in schema.names}
        d["lineage"] = [
            dict(zip(("kind", "identity", "digest"), v, strict=True)) for v in r.lineage
        ]
        for n in TIME:
            if d[n] is not None:
                d[n] = d[n].astimezone(UTC)
        scalar = encode_decimal(r.value, r.numeric_kind)
        d.update(
            value_coefficient=scalar["coefficient"],
            value_exponent=scalar["exponent"],
            value_encoding=scalar["encoding"],
            value_fixed=scalar["fixed"] if r.numeric_kind == "RAW" else None,
            factor_fixed=scalar["fixed"] if r.numeric_kind == "CALCULATION" else None,
        )
        out.append(d)
    try:
        return pa.Table.from_pylist(out, schema=schema)
    except (pa.ArrowException, ValueError, OverflowError) as error:
        raise StorageError("STORAGE_PRECISION_OR_TYPE") from error


def from_table(table: Any) -> tuple[Observation, ...]:
    version = (table.schema.metadata or {}).get(b"canonical_schema", b"").decode()
    if not table.schema.equals(get_schema(version), check_metadata=True):
        raise StorageError("SCHEMA_FINGERPRINT_MISMATCH")
    result = []
    for raw in table.to_pylist():
        r = dict(raw)
        value = decode_decimal(
            {"coefficient": r.pop("value_coefficient"), "exponent": r.pop("value_exponent")}
        )
        encoding = r.pop("value_encoding")
        raw_fixed = r.pop("value_fixed")
        factor_fixed = r.pop("factor_fixed")
        check = encode_decimal(value, r["numeric_kind"])
        if (
            encoding != check["encoding"]
            or raw_fixed != (check["fixed"] if r["numeric_kind"] == "RAW" else None)
            or factor_fixed != (check["fixed"] if r["numeric_kind"] == "CALCULATION" else None)
        ):
            raise StorageError("SCALAR_PHYSICAL_RECONCILIATION")
        for n in BOOL:
            if r.pop(n) is not False:
                raise StorageError("FINANCIAL_PROMOTION_REFUSED")
        r["lineage"] = tuple((v["kind"], v["identity"], v["digest"]) for v in r["lineage"])
        r["hard_block_reasons"] = tuple(r["hard_block_reasons"])
        r["value"] = value
        observation = Observation(**r)
        # Re-encode the authoritative scalar representation; fixed fields cannot disagree.
        result.append(observation)
    return tuple(result)


def classify_change(before: str, after: str) -> str:
    get_schema(before)
    get_schema(after)
    if before == after:
        return "IDENTICAL"
    if (before, after) == ("canonical/v1", "canonical/v2"):
        return "BACKWARD_COMPATIBLE_ADDITION"
    raise StorageError("LOSSY_CONVERSION_REFUSED")
