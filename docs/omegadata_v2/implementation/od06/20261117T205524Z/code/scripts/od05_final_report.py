"""Pinned data-free evidence renderer, callable only in the live Linux boundary.

No Git, subprocess, directory discovery outside the explicit bundle, dataset
read, fallback helper, cleanup, clock or financial-approval logic exists here.
The launcher must mount only the reviewed data-free bundle and public runtime.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path
from typing import Any

import od05x_isolated_runner as isolation


def boundary() -> dict[str, Any]:
    return isolation.assert_boundary()


def _json(raw: bytes) -> Any:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("REPORT_DUPLICATE_KEY")
            result[key] = value
        return result

    def constant(value: str) -> Any:
        raise ValueError("REPORT_JSON_UNSAFE")

    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_constant=constant)
    except (UnicodeError, RecursionError) as error:
        raise ValueError("REPORT_JSON_UNSAFE") from error


def _read(root: Path, name: str, expected: dict[str, Any] | None) -> bytes:
    path = root / name
    before = isolation.identity(path)
    if not stat.S_ISREG(before[2]) or before[5] != 1 or before[3] > 4_000_000:
        raise ValueError("REPORT_FILE_UNSAFE")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        if isolation.stat_identity(os.fstat(stream.fileno())) != before:
            raise ValueError("REPORT_INPUT_CHANGED")
        raw = stream.read(4_000_001)
        if isolation.stat_identity(os.fstat(stream.fileno())) != before:
            raise ValueError("REPORT_INPUT_CHANGED")
    if isolation.identity(path) != before or len(raw) != before[3]:
        raise ValueError("REPORT_INPUT_CHANGED")
    if expected is not None and (
        set(expected) != {"bytes", "sha256"} or type(expected["bytes"]) is not int
        or expected["bytes"] != len(raw)
        or hashlib.sha256(raw).hexdigest() != expected["sha256"]
    ):
        raise ValueError("REPORT_PIN_MISMATCH")
    return raw


def render(root: Path, manifest_sha256: str, output: Path,
           *, capability: dict[str, Any] | None) -> dict[str, Any]:
    if capability is None or capability != boundary():
        raise ValueError("REPORT_BOUNDARY_REQUIRED")
    if (not root.is_absolute() or ".." in root.parts or not root.is_relative_to(Path("/work"))
            or not re.fullmatch(r"[a-f0-9]{64}", manifest_sha256)):
        raise ValueError("REPORT_SCOPE")
    isolation.ancestors(root)
    original_root = isolation.identity(root)
    raw = _read(root, "manifest.json", None)
    if len(raw) > 65536 or hashlib.sha256(raw).hexdigest() != manifest_sha256:
        raise ValueError("REPORT_MANIFEST_PIN")
    spec = _json(raw)
    if (not isinstance(spec, dict) or set(spec) != {"schema_version", "files"}
            or spec["schema_version"] != "od05.final-report/v1"
            or not isinstance(spec["files"], dict) or set(spec["files"]) != {"summary.json"}):
        raise ValueError("REPORT_MANIFEST_SCOPE")
    # Enumeration is bounded to this already approved, flat input bundle only.
    with os.scandir(root) as entries:
        names = set()
        for entry in entries:
            names.add(entry.name)
            if len(names) > 2:
                raise ValueError("REPORT_UNEXPECTED_INPUT")
    if names != {"manifest.json", "summary.json"}:
        raise ValueError("REPORT_UNEXPECTED_INPUT")
    body = _json(_read(root, "summary.json", spec["files"]["summary.json"]))
    if (not isinstance(body, dict) or set(body) != {"artifacts"}
            or not isinstance(body["artifacts"], dict) or not 1 <= len(body["artifacts"]) <= 32):
        raise ValueError("REPORT_BODY_SCOPE")
    outputs = {}
    aliases = set()
    for name, content in body["artifacts"].items():
        if (not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_-]+\.(md|json)", name)
                or name.casefold() in aliases or name.split(".")[0].casefold() in {"con", "nul", "aux", "prn"}
                or not isinstance(content, str) or len(content.encode()) > 4_000_000):
            raise ValueError("REPORT_OUTPUT_SCOPE")
        aliases.add(name.casefold())
        outputs[name] = content.encode()
    if isolation.identity(root) != original_root:
        raise ValueError("REPORT_INPUT_CHANGED")
    if (not output.is_absolute() or not output.is_relative_to(Path("/work"))
            or output.is_relative_to(root) or root.is_relative_to(output)
            or output.exists() or output.is_symlink() or ".." in output.parts):
        raise ValueError("REPORT_FRESH_OUTPUT_REQUIRED")
    isolation.ancestors(output.parent)
    output.mkdir(mode=0o700)
    for name, raw in outputs.items():
        with (output / name).open("xb") as stream:
            stream.write(raw)
    return {"schema_version": "od05.final-report.receipt/v1", "files": sorted(outputs),
            "manifest_sha256": manifest_sha256,
            "sha256": {n: hashlib.sha256(raw).hexdigest() for n, raw in outputs.items()},
            "boundary": capability, "git_calls": 0, "original_repository_mounted": False}
