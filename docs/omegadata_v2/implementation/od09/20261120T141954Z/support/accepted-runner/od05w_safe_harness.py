"""Exact, reviewed code/metadata clean-room copy contract. No data discovery.

The host runner must activate guards before invoking this API. A guard receipt
reports OS isolation separately; Python audit hooks are not a kernel sandbox.
This module never invokes or falls back to any historical fixture-copy helper.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import stat
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from omegadata.parsers.archive_candidate_inventory import relative_name

DENIED = {
    "zip",
    "csv",
    "gz",
    "parquet",
    "db",
    "sqlite",
    "sqlite3",
    "bin",
    "key",
    "pem",
    "pfx",
    "crt",
    "rev",
}
CLASSES = {
    "CODE": {".py"},
    "STATIC_CONFIG": {".json", ".toml"},
    "LOCAL_META": {".json"},
    "EXISTING_REGRESSION_METADATA": {".json"},
    "STATIC_UI": {".css", ".html", ".js"},
    "DOCUMENTATION": {".md"},
}


@dataclass(frozen=True)
class CopyEntry:
    path: str
    size: int
    identity: tuple[int, ...]
    classification: str


def _identity(info: os.stat_result) -> tuple[int, ...]:
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_nlink)


def preflight(
    root: Path, names: Sequence[str], approved: Mapping[str, str]
) -> tuple[CopyEntry, ...]:
    """Validate the ENTIRE exact list using metadata before opening any input."""
    if not root.is_absolute() or not names or len(names) > 10000:
        raise ValueError("COPY_SCOPE")
    if (
        str(root).startswith(("//", "\\\\"))
        or ".." in root.parts
        or any(
            part.casefold() in {"gnupg", "private-keys-v1.d", "openpgp-revocs.d"}
            or part.casefold().startswith((".env", ".venv"))
            for part in root.parts
        )
    ):
        raise ValueError("COPY_PATH_UNSAFE")
    for parent in (*reversed(root.parents), root):
        info = parent.lstat()
        if (
            not stat.S_ISDIR(info.st_mode)
            or stat.S_ISLNK(info.st_mode)
            or getattr(info, "st_file_attributes", 0) & 0x400
        ):
            raise ValueError("COPY_PATH_UNSAFE")
    result = []
    seen: set[str] = set()
    device = root.lstat().st_dev
    for name in names:
        relative_name(name)
        parts = Path(name).parts
        classification = approved.get(name)
        if (
            name.casefold() in seen
            or classification not in CLASSES
            or Path(name).suffix not in CLASSES[classification]
            or any(
                p.casefold() in {"gnupg", "artifacts", "private-keys-v1.d", "openpgp-revocs.d"}
                or p.startswith((".env", ".venv"))
                for p in parts
            )
            or any(p.casefold() in DENIED for p in Path(name).name.split("."))
            or any(p.casefold() in {"od05r", "od05v"} for p in parts)
            or (
                "data" in parts
                and not (classification == "LOCAL_META" and name.endswith(".manifest.json"))
            )
        ):
            raise ValueError("COPY_SCOPE")
        seen.add(name.casefold())
        current = root
        for part in parts:
            # Case aliases and linked ancestors are not allowed.
            if part not in {p.name for p in current.iterdir()}:
                raise ValueError("COPY_PATH_UNSAFE")
            current /= part
            info = current.lstat()
            if (
                stat.S_ISLNK(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & 0x400
                or info.st_dev != device
            ):
                raise ValueError("COPY_PATH_UNSAFE")
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 4_000_000:
            raise ValueError("COPY_PATH_UNSAFE")
        result.append(CopyEntry(name, info.st_size, _identity(info), classification))
    return tuple(result)


def active_guard() -> dict[str, Any]:
    # An environment value alone is not authorization: the copy function also
    # requires the live guard callback and probes its denial behavior.
    return {
        "active": os.environ.get("OD05W_GUARD_ACTIVE") == "1",
        "os_isolation": "NOT_ESTABLISHED",
    }


def copy_exact(
    root: Path,
    destination: Path,
    names: Sequence[str],
    approved: Mapping[str, str],
    *,
    guard: Mapping[str, Any] | None,
    expected: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    if guard is None or guard.get("active") is not True or not callable(guard.get("probe")):
        raise ValueError("GUARD_REQUIRED")
    if guard["probe"]() is not True:
        raise ValueError("GUARD_PROBE_FAILED")
    if (
        not destination.is_absolute()
        or destination.exists()
        or destination.is_relative_to(root)
        or root.is_relative_to(destination)
    ):
        raise ValueError("FRESH_EXTERNAL_DESTINATION_REQUIRED")
    entries = preflight(root, names, approved)
    if expected is None or set(expected) != set(names):
        raise ValueError("REVIEWED_PINS_REQUIRED")
    # Destination is created only after full preflight, but remains forensic
    # evidence if a later input changes. No cleanup/reuse fallback exists.
    destination.mkdir(mode=0o700, exist_ok=False)
    copied = []
    for item in entries:
        source = root / item.path
        if _identity(source.lstat()) != item.identity:
            raise ValueError("COPY_INPUT_CHANGED")
        fd = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(fd, "rb") as stream:
            if _identity(os.fstat(stream.fileno())) != item.identity:
                raise ValueError("COPY_INPUT_CHANGED")
            raw = stream.read(item.size + 1)
        digest = hashlib.sha256(raw).hexdigest()
        if (
            len(raw) != item.size
            or digest != expected[item.path]
            or _identity(source.lstat()) != item.identity
        ):
            raise ValueError("COPY_INPUT_CHANGED")
        if item.classification == "CODE":
            ast.parse(raw.decode("utf-8"))
        elif item.classification in {"LOCAL_META", "EXISTING_REGRESSION_METADATA"}:
            json.loads(raw)
        output = destination / item.path
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("xb") as stream:
            stream.write(raw)
        if hashlib.sha256(output.read_bytes()).hexdigest() != digest:
            raise ValueError("COPY_DESTINATION_MISMATCH")
        copied.append(
            {"path": item.path, "sha256": digest, "bytes": len(raw), "class": item.classification}
        )
    return {
        "schema_version": "od05w.copy/v1",
        "utc": datetime.now(UTC).isoformat(),
        "files": copied,
        "file_count": len(copied),
        "bytes": sum(r["bytes"] for r in copied),
        "guard_before_copy": True,
        "os_isolation": guard.get("os_isolation", "UNKNOWN"),
        "payload_files_copied": 0,
    }


def classify_tests(nodes: Sequence[str], inventory: Mapping[str, str]) -> dict[str, str]:
    if (
        len(set(nodes)) != len(nodes)
        or set(nodes) != set(inventory)
        or any(c not in {"A", "B", "C"} for c in inventory.values())
    ):
        raise ValueError("TEST_INVENTORY_MISMATCH")
    return {n: inventory[n] for n in sorted(nodes)}


def blocked_inputs(inventory: Mapping[str, str]) -> dict[str, str]:
    return {
        n: "BLOCKED_INPUT" if c == "B" else "BLOCKED_REAL_DATA"
        for n, c in inventory.items()
        if c in {"B", "C"}
    }


def gate_summary(diagnostic: Mapping[str, int], *, engineering_exit: int) -> dict[str, str]:
    return {
        "diagnostic": "FAIL" if diagnostic.get("failed", 0) else "PASS",
        "engineering": "PASS" if engineering_exit == 0 else "FAIL",
    }
