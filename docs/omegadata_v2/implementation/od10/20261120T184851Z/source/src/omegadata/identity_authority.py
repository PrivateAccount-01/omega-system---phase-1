"""Pinned offline authority boundary; labels are never review or rights proofs.

Bundle hash is an operator-configured trust anchor, not a caller's claim field.
No authenticated bundle is supplied in the development configuration. Canonical
source-rights enforcement always runs against the existing read-only register.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass, is_dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from omegadata.track_a.source_rights import (
    PolicyRequest,
    SourceOperation,
    SourcePolicyError,
    SourceTransport,
    authorize_source,
)

# No owner-authenticated source-reference anchors have been supplied. This fixed,
# reviewed register is independent of a caller-supplied evidence bundle digest.
OWNER_ROOT_PATH = Path(__file__).resolve().parents[2] / "config/identity_authority_roots.v1.json"
OWNER_ROOT_SHA256 = "85b0b763221cf91f3a83afbd5f22f17740f85f61be57f1156e0e7b7eb96662dd"


def canonical(value: Any) -> str:
    def encode(item: Any) -> Any:
        if isinstance(item, datetime):
            if item.tzinfo is None or item.utcoffset() is None:
                raise ValueError("TIMEZONE_REQUIRED")
            return item.astimezone(UTC).isoformat()
        if isinstance(item, Decimal):
            if (
                not item.is_finite()
                or len(item.as_tuple().digits) > 64
                or abs(int(item.as_tuple().exponent)) > 64
            ):
                raise ValueError("AUTHORITY_DECIMAL_RESOURCE_LIMIT")
            return str(item)
        if isinstance(item, date):
            return item.isoformat()
        if is_dataclass(item) and not isinstance(item, type):
            return asdict(item)
        raise TypeError("CANONICAL_TYPE")

    return json.dumps(
        value,
        default=encode,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def claim_digest(claim: Any) -> str:
    return hashlib.sha256(canonical(claim).encode()).hexdigest()


@dataclass(frozen=True)
class AuthorityDecision:
    allowed: bool
    reason: str
    evidence_id: str
    anchor_sha256: str | None = None

    @property
    def financial_eligible(self) -> bool:
        return self.allowed


class EvidenceAuthority:
    """Configured by trusted launcher/service, never from parser or query labels.

    The API cannot establish human attestation authenticity from an unpinned
    document. An absent external anchor fails closed. Same-process arbitrary code
    execution is outside this data-contract boundary; OS sandbox handles workers.
    """

    def __init__(self, raw: bytes = b"", anchor_sha256: str | None = None) -> None:
        if raw and (anchor_sha256 is None or hashlib.sha256(raw).hexdigest() != anchor_sha256):
            raise ValueError("AUTHORITY_ANCHOR_MISMATCH")
        self.__raw = raw
        self.__pin = anchor_sha256
        if raw:
            body = self._body()
            if (
                set(body) != {"schema_version", "records"}
                or body["schema_version"] != "od06.authority/v1"
            ):
                raise ValueError("AUTHORITY_SCHEMA")
            records = body["records"]
            if not isinstance(records, list) or len(records) > 10000:
                raise ValueError("AUTHORITY_RESOURCE_LIMIT")
            ids = [r["evidence_id"] for r in records]
            if len(set(ids)) != len(ids):
                raise ValueError("CONFLICTING_REVIEW_RECORDS")

    @classmethod
    def unconfigured(cls) -> EvidenceAuthority:
        return cls()

    @classmethod
    def from_pinned_bundle(cls, path: Path, expected_sha256: str) -> EvidenceAuthority:
        if path.is_symlink() or path.stat().st_size > 2_000_000:
            raise ValueError("AUTHORITY_INPUT_UNSAFE")
        raw = path.read_bytes()
        return cls(raw, expected_sha256)

    def _body(self) -> dict[str, Any]:
        def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("AUTHORITY_DUPLICATE_KEY")
                result[key] = value
            return result

        result = json.loads(self.__raw, object_pairs_hook=unique)
        if not isinstance(result, dict):
            raise ValueError("AUTHORITY_SCHEMA")
        return result

    def _owner_root_approved(self, known_at: datetime) -> bool:
        try:
            if OWNER_ROOT_PATH.is_symlink():
                return False
            with OWNER_ROOT_PATH.open("rb") as stream:
                raw = stream.read(65537)
            if len(raw) > 65536 or hashlib.sha256(raw).hexdigest() != OWNER_ROOT_SHA256:
                return False
            body = json.loads(raw)
            if (
                set(body) != {"schema_version", "roots"}
                or body["schema_version"] != "od06.owner-authority-roots/v1"
            ):
                return False
            for root in body["roots"]:
                if root.get("anchor_sha256") != self.__pin:
                    continue
                when = datetime.fromisoformat(root["owner_recorded_at"])
                if (
                    when.tzinfo is not None
                    and when.utcoffset() is not None
                    and when <= known_at
                    and root.get("owner_record_identity")
                    and root.get("independent_reviewer_identity")
                    and not root.get("revoked")
                    and not root.get("superseded")
                ):
                    return True
        except (OSError, ValueError, TypeError, KeyError):
            return False
        return False

    def verify_identity_evidence(
        self,
        evidence_id: str,
        source_record: Mapping[str, Any],
        reviewer_attestation: Mapping[str, Any],
        consumer_purpose: str,
        as_of_knowledge: datetime,
        claim_sha256: str,
    ) -> AuthorityDecision:
        def deny(reason: str) -> AuthorityDecision:
            return AuthorityDecision(False, reason, evidence_id, self.__pin)

        if not evidence_id:
            return deny("EVIDENCE_ID_MISSING")
        if (
            not isinstance(as_of_knowledge, datetime)
            or as_of_knowledge.tzinfo is None
            or as_of_knowledge.utcoffset() is None
        ):
            return deny("KNOWLEDGE_TIME_UNKNOWN")
        try:
            purpose = SourceOperation(consumer_purpose)
        except ValueError:
            return deny("CONSUMER_PURPOSE_UNSUPPORTED")
        if not self.__raw:
            return deny("TRUSTED_AUTHORITY_NOT_CONFIGURED")
        row = next((r for r in self._body()["records"] if r["evidence_id"] == evidence_id), None)
        if row is None:
            return deny("EVIDENCE_NOT_IN_TRUST_ANCHOR")
        if row.get("revoked") or row.get("superseded"):
            return deny("EVIDENCE_REVOKED_OR_SUPERSEDED")
        if row.get("classification") != "AUTHENTIC_SOURCE":
            return deny("NON_MARKET_OR_UNVERIFIED_EVIDENCE")
        if (
            row.get("source_record") != dict(source_record)
            or row.get("reviewer_attestation") != dict(reviewer_attestation)
            or row.get("claim_sha256") != claim_sha256
        ):
            return deny("EVIDENCE_RELATIONSHIP_MISMATCH")
        if (
            source_record.get("authentication") != "VERIFIED"
            or source_record.get("revoked")
            or not isinstance(source_record.get("artifact_sha256"), str)
            or not re.fullmatch("[a-f0-9]{64}", source_record["artifact_sha256"])
            or not source_record.get("publisher_identity")
            or not source_record.get("document_version")
        ):
            return deny("PROVENANCE_INCOMPLETE")
        if (
            not reviewer_attestation.get("reviewer_id")
            or not reviewer_attestation.get("attestation_identity")
            or reviewer_attestation.get("conflict")
        ):
            return deny("ATTESTATION_INCOMPLETE")
        for raw in (source_record.get("available_at"), reviewer_attestation.get("reviewed_at")):
            try:
                if not isinstance(raw, str):
                    return deny("EVIDENCE_TIME_UNKNOWN")
                t = datetime.fromisoformat(raw)
                if t.tzinfo is None or t.utcoffset() is None or t > as_of_knowledge:
                    return deny("EVIDENCE_NOT_AVAILABLE_AS_KNOWN")
            except (ValueError, TypeError):
                return deny("EVIDENCE_TIME_UNKNOWN")
        try:
            decision = authorize_source(
                PolicyRequest(
                    source_key=source_record["source_key"],
                    operation=SourceOperation.READ_CACHED,
                    decision_at=as_of_knowledge.astimezone(UTC),
                    requested_transport=SourceTransport.CACHE,
                    consumer_purpose=purpose,
                )
            )
        except (ValueError, SourcePolicyError, KeyError) as error:
            return deny(
                "SOURCE_RIGHTS_BLOCKED:"
                + getattr(getattr(error, "reason_code", None), "value", "INVALID_SOURCE")
            )
        if not self._owner_root_approved(as_of_knowledge):
            return deny("OWNER_REVIEWED_AUTHORITY_ROOT_NOT_SUPPLIED")
        return AuthorityDecision(
            decision.allowed,
            "VERIFIED_BY_PINNED_AUTHORITY_AND_SOURCE_POLICY",
            evidence_id,
            self.__pin,
        )

    def check_claim(
        self, claim: Any, known_at: datetime, purpose: str = "RESEARCH"
    ) -> AuthorityDecision:
        if claim.evidence.classification == "NON_MARKET_CANARY":
            return AuthorityDecision(
                False, "NON_MARKET_CANARY", claim.evidence.evidence_id, self.__pin
            )
        row = (
            next(
                (
                    r
                    for r in self._body()["records"]
                    if r["evidence_id"] == claim.evidence.evidence_id
                ),
                None,
            )
            if self.__raw
            else None
        )
        return self.verify_identity_evidence(
            claim.evidence.evidence_id,
            row.get("source_record", {}) if row else {},
            row.get("reviewer_attestation", {}) if row else {},
            purpose,
            known_at,
            claim_digest(claim),
        )

    def snapshot_digest(self) -> str:
        """OD07 dependency: exact bundle/root/policy identity, not a permission grant."""
        from omegadata.track_a.source_rights import load_policy_register

        try:
            policy = load_policy_register().model_dump(mode="json")
        except ValueError:
            policy = {"status": "SOURCE_POLICY_UNAVAILABLE"}
        try:
            root = hashlib.sha256(OWNER_ROOT_PATH.read_bytes()).hexdigest()
        except OSError:
            root = "ROOT_UNAVAILABLE"
        return hashlib.sha256(
            canonical(
                {
                    "bundle_sha256": hashlib.sha256(self.__raw).hexdigest(),
                    "bundle_pin": self.__pin,
                    "owner_root_sha256": root,
                    "source_policy": policy,
                }
            ).encode()
        ).hexdigest()
