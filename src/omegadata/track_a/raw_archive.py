"""Opt-in local immutable raw bytes. Integrity is not source authenticity.

Requires a trusted private local directory. Hardlinks define exclusive publication;
only a validated commit marker exposes an observation. Staging is never deleted.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import threading
import time
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omegadata.track_a.acquisition import load_limits, safe_url, validate_payload
from omegadata.track_a.source_registry import SOURCE_REGISTRY, resolve_era
from omegadata.track_a.source_rights import (
    PolicyProvider,
    PolicyRequest,
    SourceOperation,
    SourcePolicyDecision,
    SourceTransport,
    authorize_source,
    load_policy_register,
    policy_url_host,
    utc_datetime,
)

Hex64 = Annotated[str, Field(strict=True, pattern=r"^[0-9a-f]{64}$")]
Hex32 = Annotated[str, Field(strict=True, pattern=r"^[0-9a-f]{32}$")]
Label = Annotated[str, Field(strict=True, min_length=1, max_length=256, pattern=r"^[A-Za-z0-9_.:/-]+$")]
Size = Annotated[int, Field(strict=True, gt=0)]
Mode = Literal["SYNTHETIC_TEST_ONLY", "SOURCE_CACHED_RAW", "SOURCE_SEED_IMPORTED", "PROVIDER_OBSERVED_UNVERIFIED"]
_LOCKS: dict[str, threading.RLock] = {}
_LOCKS_GUARD = threading.Lock()


class ArchiveError(RuntimeError):
    """Code-only public error: untrusted payloads and paths never enter context."""

    def __init__(self, code: str) -> None:
        self.reason_code = code
        super().__init__(code)


class Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")


class ObservationRequest(Frozen):
    source_key: str
    business_date: date
    observed_at: datetime
    operation_id: Hex32 = Field(default_factory=lambda: uuid.uuid4().hex)
    source_era: Label
    source_mode: Mode
    parser_schema: Label
    payload_state: Literal["HTTP_RECEIVED", "PAYLOAD_STRUCTURALLY_VALID"]
    transport: SourceTransport
    original_url: Annotated[str, Field(max_length=2048)]
    final_url: Annotated[str, Field(max_length=2048)]
    origin_ref: Label
    attempts: Annotated[int, Field(strict=True, ge=0, le=64)] = 1
    consumer_purpose: SourceOperation | None = None

    @field_validator("observed_at", mode="before")
    @classmethod
    def utc(cls, value: Any) -> datetime:
        return utc_datetime(value)

    @field_validator("origin_ref", "parser_schema", "source_era")
    @classmethod
    def safe_label(cls, value: str) -> str:
        if ".." in value or "\\" in value or value.startswith(("/", ":")):
            raise ValueError("Invalid metadata label")
        return value

    @field_validator("original_url", "final_url")
    @classmethod
    def sanitized(cls, value: str) -> str:
        value = safe_url(value)
        if policy_url_host(value) is None:
            raise ValueError("Invalid evidence URL")
        return value

    @model_validator(mode="after")
    def scope(self) -> ObservationRequest:
        if self.source_key not in SOURCE_REGISTRY or resolve_era(self.source_key, self.business_date).name != self.source_era:
            raise ValueError("Unknown source/date/era")
        if self.source_mode == "SOURCE_SEED_IMPORTED" and self.transport != SourceTransport.SEED_CACHE:
            raise ValueError("Seed origin requires seed transport")
        if self.source_mode == "SOURCE_CACHED_RAW" and self.transport != SourceTransport.CACHE:
            raise ValueError("Cache origin requires cache transport")
        if self.source_mode == "PROVIDER_OBSERVED_UNVERIFIED" and self.transport in {SourceTransport.CACHE, SourceTransport.SEED_CACHE}:
            raise ValueError("Cached bytes cannot become provider observation")
        if "SYNTHETIC_TEST_ONLY" in self.origin_ref and self.source_mode != "SYNTHETIC_TEST_ONLY":
            raise ValueError("Synthetic origin cannot become real-source provenance")
        return self


class RawObject(Frozen):
    schema_version: Literal["raw-object/v1"] = "raw-object/v1"
    sha256: Hex64
    size: Size
    relative_path: str
    verification: Literal["RAW_BYTES_CAPTURED"] = "RAW_BYTES_CAPTURED"
    media_hint: Literal["application/octet-stream"] = "application/octet-stream"

    @model_validator(mode="after")
    def path_matches(self) -> RawObject:
        if self.relative_path != f"objects/sha256/{self.sha256[:2]}/{self.sha256[2:4]}/{self.sha256}":
            raise ValueError("Invalid object address")
        return self


class RawObservation(Frozen):
    schema_version: Literal["raw-observation/v1"] = "raw-observation/v1"
    observation_id: Hex32
    request: ObservationRequest
    object: RawObject
    policy_decisions: tuple[SourcePolicyDecision, ...]
    published_at: None = None
    source_reference: Literal["SOURCE_REFERENCE_PENDING"] = "SOURCE_REFERENCE_PENDING"
    warnings: tuple[Literal["SOURCE_REFERENCE_PENDING"], ...] = ("SOURCE_REFERENCE_PENDING",)

    @model_validator(mode="after")
    def identity(self) -> RawObservation:
        if self.observation_id != self.request.operation_id or not self.policy_decisions:
            raise ValueError("Invalid observation identity")
        if any(not d.allowed or d.source_key != self.request.source_key or not d.revision_hash for d in self.policy_decisions):
            raise ValueError("Invalid decision identity")
        return self


class RawCommit(Frozen):
    schema_version: Literal["raw-commit/v1"] = "raw-commit/v1"
    state: Literal["COMMITTED"] = "COMMITTED"
    observation_id: Hex32
    object: RawObject
    observation_sha256: Hex64
    committed_at: datetime

    @field_validator("committed_at", mode="before")
    @classmethod
    def utc(cls, value: Any) -> datetime:
        return utc_datetime(value)


def canonical(model: BaseModel) -> bytes:
    return json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def unique_json(raw: bytes) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON field")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Invalid number")))


class RawArchive:
    def __init__(self, root: Path, *, policy_provider: PolicyProvider | None = None,
                 clock: Callable[[], datetime] | None = None, fault: Callable[[str], None] | None = None) -> None:
        self.root = Path(os.path.abspath(root))
        self.policy_provider = policy_provider or load_policy_register
        self.clock = clock or (lambda: datetime.now(UTC))
        self.fault = fault
        self.max_payload = 16 * 1024 * 1024
        self.max_metadata = 64 * 1024
        self.max_bytes = 128 * 1024 * 1024
        self.max_entries = 4096
        self.lock_seconds = 5.0

    def _safe(self, path: Path) -> Path:
        # The directory ownership boundary is explicit: no hostile concurrent
        # parent swaps are certified. Reject static links, including inside-root.
        path = Path(os.path.abspath(path))
        if not path.is_relative_to(self.root):
            raise ArchiveError("INTEGRITY")
        for parent in [path, *path.parents]:
            if parent.is_symlink() or (parent.exists() and parent.resolve() != parent):
                raise ArchiveError("INTEGRITY")
        return path

    def _mkdir(self, path: Path) -> None:
        self._safe(path)
        missing = [p for p in [path, *path.parents] if p.is_relative_to(self.root) and not p.exists()]
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._safe(path)
        for created in reversed(missing):
            if created.parent.is_relative_to(self.root):
                self._sync_dir(created.parent)

    def _read(self, path: Path, limit: int) -> bytes:
        self._safe(path)
        if not path.is_file() or path.stat().st_size > limit:
            raise ArchiveError("INTEGRITY")
        with path.open("rb") as handle:
            data = handle.read(limit + 1)
        if len(data) > limit:
            raise ArchiveError("INTEGRITY")
        return data

    def _authorize(self, request: ObservationRequest, operation: SourceOperation) -> SourcePolicyDecision:
        return authorize_source(PolicyRequest(source_key=request.source_key, operation=operation,
            decision_at=self.clock(), requested_transport=request.transport,
            requested_host=policy_url_host(request.final_url) if request.transport not in {SourceTransport.CACHE, SourceTransport.SEED_CACHE} else None,
            consumer_purpose=request.consumer_purpose), self.policy_provider)

    def _read_rights(self, source_key: str, purpose: SourceOperation | None, transport: SourceTransport = SourceTransport.CACHE) -> None:
        authorize_source(PolicyRequest(source_key=source_key, operation=SourceOperation.READ_CACHED,
            decision_at=self.clock(), requested_transport=transport, consumer_purpose=purpose), self.policy_provider)

    def commit_path(self, observation_id: str) -> Path:
        return self._id_path("commits", observation_id)

    def observation_path(self, observation_id: str) -> Path:
        return self._id_path("observations", observation_id)

    def _id_path(self, namespace: str, observation_id: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{32}", observation_id):
            raise ArchiveError("INPUT_INVALID")
        return self._safe(self.root / namespace / (observation_id + ".json"))

    @contextmanager
    def _lock(self) -> Iterator[None]:
        with _LOCKS_GUARD:
            local = _LOCKS.setdefault(str(self.root), threading.RLock())
        if not local.acquire(timeout=self.lock_seconds):
            raise ArchiveError("ARCHIVE_BUSY")
        try:
            self._mkdir(self.root)
            path = self._safe(self.root / ".writer.lock")
            with path.open("a+b") as handle:
                if handle.seek(0, os.SEEK_END) == 0:
                    handle.write(b"0")
                    handle.flush()
                deadline = time.monotonic() + self.lock_seconds
                while True:
                    try:
                        handle.seek(0)
                        if sys.platform == "win32":
                            import msvcrt
                            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                        else:
                            import fcntl
                            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except OSError:
                        if time.monotonic() >= deadline:
                            raise ArchiveError("ARCHIVE_BUSY") from None
                        time.sleep(0.01)
                try:
                    yield
                finally:
                    handle.seek(0)
                    if sys.platform == "win32":
                        import msvcrt
                        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            local.release()

    def _inventory(self) -> tuple[int, int]:
        total = entries = 0
        if not self.root.exists():
            return total, entries
        for directory, dirs, files in os.walk(self._safe(self.root), followlinks=False):
            for name in [*dirs, *files]:
                path = self._safe(Path(directory) / name)
                entries += 1
                if entries > self.max_entries:
                    raise ArchiveError("BUDGET_EXCEEDED")
                if path.is_file():
                    total += path.stat().st_size
                if total > self.max_bytes:
                    raise ArchiveError("BUDGET_EXCEEDED")
        return total, entries

    def _sync_dir(self, path: Path) -> None:
        if sys.platform != "win32":
            fd = os.open(self._safe(path), os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)

    def _publish(self, path: Path, data: bytes, stage: Path, name: str) -> None:
        if path.exists():
            if self._read(path, max(self.max_payload, self.max_metadata)) != data:
                raise ArchiveError("INTEGRITY")
            return
        self._mkdir(path.parent)
        temp = self._safe(stage / name)
        with temp.open("xb") as handle:
            if handle.write(data) != len(data):
                raise ArchiveError("STORAGE_FAILURE")
            handle.flush()
            os.fsync(handle.fileno())
        if hashlib.sha256(self._read(temp, len(data))).digest() != hashlib.sha256(data).digest():
            raise ArchiveError("INTEGRITY")
        try:
            os.link(temp, self._safe(path))
        except FileExistsError:
            if self._read(path, len(data)) != data:
                raise ArchiveError("INTEGRITY") from None
        self._sync_dir(path.parent)

    def _step(self, phase: str) -> None:
        if self.fault:
            self.fault(phase)

    def put(self, payload: bytes, request: ObservationRequest) -> RawCommit:
        request = ObservationRequest.model_validate(request)
        self._authorize(request, SourceOperation.STORE_RAW)
        if type(payload) is not bytes or not 0 < len(payload) <= self.max_payload:
            raise ArchiveError("BUDGET_EXCEEDED")
        if request.payload_state == "PAYLOAD_STRUCTURALLY_VALID":
            validated = validate_payload(request.source_key, payload, request.business_date, load_limits())
            if validated.state != request.payload_state or validated.schema != request.parser_schema:
                raise ArchiveError("INPUT_INVALID")
        digest = hashlib.sha256(payload).hexdigest()
        obj = RawObject(sha256=digest, size=len(payload), relative_path=f"objects/sha256/{digest[:2]}/{digest[2:4]}/{digest}")
        try:
            with self._lock():
                commit_path = self.commit_path(request.operation_id)
                obs_path = self.observation_path(request.operation_id)
                decision = self._authorize(request, SourceOperation.STORE_RAW)
                if commit_path.exists():
                    commit, observation, previous = self._verified(request.operation_id)
                    if previous != payload or observation.request != request or observation.policy_decisions[-1].revision_hash != decision.revision_hash:
                        raise ArchiveError("CONFLICT")
                    return commit
                observation = RawObservation(observation_id=request.operation_id, request=request, object=obj, policy_decisions=(decision,))
                if obs_path.exists():
                    old = RawObservation.model_validate(unique_json(self._read(obs_path, self.max_metadata)))
                    if old.request != request or old.object != obj or old.policy_decisions[-1].revision_hash != decision.revision_hash:
                        raise ArchiveError("CONFLICT")
                    observation = old
                observation_bytes = canonical(observation)
                commit = RawCommit(observation_id=request.operation_id, object=obj,
                    observation_sha256=hashlib.sha256(observation_bytes).hexdigest(), committed_at=self.clock())
                commit_bytes = canonical(commit)
                if max(len(observation_bytes), len(commit_bytes)) > self.max_metadata:
                    raise ArchiveError("BUDGET_EXCEEDED")
                total, entries = self._inventory()
                # Conservative reservation: retained staging and linked finals
                # counted twice; neither logical quota nor entries can race.
                if total + 2 * (len(payload) + len(observation_bytes) + len(commit_bytes)) > self.max_bytes or entries + 16 > self.max_entries:
                    raise ArchiveError("BUDGET_EXCEEDED")
                self._step("before_stage")
                stage = self.root / "staging" / uuid.uuid4().hex
                self._mkdir(stage)
                self._step("after_stage")
                self._publish(self._safe(self.root / obj.relative_path), payload, stage, "payload")
                self._step("after_object")
                self._publish(obs_path, observation_bytes, stage, "observation")
                self._step("after_observation")
                self._step("before_commit")
                if self._authorize(request, SourceOperation.STORE_RAW).revision_hash != observation.policy_decisions[-1].revision_hash:
                    raise ArchiveError("CONFLICT")
                self._publish(commit_path, commit_bytes, stage, "commit")
                return self._verified(request.operation_id)[0]
        except (OSError, ValueError, json.JSONDecodeError):
            raise ArchiveError("STORAGE_FAILURE") from None

    def _verified(self, observation_id: str) -> tuple[RawCommit, RawObservation, bytes]:
        path = self.commit_path(observation_id)
        if not path.exists():
            raise ArchiveError("NOT_COMMITTED")
        commit = RawCommit.model_validate(unique_json(self._read(path, self.max_metadata)))
        raw = self._read(self.observation_path(observation_id), self.max_metadata)
        observation = RawObservation.model_validate(unique_json(raw))
        if commit.observation_id != observation_id or observation.observation_id != observation_id or commit.object != observation.object or hashlib.sha256(raw).hexdigest() != commit.observation_sha256:
            raise ArchiveError("INTEGRITY")
        data = self._read(self._safe(self.root / commit.object.relative_path), self.max_payload)
        if len(data) != commit.object.size or hashlib.sha256(data).hexdigest() != commit.object.sha256:
            raise ArchiveError("INTEGRITY")
        return commit, observation, data

    def read_verified(self, observation_id: str, source_key: str, business_date: date,
                      consumer_purpose: SourceOperation | None = None) -> tuple[bytes, RawObservation]:
        self._read_rights(source_key, consumer_purpose)
        try:
            # Validate source/date metadata before opening raw bytes.
            raw = self._read(self.observation_path(observation_id), self.max_metadata) if self.commit_path(observation_id).exists() else None
            if raw is None:
                raise ArchiveError("NOT_COMMITTED")
            obs = RawObservation.model_validate(unique_json(raw))
            if obs.request.source_key != source_key or obs.request.business_date != business_date:
                raise ArchiveError("INTEGRITY")
            if obs.request.source_mode == "SOURCE_SEED_IMPORTED":
                self._read_rights(source_key, consumer_purpose, SourceTransport.SEED_CACHE)
            _, observation, data = self._verified(observation_id)
            self._read_rights(source_key, consumer_purpose)
            return data, observation
        except (OSError, ValueError, json.JSONDecodeError):
            raise ArchiveError("INTEGRITY") from None

    def recover_staging(self) -> dict[str, Any]:
        """Read-only bounded inventory. No promotion, deletion or implicit retention."""
        try:
            total, entries = self._inventory()
            commits = self._safe(self.root / "commits")
            staging = self._safe(self.root / "staging")
            observations = self._safe(self.root / "observations")
            ids = sorted(p.stem for p in commits.glob("*.json"))
            orphan_ids = sorted(p.stem for p in observations.glob("*.json") if p.stem not in ids)
            return {"committed": len(ids), "commit_ids": ids, "uncommitted_observations": orphan_ids,
                    "retained_staging": sorted(p.name for p in staging.iterdir()) if staging.exists() else [],
                    "logical_bytes": total, "entries": entries, "action": "READ_ONLY_NO_PROMOTION_NO_DELETION",
                    "verification": "UNVERIFIED_COMMIT_MARKER_COUNT_USE_SCAN_VERIFIED"}
        except OSError:
            raise ArchiveError("INTEGRITY") from None

    def scan_verified(self, source_key: str, business_date: date,
                      consumer_purpose: SourceOperation | None = None) -> dict[str, Any]:
        """Deterministic fail-closed scan of a scoped archive, never repair it.

        A mixed source/date root refuses rather than silently omitting records.
        Recovery inventory is not a substitute for this full byte verification.
        """
        self._read_rights(source_key, consumer_purpose)
        inventory = self.recover_staging()
        rows = []
        for identity in inventory["commit_ids"]:
            data, obs = self.read_verified(identity, source_key, business_date, consumer_purpose)
            rows.append({"observation_id": identity, "sha256": hashlib.sha256(data).hexdigest(),
                         "bytes": len(data), "source_mode": obs.request.source_mode,
                         "source_reference": obs.source_reference})
        return {"schema_version": "raw-verification/v1", "source_key": source_key,
                "business_date": business_date.isoformat(), "observations": rows,
                "retention": "NO_PROMOTION_NO_DELETION"}
