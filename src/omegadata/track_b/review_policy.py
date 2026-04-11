from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from omegadata.config import settings
from omegadata.domain import ReviewBlockScope


@dataclass(frozen=True)
class ReviewPolicy:
    category: str
    blocks_publication: bool
    scope: ReviewBlockScope
    requires_reprocess: bool


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
            ),
        )


def load_review_policies() -> ReviewPolicySet:
    path = Path(settings.review_policy_path)
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
            )
    return ReviewPolicySet(version=version, policies=policies)
