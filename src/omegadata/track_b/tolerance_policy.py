from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from omegadata.config import settings


@dataclass(frozen=True)
class TolerancePolicyEntry:
    liquidity_bucket: str
    source_quality: str
    field: str
    imputed: bool
    tolerance_pct: str
    warning_breach_rate_limit: float
    fail_breach_rate_limit: float


@dataclass(frozen=True)
class TolerancePolicySet:
    version: str
    generated_at: str | None
    entries: tuple[TolerancePolicyEntry, ...]

    def match(
        self,
        *,
        liquidity_bucket: str,
        source_quality: str,
        field: str,
        imputed: bool,
    ) -> TolerancePolicyEntry | None:
        exact = next(
            (
                entry
                for entry in self.entries
                if entry.liquidity_bucket == liquidity_bucket
                and entry.source_quality == source_quality
                and entry.field == field
                and entry.imputed is imputed
            ),
            None,
        )
        if exact is not None:
            return exact
        return next(
            (
                entry
                for entry in self.entries
                if entry.liquidity_bucket == liquidity_bucket
                and entry.source_quality == source_quality
                and entry.field == field
                and entry.imputed is False
            ),
            None,
        )


_CACHE: tuple[tuple[str, int, int], TolerancePolicySet] | None = None


def invalidate_tolerance_policy_cache() -> None:
    global _CACHE
    _CACHE = None


def _read_policy(path: Path) -> TolerancePolicySet:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_entries = payload.get("entries", [])
    entries: list[TolerancePolicyEntry] = []
    if isinstance(raw_entries, list):
        for raw in raw_entries:
            if not isinstance(raw, dict):
                continue
            entries.append(
                TolerancePolicyEntry(
                    liquidity_bucket=str(raw.get("liquidity_bucket", "")).strip(),
                    source_quality=str(raw.get("source_quality", "")).strip(),
                    field=str(raw.get("field", "")).strip(),
                    imputed=bool(raw.get("imputed", False)),
                    tolerance_pct=str(raw.get("tolerance_pct", "0.0010")).strip(),
                    warning_breach_rate_limit=float(raw.get("warning_breach_rate_limit", 0.08)),
                    fail_breach_rate_limit=float(raw.get("fail_breach_rate_limit", 0.02)),
                )
            )
    return TolerancePolicySet(
        version=str(payload.get("version", "unknown")),
        generated_at=None if payload.get("generated_at") is None else str(payload.get("generated_at")),
        entries=tuple(entries),
    )


def load_tolerance_policy(*, force_reload: bool = False) -> TolerancePolicySet | None:
    global _CACHE

    path = Path(settings.cross_source_tolerance_policy_path).resolve()
    if not path.exists():
        return None
    stat = path.stat()
    cache_key = (str(path), stat.st_mtime_ns, stat.st_size)
    if force_reload:
        _CACHE = None
    if _CACHE is not None:
        cached_key, cached_value = _CACHE
        if cached_key == cache_key:
            return cached_value
    policy = _read_policy(path)
    _CACHE = (cache_key, policy)
    return policy
