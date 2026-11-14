"""Versioned source-use preconditions. Technical validation is not legal approval."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictStr,
    StringConstraints,
    ValidationError,
    field_validator,
    model_validator,
)

from omegadata.track_a.source_registry import SOURCE_REGISTRY

DEFAULT_POLICY_PATH = Path(__file__).resolve().parents[3] / "config/source_rights_policy.v1.json"
Text = Annotated[StrictStr, StringConstraints(strip_whitespace=True, min_length=1)]
Digest = Annotated[StrictStr, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class PolicyStatus(StrEnum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class SourceOperation(StrEnum):
    FETCH = "FETCH"
    READ_CACHED = "READ_CACHED"
    STORE_RAW = "STORE_RAW"
    DERIVE = "DERIVE"
    RESEARCH = "RESEARCH"
    TRADE_DECISION_USE = "TRADE_DECISION_USE"
    REDISTRIBUTE = "REDISTRIBUTE"
    COMMERCIAL_PRODUCT = "COMMERCIAL_PRODUCT"


class SourceTransport(StrEnum):
    HTTPX = "HTTPX"
    URLLIB = "URLLIB"
    CURL = "CURL"
    CACHE = "CACHE"
    SEED_CACHE = "SEED_CACHE"
    BROWSER = "BROWSER"


class PolicyReason(StrEnum):
    ALLOWED = "ALLOWED"
    UNKNOWN_SOURCE = "UNKNOWN_SOURCE"
    MISSING_POLICY = "MISSING_POLICY"
    POLICY_PENDING = "POLICY_PENDING"
    POLICY_DENIED = "POLICY_DENIED"
    POLICY_REVOKED = "POLICY_REVOKED"
    POLICY_EXPIRED = "POLICY_EXPIRED"
    EVIDENCE_INCOMPLETE = "EVIDENCE_INCOMPLETE"
    SCOPE_NOT_ALLOWED = "SCOPE_NOT_ALLOWED"
    HOST_NOT_ALLOWED = "HOST_NOT_ALLOWED"
    TRANSPORT_NOT_ALLOWED = "TRANSPORT_NOT_ALLOWED"
    MALFORMED_POLICY = "MALFORMED_POLICY"


def utc_datetime(value: object) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if not isinstance(value, datetime) or value.utcoffset() != timedelta(0):
        raise ValueError("An explicitly timezone-aware UTC datetime is required")
    return value


def normalized_host(value: str) -> str:
    host = value.lower().removesuffix(".")
    if (
        len(host) > 253
        or not re.fullmatch(
            r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)*", host
        )
        or any(len(label) > 63 for label in host.split("."))
    ):
        raise ValueError("Expected an exact DNS hostname, without scheme, port or wildcard")
    return host


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")


class SourcePolicy(FrozenModel):
    schema_version: Literal["source-policy/v1"]
    source_key: Text
    policy_id: Text
    policy_revision: Annotated[int, Field(strict=True, gt=0)]
    status: PolicyStatus
    created_at: datetime
    change_reason: Text
    revision_hash: Digest
    previous_revision_hash: Digest | None = None
    source_entity: Text | None = None
    source_terms_url: Text | None = None
    terms_sha256: Digest | None = None
    terms_retrieved_at: datetime | None = None
    approval_evidence_ref: Text | None = None
    approved_by: Text | None = None
    approved_at: datetime | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    permitted_operations: tuple[SourceOperation, ...] = ()
    permitted_transports: tuple[SourceTransport, ...] = ()
    allowed_hosts: tuple[Text, ...] = ()
    rate_limit: Annotated[int, Field(strict=True, gt=0)] | None = None
    retention_policy: Text | None = None
    attribution: Text | None = None
    geography: Text | None = None
    credential_requirement: Text | None = None
    cost_ceiling: Text | None = None
    revocation_reason: Text | None = None
    revoked_at: datetime | None = None

    @field_validator(
        "created_at",
        "terms_retrieved_at",
        "approved_at",
        "valid_from",
        "valid_until",
        "revoked_at",
        mode="before",
    )
    @classmethod
    def validate_utc(cls, value: object) -> datetime | None:
        return None if value is None else utc_datetime(value)

    @field_validator("source_key", mode="before")
    @classmethod
    def known_key(cls, value: object) -> str:
        if not isinstance(value, str) or value not in SOURCE_REGISTRY:
            raise ValueError("Policy source key is not registered")
        return value

    @field_validator("source_terms_url")
    @classmethod
    def terms_url(cls, value: str | None) -> str | None:
        if value is not None:
            from urllib.parse import urlsplit

            url = urlsplit(value)
            if (
                url.scheme not in {"http", "https"}
                or not url.hostname
                or url.username
                or url.password
            ):
                raise ValueError("Terms URL must identify a public document without credentials")
        return value

    @field_validator("allowed_hosts")
    @classmethod
    def hosts(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        result = tuple(normalized_host(host) for host in value)
        if len(set(result)) != len(result):
            raise ValueError("Duplicate allowed host")
        return result

    @model_validator(mode="after")
    def intervals_and_sets(self) -> Self:
        if self.status == PolicyStatus.REVOKED and (
            not self.revocation_reason or self.revoked_at is None
        ):
            raise ValueError("Revocation requires reason and UTC timestamp")
        if (
            self.valid_from is not None
            and self.valid_until is not None
            and self.valid_until <= self.valid_from
        ):
            raise ValueError("Approval interval must be nonempty")
        if len(set(self.permitted_operations)) != len(self.permitted_operations):
            raise ValueError("Duplicate operation")
        if len(set(self.permitted_transports)) != len(self.permitted_transports):
            raise ValueError("Duplicate transport")
        return self

    def canonical_hash(self) -> str:
        body = self.model_dump(mode="json", exclude={"revision_hash"})
        return hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        ).hexdigest()


class PolicyRequest(FrozenModel):
    source_key: Text
    operation: SourceOperation
    decision_at: datetime
    requested_transport: SourceTransport
    requested_host: StrictStr | None = None
    consumer_purpose: SourceOperation | None = None

    @field_validator("source_key", mode="before")
    @classmethod
    def exact_source_key(cls, value: object) -> object:
        if isinstance(value, str) and value != value.strip():
            raise ValueError("Source keys must match exactly")
        return value

    @field_validator("decision_at", mode="before")
    @classmethod
    def validate_utc(cls, value: object) -> datetime:
        return utc_datetime(value)


class SourcePolicyDecision(FrozenModel):
    allowed: bool
    reason_code: PolicyReason
    source_key: str
    operation: SourceOperation
    evaluated_at: datetime
    requested_transport: SourceTransport
    requested_host: str | None
    consumer_purpose: SourceOperation | None
    policy_id: str | None = None
    policy_revision: int | None = None
    revision_hash: str | None = None


class SourcePolicyError(RuntimeError):
    def __init__(self, decision: SourcePolicyDecision) -> None:
        self.decision = decision
        self.reason_code = decision.reason_code
        super().__init__(
            f"{decision.reason_code.value}: source={decision.source_key}, operation={decision.operation.value}"
        )


class PolicyRegisterError(ValueError):
    def __init__(self, reason_code: PolicyReason) -> None:
        self.reason_code = reason_code
        super().__init__(reason_code.value)


def decision_record(
    request: PolicyRequest, reason: PolicyReason, policy: SourcePolicy | None = None
) -> SourcePolicyDecision:
    return SourcePolicyDecision(
        allowed=reason == PolicyReason.ALLOWED,
        reason_code=reason,
        source_key=request.source_key,
        operation=request.operation,
        evaluated_at=request.decision_at,
        requested_transport=request.requested_transport,
        requested_host=request.requested_host,
        consumer_purpose=request.consumer_purpose,
        policy_id=None if policy is None else policy.policy_id,
        policy_revision=None if policy is None else policy.policy_revision,
        revision_hash=None if policy is None else policy.revision_hash,
    )


class SourcePolicyRegister(FrozenModel):
    schema_version: Literal["source-policy/v1"]
    policies: tuple[SourcePolicy, ...]

    @model_validator(mode="after")
    def revisions(self) -> Self:
        previous: dict[str, SourcePolicy] = {}
        identities: dict[str, str] = {}
        for policy in self.policies:
            if policy.revision_hash != policy.canonical_hash():
                raise ValueError("Policy revision hash mismatch")
            old = previous.get(policy.source_key)
            if old is None:
                if policy.policy_revision != 1 or policy.previous_revision_hash is not None:
                    raise ValueError("History must begin with revision 1")
            elif (
                policy.policy_id != old.policy_id
                or policy.policy_revision <= old.policy_revision
                or policy.previous_revision_hash != old.revision_hash
                or policy.created_at < old.created_at
            ):
                raise ValueError("Policy history is duplicated, reordered or unlinked")
            owner = identities.setdefault(policy.policy_id, policy.source_key)
            if owner != policy.source_key:
                raise ValueError("Policy ID reused across sources")
            previous[policy.source_key] = policy
        return self

    def evaluate(self, request: PolicyRequest) -> SourcePolicyDecision:
        if request.source_key not in SOURCE_REGISTRY:
            return decision_record(request, PolicyReason.UNKNOWN_SOURCE)
        policy = next(
            (p for p in reversed(self.policies) if p.source_key == request.source_key), None
        )
        if policy is None:
            return decision_record(request, PolicyReason.MISSING_POLICY)
        blocked = {
            PolicyStatus.PENDING_REVIEW: PolicyReason.POLICY_PENDING,
            PolicyStatus.DENIED: PolicyReason.POLICY_DENIED,
            PolicyStatus.REVOKED: PolicyReason.POLICY_REVOKED,
            PolicyStatus.EXPIRED: PolicyReason.POLICY_EXPIRED,
        }
        if policy.status in blocked:
            return decision_record(request, blocked[policy.status], policy)
        required = (
            policy.source_entity,
            policy.source_terms_url,
            policy.terms_sha256,
            policy.terms_retrieved_at,
            policy.approval_evidence_ref,
            policy.approved_by,
            policy.approved_at,
            policy.valid_from,
            policy.valid_until,
        )
        if not all(value is not None for value in required):
            return decision_record(request, PolicyReason.EVIDENCE_INCOMPLETE, policy)
        assert policy.valid_from is not None and policy.valid_until is not None
        if request.decision_at >= policy.valid_until:
            return decision_record(request, PolicyReason.POLICY_EXPIRED, policy)
        if any(
            t is not None and t > request.decision_at
            for t in (
                policy.created_at,
                policy.terms_retrieved_at,
                policy.approved_at,
                policy.valid_from,
            )
        ):
            return decision_record(request, PolicyReason.SCOPE_NOT_ALLOWED, policy)
        if request.operation not in policy.permitted_operations or (
            request.consumer_purpose is not None
            and request.consumer_purpose not in policy.permitted_operations
        ):
            return decision_record(request, PolicyReason.SCOPE_NOT_ALLOWED, policy)
        if request.requested_transport not in policy.permitted_transports:
            return decision_record(request, PolicyReason.TRANSPORT_NOT_ALLOWED, policy)
        if request.requested_host is None:
            if request.requested_transport not in {
                SourceTransport.CACHE,
                SourceTransport.SEED_CACHE,
            }:
                return decision_record(request, PolicyReason.HOST_NOT_ALLOWED, policy)
        else:
            try:
                host = normalized_host(request.requested_host)
            except ValueError:
                return decision_record(request, PolicyReason.HOST_NOT_ALLOWED, policy)
            if host not in policy.allowed_hosts:
                return decision_record(request, PolicyReason.HOST_NOT_ALLOWED, policy)
        return decision_record(request, PolicyReason.ALLOWED, policy)


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def load_policy_register(path: Path = DEFAULT_POLICY_PATH) -> SourcePolicyRegister:
    try:
        text = path.read_text(encoding="utf-8")
        json.loads(text, object_pairs_hook=_unique_object)
        return SourcePolicyRegister.model_validate_json(text)
    except FileNotFoundError as exc:
        raise PolicyRegisterError(PolicyReason.MISSING_POLICY) from exc
    except (OSError, UnicodeError, ValueError, ValidationError) as exc:
        raise PolicyRegisterError(PolicyReason.MALFORMED_POLICY) from exc


PolicyProvider = Callable[[], SourcePolicyRegister]


def authorize_source(
    request: PolicyRequest, provider: PolicyProvider = load_policy_register
) -> SourcePolicyDecision:
    if request.source_key not in SOURCE_REGISTRY:
        raise SourcePolicyError(decision_record(request, PolicyReason.UNKNOWN_SOURCE))
    try:
        decision = provider().evaluate(request)
    except PolicyRegisterError as exc:
        raise SourcePolicyError(decision_record(request, exc.reason_code)) from exc
    if not decision.allowed:
        raise SourcePolicyError(decision)
    return decision
