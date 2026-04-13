from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from omegadata.config import settings
from omegadata.domain import ReviewBlockScope
from omegadata.track_a.monitoring import REVIEW_POLICY_RELOAD_COUNTER


@dataclass(frozen=True)
class ReviewPolicy:
    category: str
    blocks_publication: bool
    scope: ReviewBlockScope
    requires_reprocess: bool
    triage_instructions: str = ""


@dataclass(frozen=True)
class ReviewPolicySet:
    version: str
    policies: dict[str, ReviewPolicy]

    def for_category(self, category: str) -> ReviewPolicy:
        return self.policies.get(
            category,
            ReviewPolicy(
                category=category,
                blocks_publication=True,
                scope=ReviewBlockScope.RECORD,
                requires_reprocess=False,
                triage_instructions="Review the evidence, record a clear disposition, and close the review explicitly.",
            ),
        )


def _read_policy_set(path: Path) -> ReviewPolicySet:
    payload = json.loads(path.read_text(encoding="utf-8"))
    version = str(payload.get("version", "unknown"))
    raw_policies = payload.get("policies", {})
    policies: dict[str, ReviewPolicy] = {}
    if isinstance(raw_policies, dict):
        for category, raw in raw_policies.items():
            if not isinstance(raw, dict):
                continue
            policies[category] = ReviewPolicy(
                category=category,
                blocks_publication=bool(raw.get("blocks_publication", True)),
                scope=ReviewBlockScope(str(raw.get("scope", ReviewBlockScope.RECORD.value))),
                requires_reprocess=bool(raw.get("requires_reprocess", False)),
                triage_instructions=str(raw.get("triage_instructions", "")),
            )
    return ReviewPolicySet(version=version, policies=policies)


_POLICY_CACHE: tuple[tuple[str, int, int], ReviewPolicySet] | None = None


def invalidate_review_policy_cache() -> None:
    global _POLICY_CACHE
    _POLICY_CACHE = None
    REVIEW_POLICY_RELOAD_COUNTER.labels(reason="manual_invalidate").inc()


def load_review_policies(*, force_reload: bool = False) -> ReviewPolicySet:
    global _POLICY_CACHE

    path = Path(settings.review_policy_path).resolve()
    stat = path.stat()
    cache_key = (str(path), stat.st_mtime_ns, stat.st_size)

    if force_reload:
        _POLICY_CACHE = None
        REVIEW_POLICY_RELOAD_COUNTER.labels(reason="force_reload").inc()

    if _POLICY_CACHE is not None:
        cached_key, cached_value = _POLICY_CACHE
        if cached_key == cache_key:
            return cached_value

    policy_set = _read_policy_set(path)
    reason = "mtime_change" if _POLICY_CACHE is not None else "cold_load"
    REVIEW_POLICY_RELOAD_COUNTER.labels(reason=reason).inc()
    _POLICY_CACHE = (cache_key, policy_set)
    return policy_set
