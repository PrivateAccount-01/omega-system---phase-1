"""Explicit storage identities, semantics and resource limits. No financial promotion."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from omegadata.universe.repository import pack


class StorageError(ValueError):
    def __init__(self, reason_code: str):
        self.reason_code = reason_code
        super().__init__(reason_code)


def fingerprint(value: Any) -> str:
    return hashlib.sha256(pack(value).encode()).hexdigest()


def token(value: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,160}", value):
        raise StorageError("IDENTIFIER_UNSAFE")


def timestamp(value: datetime | None) -> None:
    if value is not None and (
        not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None
    ):
        raise StorageError("TIMESTAMP_TIMEZONE_REQUIRED")


@dataclass(frozen=True)
class Observation:
    observation_id: str
    observation_revision_id: str
    source_id: str
    source_artifact_identity: str
    source_record_identity: str
    trade_date: date
    session_date: date
    known_from: datetime | None
    field_semantics: str
    value: Decimal | None
    supersedes_revision_id: str | None = None
    publisher_identity: str | None = None
    source_row_ordinal: int | None = None
    parser_version: str | None = None
    schema_version: str | None = None
    canonical_schema_version: str = "canonical/v1"
    security_id: str | None = None
    listing_id: str | None = None
    exchange: str | None = None
    symbol_as_reported: str | None = None
    series_as_reported: str | None = None
    isin_as_reported_if_available: str | None = None
    observation_type: str = "NON_MARKET_CONTROL"
    observation_interval: str = "CONTROL"
    economic_valid_from: date | None = None
    economic_valid_to: date | None = None
    observed_at: datetime | None = None
    published_at: datetime | None = None
    known_to: datetime | None = None
    ingested_at: datetime | None = None
    currency: str | None = None
    price_unit: str | None = None
    volume_unit: str | None = None
    price_basis: str = "RAW_UNADJUSTED"
    volume_basis: str | None = None
    source_evidence_id: str | None = None
    source_rights_state: str = "UNKNOWN"
    source_authority_digest: str | None = None
    observation_classification: str = "UNVERIFIED_SOURCE"
    quality_state: str = "UNVERIFIED"
    hard_block_reasons: tuple[str, ...] = ("SOURCE_AUTHORITY_UNVERIFIED",)
    lineage: tuple[tuple[str, str, str], ...] = ()
    numeric_kind: str = "RAW"
    value_state: str = "PRESENT"
    rational_numerator: str | None = None
    rational_denominator: str | None = None
    consumer_profile: str = "AUDIT"
    source_note: str | None = None
    financial_eligibility: bool = field(default=False, init=False)
    publication_eligibility: bool = field(default=False, init=False)
    execution_eligibility: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        for v in (
            self.observation_id,
            self.observation_revision_id,
            self.source_id,
            self.source_artifact_identity,
            self.source_record_identity,
        ):
            token(v)
        for name in ("known_from", "known_to", "observed_at", "published_at", "ingested_at"):
            value = getattr(self, name)
            timestamp(value)
            if value is not None:
                object.__setattr__(self, name, value.astimezone(UTC))
        if type(self.hard_block_reasons) is not tuple or len(self.hard_block_reasons) > 64:
            raise StorageError("HARD_BLOCK_RESOURCE_LIMIT")
        reasons = set(self.hard_block_reasons)
        if self.security_id is None or self.listing_id is None:
            reasons.add("IDENTITY_UNRESOLVED")
        if self.known_from is None:
            reasons.add("AVAILABILITY_UNKNOWN")
        if self.observation_classification == "NON_MARKET_STRUCTURAL_CONTROL":
            reasons.add("NON_MARKET_CONTROL")
        if self.source_rights_state == "DENIED":
            reasons.add("SOURCE_RIGHTS_DENIED")
        object.__setattr__(self, "hard_block_reasons", tuple(sorted(reasons)))
        if type(self.trade_date) is not date or type(self.session_date) is not date:
            raise StorageError("DATE_SEMANTICS")
        if self.economic_valid_to and (
            self.economic_valid_from is None or self.economic_valid_to <= self.economic_valid_from
        ):
            raise StorageError("VALID_INTERVAL")
        if self.known_to and (self.known_from is None or self.known_to <= self.known_from):
            raise StorageError("KNOWLEDGE_INTERVAL")
        if self.field_semantics not in {
            "OPEN",
            "HIGH",
            "LOW",
            "CLOSE",
            "VOLUME",
            "TURNOVER",
            "REFERENCE_CLOSE",
            "SETTLEMENT_PRICE",
            "FACTOR",
            "CONTROL_SCALAR",
        }:
            raise StorageError("FIELD_SEMANTICS_UNKNOWN")
        semantic = {
            "RAW_CLOSE": "CLOSE",
            "RAW_OPEN": "OPEN",
            "SETTLEMENT_PRICE": "SETTLEMENT_PRICE",
        }
        if (
            self.observation_type in semantic
            and self.field_semantics != semantic[self.observation_type]
        ):
            raise StorageError("FIELD_SEMANTICS_MISMATCH")
        if self.numeric_kind not in {"RAW", "CALCULATION"} or self.value_state not in {
            "PRESENT",
            "MISSING",
            "UNAVAILABLE",
            "INVALID",
        }:
            raise StorageError("VALUE_STATE")
        if (self.value is None) != (self.value_state != "PRESENT"):
            raise StorageError("MISSING_VERSUS_ZERO")
        if self.field_semantics == "VOLUME" and self.value is not None and self.value < 0:
            raise StorageError("NEGATIVE_VOLUME")
        if self.value is not None and (
            type(self.value) is not Decimal or not self.value.is_finite()
        ):
            raise StorageError("NUMERIC_INVALID")
        if self.source_row_ordinal is not None and (
            type(self.source_row_ordinal) is not int or not 1 <= self.source_row_ordinal < 2**63
        ):
            raise StorageError("ROW_ORDINAL")
        if (
            type(self.lineage) is not tuple
            or len(self.lineage) > 128
            or len(set(self.lineage)) != len(self.lineage)
        ):
            raise StorageError("LINEAGE_INVALID")
        for kind, identity, digest in self.lineage:
            token(kind)
            token(identity)
            if not re.fullmatch("[a-f0-9]{64}", digest):
                raise StorageError("LINEAGE_DIGEST")
        if (self.rational_numerator is None) != (self.rational_denominator is None):
            raise StorageError("RATIONAL_PAIR")
        if self.rational_numerator is not None:
            for rational_term in (self.rational_numerator, self.rational_denominator):
                if rational_term is None or not re.fullmatch(
                    r"-?(0|[1-9][0-9]{0,999})", rational_term
                ):
                    raise StorageError("RATIONAL_RESOURCE_LIMIT")
            if int(self.rational_denominator or "0") <= 0:
                raise StorageError("RATIONAL_DENOMINATOR")


@dataclass(frozen=True)
class DatasetDefinition:
    dataset_id: str
    domain: str
    layer: str
    schema_version: str
    price_basis: str
    consumer_profile: str
    source_scope: tuple[str, ...]
    coverage_state: str = "UNKNOWN"
    partitioning_version: str = "exchange-month/v1"
    volume_basis: str | None = None

    def __post_init__(self) -> None:
        token(self.dataset_id)
        if self.layer not in {"RAW", "DERIVED"} or self.partitioning_version != "exchange-month/v1":
            raise StorageError("DATASET_CONTRACT")
        if self.coverage_state not in {
            "COMPLETE_FOR_DECLARED_NON_MARKET_SCOPE",
            "PARTIAL",
            "UNKNOWN",
            "SOURCE_BLOCKED",
        }:
            raise StorageError("COVERAGE_AUTHORITY_REQUIRED")


@dataclass(frozen=True)
class Query:
    dataset_version_id: str
    dataset_id: str
    valid_from: date
    valid_to: date
    known_at: datetime
    price_basis: str
    consumer_profile: str
    security_ids: tuple[str, ...] | None = None
    listing_ids: tuple[str, ...] | None = None
    exchange: str | None = None
    columns: tuple[str, ...] | None = None
    maximum_rows: int = 100000
    maximum_files: int = 64

    def __post_init__(self) -> None:
        timestamp(self.known_at)
        if self.known_at is None:
            raise StorageError("KNOWLEDGE_CUTOFF_REQUIRED")
        if (
            type(self.maximum_rows) is not int
            or not 1 <= self.maximum_rows <= 100000
            or type(self.maximum_files) is not int
            or not 1 <= self.maximum_files <= 64
        ):
            raise StorageError("QUERY_RESOURCE_LIMIT")
        if self.valid_to <= self.valid_from or (self.valid_to - self.valid_from).days > 3660:
            raise StorageError("QUERY_RESOURCE_LIMIT")
        for values in (self.security_ids, self.listing_ids, self.columns):
            if values is not None and (type(values) is not tuple or len(values) > 1000):
                raise StorageError("QUERY_RESOURCE_LIMIT")


@dataclass(frozen=True)
class QueryResult:
    rows: tuple[dict[str, Any], ...]
    excluded: tuple[dict[str, Any], ...]
    files_scanned: int
    files_verified: int
    version_id: str
    financial_eligible: bool = field(default=False, init=False)
    publication_eligible: bool = field(default=False, init=False)
