"""Opt-in, pinned-manifest to lstat correlation. Never opens market payloads."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import time
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NoReturn

from omegadata.parsers.archive_candidate_inventory import (
    SOURCE_KEY,
    ExpectedMetadata,
    InventoryError,
    ScanLimits,
    json_object,
    parse_metadata,
    relative_name,
    validate_root,
)
from omegadata.parsers.reference_evidence import ReferenceError, read_file
from omegadata.track_a.source_rights import (
    PolicyProvider,
    PolicyRequest,
    SourceOperation,
    SourcePolicyError,
    SourceTransport,
    authorize_source,
    load_policy_register,
)

ROOTS = {
    "seed": "data/seed_raw/omega_phase2_repo/nse_equity_bhavcopy",
    "cache": "data/raw/nse_equity_bhavcopy",
}
SAMPLE_DAYS = ("2011-06-22", "2020-01-02", "2024-07-23")


def request_payload_integrity(
    root_name: str, *, policy_provider: PolicyProvider = load_policy_register
) -> NoReturn:
    """Refusal-only future entry: no bare legacy-file read or policy override.

    Even a policy grant cannot supply the missing per-file operator scope and
    committed RawArchive observation mapping. A separately authorized adapter
    must use RawArchive.read_verified; this function never imports legacy bytes.
    """
    if root_name not in ROOTS:
        raise InventoryError("SOURCE_SCOPE")
    try:
        authorize_source(
            PolicyRequest(
                source_key=SOURCE_KEY,
                operation=SourceOperation.READ_CACHED,
                decision_at=datetime.now(UTC),
                requested_transport=(
                    SourceTransport.SEED_CACHE if root_name == "seed" else SourceTransport.CACHE
                ),
            ),
            policy_provider,
        )
    except SourcePolicyError as error:
        raise InventoryError(error.reason_code.value) from None
    raise InventoryError("SCOPED_OPERATOR_AND_RAWARCHIVE_MAPPING_REQUIRED")


def _info(path: Path, boundary: Path, names: dict[Path, frozenset[str]]) -> tuple[str, int | None]:
    """Check every ancestor lexically; lstat never follows the final component."""
    try:
        pieces = path.relative_to(boundary).parts
        current = boundary
        for index, part in enumerate(pieces):
            # Refuse alternate-case filesystem aliases on Windows and POSIX alike.
            if current not in names:
                names[current] = frozenset(entry.name for entry in current.iterdir())
            if part not in names[current]:
                if any(entry.casefold() == part.casefold() for entry in names[current]):
                    return "PATH_UNSAFE", None
                return "MISSING_PAYLOAD", None
            current = current / part
            info = current.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                return "SYMLINK_OR_REPARSE_REFUSED", None
            if info.st_dev != boundary.lstat().st_dev:
                return "PATH_UNSAFE", None
            if index < len(pieces) - 1:
                if not stat.S_ISDIR(info.st_mode):
                    return "PATH_UNSAFE", None
            elif not stat.S_ISREG(info.st_mode):
                return "WRONG_TYPE", None
            elif info.st_nlink != 1:
                return "HARDLINK_REFUSED", info.st_size
            else:
                return "PRESENT", info.st_size
    except FileNotFoundError:
        return "MISSING_PAYLOAD", None
    except OSError:
        return "STAT_REFUSED", None
    return "WRONG_TYPE", None


def _manifest_names(root: Path, limits: ScanLimits, started: float) -> set[str]:
    names: set[str] = set()
    stack = [(root, 0)]
    count = 0
    aliases: set[str] = set()
    while stack:
        directory, depth = stack.pop()
        if depth > limits.max_depth:
            raise InventoryError("BUDGET")
        for path in directory.iterdir():
            count += 1
            if count > limits.max_entries or time.monotonic() - started > limits.max_seconds:
                raise InventoryError("BUDGET")
            info = path.lstat()
            name = relative_name(path.relative_to(root).as_posix())
            if name.casefold() in aliases:
                raise InventoryError("PATH_UNSAFE")
            aliases.add(name.casefold())
            linked = stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400
            if stat.S_ISDIR(info.st_mode) and not linked:
                stack.append((path, depth + 1))
            elif name.endswith(".manifest.json"):
                if linked or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    raise InventoryError("PATH_UNSAFE")
                names.add(name)
                if len(names) > limits.max_files:
                    raise InventoryError("BUDGET")
    return names


def _row(
    repo: Path,
    root: Path,
    name: str,
    raw: bytes,
    names: dict[Path, frozenset[str]],
    inspector: Callable[[Path, Path, dict[Path, frozenset[str]]], tuple[str, int | None]] = _info,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "manifest": name,
        "date": None,
        "state": "MALFORMED_METADATA",
        "claimed_bytes": None,
        "filesystem_bytes": None,
        "payload_relative": None,
        "claim_format": "UNKNOWN",
        "source_mode": "UNKNOWN",
        "original_filename_claim": None,
        "lineage": "UNVERIFIED",
        "era_state": "REFERENCE_PENDING",
        "payload_hash_verified": False,
        "publisher_origin": "PUBLISHER_ORIGIN_UNVERIFIED",
        "rights": "RIGHTS_PENDING",
    }
    try:
        candidate = parse_metadata(raw, name)
        body = json_object(raw, 65536)
        row.update(date=candidate.business_date, source_mode=candidate.storage_mode)
        claim = body.get("artifact_path")
        if not isinstance(claim, str):
            raise InventoryError("PATH_UNSAFE")
        claim = relative_name(claim.replace("\\", "/"))
        prefix = root.relative_to(repo).as_posix() + "/"
        if not claim.startswith(prefix) or not claim.endswith(".zip"):
            raise InventoryError("PATH_UNSAFE")
        claimed_bytes = body.get("bytes_downloaded")
        if type(claimed_bytes) is not int or not 0 < claimed_bytes <= 16 * 1024 * 1024:
            raise InventoryError("MALFORMED_METADATA")
        row.update(payload_relative=claim, claimed_bytes=claimed_bytes)
        original = body.get("original_filename")
        if isinstance(original, str) and re.fullmatch(
            r"cm\d{2}[A-Z]{3}\d{4}bhav\.csv\.zip", original
        ):
            row.update(claim_format="LEGACY_FILENAME_CLAIM", original_filename_claim=original)
        elif isinstance(body.get("used_url"), str) and re.fullmatch(
            r"https://nsearchives\.nseindia\.com/content/cm/BhavCopy_NSE_CM_0_0_0_\d{8}_F_0000\.csv\.zip",
            body["used_url"],
        ):
            row["claim_format"] = "UDIFF_URL_CLAIM"
        if (
            body.get("source_repo_url")
            == "https://github.com/PrivateAccount-01/omega-system---phase-2"
            and isinstance(original, str)
            and body.get("source_repo_relative_path") == "data/raw/bhavcopy/" + original
            and row["claim_format"] == "LEGACY_FILENAME_CLAIM"
        ):
            row["lineage"] = "PHASE2_REPOSITORY_CLAIM"
        if (
            candidate.business_date >= "2020-01-01"
            and row["claim_format"] == "LEGACY_FILENAME_CLAIM"
        ):
            row["era_state"] = "ERA_CONFLICT_2020_REFERENCE_PENDING"
        state, length = inspector(repo / claim, root, names)
        row.update(state=state, filesystem_bytes=length)
        if state == "PRESENT":
            row["state"] = "PRESENT_SIZE_MATCHED" if length == claimed_bytes else "SIZE_MISMATCH"
    except InventoryError as error:
        row["state"] = error.reason_code
    return row


def scan_presence(
    repo: Path,
    root_name: str,
    *,
    expected: ExpectedMetadata,
    source_key: str = SOURCE_KEY,
    limits: ScanLimits | None = None,
    version: int = 1,
    profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if version == 2:
        return _scan_v2(repo, root_name, expected, source_key, limits or ScanLimits(), profile)
    if version != 1:
        raise InventoryError("REPORT_VERSION_UNSUPPORTED")
    if source_key != SOURCE_KEY or root_name not in ROOTS:
        raise InventoryError("SOURCE_SCOPE")
    limits = limits or ScanLimits()
    started = time.monotonic()
    root = repo / ROOTS[root_name]
    validate_root(repo, repo)
    validate_root(root, root)
    try:
        if _manifest_names(root, limits, started) != {r[0] for r in expected.files}:
            raise InventoryError("EXPECTED_CORPUS_MISMATCH")
        rows = []
        names: dict[Path, frozenset[str]] = {}
        total = 0
        for name, digest, length in sorted(expected.files):
            if time.monotonic() - started > limits.max_seconds:
                raise InventoryError("BUDGET")
            raw = read_file(root / name, limits.max_file_bytes)
            total += len(raw)
            if total > limits.max_total_bytes:
                raise InventoryError("BUDGET")
            if len(raw) != length or hashlib.sha256(raw).hexdigest() != digest:
                raise InventoryError("METADATA_PIN_MISMATCH")
            rows.append(_row(repo, root, name, raw, names))
        counts = Counter(r["state"] for r in rows)
        present = counts["PRESENT_SIZE_MATCHED"] + counts["SIZE_MISMATCH"]
        return {
            "schema_version": "od05v.presence/v1",
            "root": root_name,
            "classification": "LSTAT_ONLY_NO_PAYLOAD_ACCESS",
            "manifest_count": len(rows),
            "metadata_bytes_read": total,
            "counts": {
                "manifest_present": len(rows),
                "present": present,
                "payload_path_exists": present
                + counts["HARDLINK_REFUSED"]
                + counts["WRONG_TYPE"]
                + counts["SYMLINK_OR_REPARSE_REFUSED"],
                "regular_file": present + counts["HARDLINK_REFUSED"],
                "size_matches_manifest": counts["PRESENT_SIZE_MATCHED"],
                "missing_payload": counts["MISSING_PAYLOAD"],
                "wrong_type": counts["WRONG_TYPE"],
                "symlink_or_reparse_refused": counts["SYMLINK_OR_REPARSE_REFUSED"],
                "hardlink_refused": counts["HARDLINK_REFUSED"],
            },
            "states": dict(sorted(counts.items())),
            "same_date_observations": len(rows) - len({r["date"] for r in rows}),
            "duplicate_candidate": present
            - len(
                {
                    r["payload_relative"]
                    for r in rows
                    if r["state"] in {"PRESENT_SIZE_MATCHED", "SIZE_MISMATCH"}
                }
            ),
            "samples": [r for day in SAMPLE_DAYS for r in rows if r["date"] == day],
            "quarantine_groups": {
                prefix: {
                    "present": sum(
                        r["date"].startswith(prefix)
                        and r["state"] in {"PRESENT_SIZE_MATCHED", "SIZE_MISMATCH"}
                        for r in rows
                        if r["date"] is not None
                    ),
                    "content_state": "ABSENT_OR_UNCHECKED",
                }
                for prefix in ("2011", "2019", "2020-01", "2024-06", "2024-07", "2025", "2026")
            },
            "rows": rows,
            "payload_bytes_read": 0,
            "market_rows_parsed": 0,
            "market_rows_independently_verified": 0,
            "raw_sha_matches": None,
            "zip_structure_valid": None,
            "real_field_mismatches": None,
            "financial_coverage_denominator": None,
            "synthetic_financial_contribution": 0,
        }
    except ReferenceError as error:
        raise InventoryError(error.reason_code) from None
    except OSError:
        raise InventoryError("METADATA_IO_REFUSED") from None


def _identity(info: os.stat_result) -> tuple[int, ...]:
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_nlink)


def _scan_v2(
    repo: Path,
    label: str,
    expected: ExpectedMetadata,
    source: str,
    limits: ScanLimits,
    profile: dict[str, Any] | None,
) -> dict[str, Any]:
    """One bounded enumeration, grouped ancestor checks and fresh final lstat.

    Trusted owner controlled roots only. Identity checks detect observed changes;
    they do not provide race immunity against a concurrent hostile mount owner.
    Profile timings are external to the deterministic report and semantic digest.
    """
    if source != SOURCE_KEY or label not in ROOTS:
        raise InventoryError("SOURCE_SCOPE")
    started = time.monotonic()
    root = repo / ROOTS[label]
    validate_root(repo, repo)
    validate_root(root, root)
    device = root.lstat().st_dev
    directories: dict[Path, tuple[int, ...]] = {}
    names: dict[Path, frozenset[str]] = {}
    found: set[str] = set()
    count = 0
    reads = 0
    read_seconds = 0.0
    correlation_seconds = 0.0

    def budget() -> None:
        if time.monotonic() - started > limits.max_seconds:
            raise InventoryError("BUDGET")

    def check_directory(path: Path) -> None:
        info = path.lstat()
        if (
            not stat.S_ISDIR(info.st_mode)
            or info.st_dev != device
            or getattr(info, "st_file_attributes", 0) & 0x400
            or _identity(info) != directories[path]
        ):
            raise InventoryError("INPUT_CHANGED")

    try:
        stack = [(root, 0)]
        while stack:
            directory, depth = stack.pop()
            budget()
            if depth > limits.max_depth:
                raise InventoryError("BUDGET")
            info = directory.lstat()
            if (
                not stat.S_ISDIR(info.st_mode)
                or info.st_dev != device
                or getattr(info, "st_file_attributes", 0) & 0x400
            ):
                raise InventoryError("PATH_UNSAFE")
            directories[directory] = _identity(info)
            exact: set[str] = set()
            aliases: set[str] = set()
            with os.scandir(directory) as entries:
                for entry in entries:
                    budget()
                    count += 1
                    if count > limits.max_entries:
                        raise InventoryError("BUDGET")
                    name = relative_name(Path(entry.path).relative_to(root).as_posix())
                    if entry.name.casefold() in aliases:
                        raise InventoryError("PATH_UNSAFE")
                    aliases.add(entry.name.casefold())
                    exact.add(entry.name)
                    # Windows DirEntry.stat omits file identity/link fields on
                    # supported CPython versions. lstat supplies those fields.
                    st = (
                        Path(entry.path).lstat()
                        if os.name == "nt"
                        else entry.stat(follow_symlinks=False)
                    )
                    linked = (
                        stat.S_ISLNK(st.st_mode) or getattr(st, "st_file_attributes", 0) & 0x400
                    )
                    if st.st_dev != device:
                        raise InventoryError("PATH_UNSAFE")
                    if stat.S_ISDIR(st.st_mode) and not linked:
                        stack.append((Path(entry.path), depth + 1))
                    elif name.endswith(".manifest.json"):
                        if linked or not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
                            raise InventoryError("PATH_UNSAFE")
                        found.add(name)
                        if len(found) > limits.max_files:
                            raise InventoryError("BUDGET")
            names[directory] = frozenset(exact)
        enumeration_seconds = time.monotonic() - started
        if found != {r[0] for r in expected.files}:
            raise InventoryError("EXPECTED_CORPUS_MISMATCH")
        last_parent: Path | None = None

        def inspect(
            path: Path, boundary: Path, unused: dict[Path, frozenset[str]]
        ) -> tuple[str, int | None]:
            nonlocal last_parent
            current = boundary
            parts = path.relative_to(boundary).parts
            for index, part in enumerate(parts):
                if current not in names:
                    return "PATH_UNSAFE", None
                if part not in names[current]:
                    return (
                        "PATH_UNSAFE"
                        if any(n.casefold() == part.casefold() for n in names[current])
                        else "MISSING_PAYLOAD"
                    ), None
                target = current / part
                if index < len(parts) - 1:
                    if target not in directories:
                        return "SYMLINK_OR_REPARSE_REFUSED", None
                    current = target
            if path.parent != last_parent:
                check_directory(root)
                for parent in reversed(path.parent.parents):
                    if parent.is_relative_to(root):
                        check_directory(parent)
                check_directory(path.parent)
                last_parent = path.parent
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                return "SYMLINK_OR_REPARSE_REFUSED", None
            if info.st_dev != device:
                return "PATH_UNSAFE", None
            if not stat.S_ISREG(info.st_mode):
                return "WRONG_TYPE", None
            return ("HARDLINK_REFUSED" if info.st_nlink != 1 else "PRESENT"), info.st_size

        rows: list[dict[str, Any]] = []
        total = 0
        for name, digest, length in sorted(expected.files):
            budget()
            tick = time.monotonic()
            raw = read_file(root / name, limits.max_file_bytes)
            reads += 1
            total += len(raw)
            read_seconds += time.monotonic() - tick
            if total > limits.max_total_bytes:
                raise InventoryError("BUDGET")
            if len(raw) != length or hashlib.sha256(raw).hexdigest() != digest:
                raise InventoryError("METADATA_PIN_MISMATCH")
            tick = time.monotonic()
            row = _row(repo, root, name, raw, names, inspect)
            old_state = row["state"]
            regular = old_state in {"PRESENT_SIZE_MATCHED", "SIZE_MISMATCH", "HARDLINK_REFUSED"}
            linked = old_state == "HARDLINK_REFUSED"
            matched = row["filesystem_bytes"] == row["claimed_bytes"] if regular else None
            if linked:
                row["state"] = "PRESENT_HARDLINK_SIZE_MATCHED" if matched else "SIZE_MISMATCH"
            row.update(
                metadata_discovery_state=row["state"],
                path_exists=regular or old_state == "WRONG_TYPE",
                regular_file=regular,
                filesystem_size_matches_manifest=matched,
                link_class="HARDLINKED"
                if linked
                else "SINGLE_LINK"
                if regular
                else "SYMLINK_OR_REPARSE"
                if old_state == "SYMLINK_OR_REPARSE_REFUSED"
                else "UNKNOWN",
                content_inspection_eligibility=False,
                raw_sha_verified=False,
                zip_structure_verified=False,
                publisher_origin_verified=False,
                row_financial_verified=False,
                metadata_sha256=digest,
            )
            rows.append(row)
            correlation_seconds += time.monotonic() - tick
        for directory in directories:
            budget()
            check_directory(directory)
        result: dict[str, Any] = {
            "schema_version": "od05w.presence/v2",
            "root": label,
            "classification": "LSTAT_ONLY_NO_PAYLOAD_ACCESS",
            "manifest_count": len(rows),
            "metadata_bytes_read": total,
            "counts": {
                "manifest_present": len(rows),
                "present": sum(r["regular_file"] for r in rows),
                "regular_file": sum(r["regular_file"] for r in rows),
                "payload_path_exists": sum(r["path_exists"] for r in rows),
                "size_matches_manifest": sum(
                    r["filesystem_size_matches_manifest"] is True for r in rows
                ),
                "hardlinked": sum(r["link_class"] == "HARDLINKED" for r in rows),
                "single_link": sum(r["link_class"] == "SINGLE_LINK" for r in rows),
                "missing_payload": sum(r["state"] == "MISSING_PAYLOAD" for r in rows),
                "content_eligible": 0,
            },
            "states": dict(sorted(Counter(r["state"] for r in rows).items())),
            "rows": rows,
            "payload_bytes_read": 0,
            "market_rows_parsed": 0,
            "market_rows_independently_verified": 0,
            "root_ownership_requirement": "TRUSTED_OWNER_NO_HOSTILE_CONCURRENT_MUTATION",
        }
        result["semantic_sha256"] = hashlib.sha256(
            json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return result
    except ReferenceError as error:
        raise InventoryError(error.reason_code) from None
    except OSError:
        raise InventoryError("METADATA_IO_REFUSED") from None
    finally:
        if profile is not None:
            profile.update(
                max_seconds=limits.max_seconds,
                entries=count,
                metadata_reads=reads,
                enumeration_seconds=locals().get("enumeration_seconds", time.monotonic() - started),
                read_seconds=read_seconds,
                correlation_seconds=correlation_seconds,
                total_seconds=time.monotonic() - started,
            )


class PresenceObservation:
    """Explicit immutable test observation, invalidated by any observed stat change.

    Never a replacement for a fresh original-host inventory. get() returns a new
    decoded value; no caller can modify the retained observation. Native disposable
    trusted-owner metadata/canary snapshots are the intended reuse boundary.
    """

    def __init__(self, repo: Path, label: str, expected: ExpectedMetadata, *, version: int = 2):
        self.repo, self.label, self.expected, self.version = repo, label, expected, version
        self.scan_count = 0
        self._json: str | None = None
        self._identities: dict[Path, tuple[int, ...]] = {}

    def get(self) -> dict[str, Any]:
        root = self.repo / ROOTS[self.label]
        if self._json is None:
            before = self._fingerprint(root)
            report = scan_presence(
                self.repo, self.label, expected=self.expected, version=self.version
            )
            after = self._fingerprint(root)
            if before != after:
                raise InventoryError("INPUT_CHANGED")
            self._identities = after
            self._json = json.dumps(report, sort_keys=True)
            self.scan_count += 1
        elif self._fingerprint(root) != self._identities:
            raise InventoryError("INPUT_CHANGED")
        result: dict[str, Any] = json.loads(self._json)
        return result

    @staticmethod
    def _fingerprint(root: Path) -> dict[Path, tuple[int, ...]]:
        result = {}
        stack = [(root, 0)]
        started = time.monotonic()
        while stack:
            directory, depth = stack.pop()
            if depth > 12:
                raise InventoryError("BUDGET")
            info = directory.lstat()
            if not stat.S_ISDIR(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise InventoryError("INPUT_CHANGED")
            result[directory] = _identity(info)
            with os.scandir(directory) as entries:
                for entry in entries:
                    if len(result) >= 20000 or time.monotonic() - started > 30:
                        raise InventoryError("BUDGET")
                    info = (
                        Path(entry.path).lstat()
                        if os.name == "nt"
                        else entry.stat(follow_symlinks=False)
                    )
                    path = Path(entry.path)
                    result[path] = _identity(info)
                    if (
                        stat.S_ISDIR(info.st_mode)
                        and not getattr(info, "st_file_attributes", 0) & 0x400
                    ):
                        stack.append((path, depth + 1))
        return result
