"""OD05X-R1 Windows admission contracts, with no unverified execution backend.

Host investigation found no approved VM/worker. This module implements reusable
data-free validation and an executable refusal before input access. It does not
claim to configure AppContainer, ACLs, jobs, network policy or Windows Sandbox.
There is intentionally no copy routine, native attack executor or fallback.
"""
from __future__ import annotations

import argparse
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn

import od05x_isolated_runner as linux

_DEVICE = re.compile(r"^(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", re.IGNORECASE)


def windows_relative(name: object) -> str:
    """Portable lexical refusal; not a Windows handle/ACL enforcement claim."""
    if not isinstance(name, str) or not name:
        raise ValueError("WINDOWS_PATH_UNSAFE")
    for part in name.split("/"):
        if (part in {"", ".", ".."} or part.endswith((".", " "))
                or not re.fullmatch(r"[A-Za-z0-9_. =-]+", part) or _DEVICE.match(part)):
            raise ValueError("WINDOWS_PATH_UNSAFE")
    return name


def validate_reviewed_manifest(spec: Mapping[str, Any],
                               approved: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Compare exact code/metadata entries to separately reviewed input pins.

    These mapping arguments are validation inputs, never authority to execute or
    proof of operator approval. The future trusted transport must pin their bytes.
    """
    for candidate in (spec, approved):
        rows = candidate.get("files")
        if not isinstance(rows, list):
            raise ValueError("MANIFEST_SCOPE")
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("MANIFEST_SCOPE")
            windows_relative(row.get("path"))
        linux.entries(candidate)
    if spec != approved:
        raise ValueError("REVIEWED_MANIFEST_MISMATCH")
    return [dict(row) for row in spec["files"]]


@dataclass(frozen=True)
class FileIdentity:
    """Comparison contract only; values must eventually come from native handles.

    Python stat or caller-provided values alone cannot attest a Windows source.
    """
    volume: int
    file_id: int
    size: int
    attributes: int
    links: int
    directory: bool
    mtime_ns: int = 0


def validate_file_identity(current: FileIdentity, before: FileIdentity,
                           *, expected_volume: int) -> None:
    if (current.volume != expected_volume or current.links != 1 or current.directory
            or current.attributes & (0x400 | 0x10) or current.size < 0
            or current.file_id <= 0):
        raise ValueError("WINDOWS_SOURCE_UNSAFE")
    if current != before:
        raise ValueError("WINDOWS_INPUT_CHANGED")


def validate_destination(destination: Path) -> None:
    """No directory is created; native handle-safe creation remains blocked."""
    if (not destination.is_absolute() or destination.exists() or destination.is_symlink()
            or ".." in destination.parts):
        raise ValueError("FRESH_DESTINATION_REQUIRED")
    linux.ancestors(destination.parent)


def reconcile_nodes(nodes: Sequence[str], reviewed: Mapping[str, str]) -> dict[str, str]:
    return linux.classify(nodes, reviewed)


def gatekeeper(*, linux: bool, windows314: bool, windows311: bool,
               windows_containment: bool) -> dict[str, Any]:
    # Boolean software observations cannot certify this absent Windows backend.
    # Until real native attestation/execution exists, declarations fail closed.
    return {"G1": "PASS" if linux else "BLOCKED",
            "G2": "BLOCKED", "G3": "BLOCKED", "G4": "BLOCKED_REAL_DATA",
            "windows_runtime_results_supplied": [windows314, windows311],
            "windows_containment_claim_supplied": windows_containment,
            "native_windows_backend": "NOT_IMPLEMENTED_OS_CAPABILITY_BLOCKED",
            "incident": "PENDING_HUMAN_OWNER_REVIEW", "verified_market_rows": 0,
            "safe_engineering": "BLOCKED"}


def launch_windows(manifest: Path, manifest_sha256: str, destination: Path,
                   *, configuration: Mapping[str, Any] | None) -> NoReturn:
    """Never read manifest/configuration paths, create output or launch a child.

    Merely supplying a plausible VM/probe report must not unlock execution. No
    security backend is selected from a user-controlled string or environment.
    """
    if configuration is None:
        raise ValueError("OS_ISOLATION_CAPABILITY_BLOCKED")
    raise ValueError("UNVERIFIED_WINDOWS_BOUNDARY")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        launch_windows(args.manifest, args.manifest_sha256, args.output, configuration=None)
    except ValueError as error:
        print(json.dumps({"state": "REFUSED", "reason": str(error),
                          "manifest_read": False, "destination_created": False,
                          "copied_files": 0}))
        raise SystemExit(2) from None
