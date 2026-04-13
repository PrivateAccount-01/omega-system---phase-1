from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from omegadata.config import settings


@dataclass(frozen=True)
class MatchingPolicy:
    version: str
    pair_max_gap_days: int
    related_candidate_gap_days: int
    high_similarity_threshold: int
    ambiguous_similarity_threshold: int
    pair_min_score: int
    economic_overlap_bonus: int


_CACHE: tuple[tuple[str, int, int], MatchingPolicy] | None = None


def invalidate_matching_policy_cache() -> None:
    global _CACHE
    _CACHE = None


def _read_policy(path: Path) -> MatchingPolicy:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return MatchingPolicy(
        version=str(payload.get("version", "unknown")),
        pair_max_gap_days=int(payload.get("pair_max_gap_days", 30)),
        related_candidate_gap_days=int(payload.get("related_candidate_gap_days", 10)),
        high_similarity_threshold=int(payload.get("high_similarity_threshold", 60)),
        ambiguous_similarity_threshold=int(payload.get("ambiguous_similarity_threshold", 35)),
        pair_min_score=int(payload.get("pair_min_score", 1)),
        economic_overlap_bonus=int(payload.get("economic_overlap_bonus", 8)),
    )


def load_matching_policy(*, force_reload: bool = False) -> MatchingPolicy:
    global _CACHE

    path = Path(settings.corporate_action_matching_policy_path).resolve()
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
