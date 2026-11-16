"""Stdlib-only metadata identity oracle. Never opens market payload paths."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def pins(root: Path) -> tuple[tuple[str, str, int], ...]:
    return tuple(
        (
            p.relative_to(root).as_posix(),
            hashlib.sha256(p.read_bytes()).hexdigest(),
            p.stat().st_size,
        )
        for p in sorted(root.rglob("*.manifest.json"))
    )


def digest(entries: tuple[tuple[str, str, int], ...]) -> str:
    return hashlib.sha256(
        b"od05t.metadata/v1\n"
        + json.dumps(sorted(entries), separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def verify(root: Path, expected: tuple[tuple[str, str, int], ...]) -> str:
    actual = pins(root)
    if not expected or actual != tuple(sorted(expected)):
        raise ValueError("ORACLE_CORPUS_MISMATCH")
    return digest(actual)
