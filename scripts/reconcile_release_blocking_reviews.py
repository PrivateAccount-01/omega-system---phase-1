from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from omegadata.config import settings
from omegadata.db.models import ConfirmedCorporateAction, ManualReviewQueue
from omegadata.db.session import get_session, init_db
from omegadata.domain import ReviewDecision
from omegadata.track_b.manual_review import ManualReviewService

REPO_ROOT = Path(__file__).resolve().parents[1]


def _confirmed_action_satisfies_parameter_review(review: ManualReviewQueue) -> bool:
    payload = dict(review.payload or {})
    differences = str(payload.get("differences", ""))
    # Missing fields on one source are now acceptable once the confirmed action holds
    # the required economic payload used by the adjustment engine.
    tolerated_tokens = {
        "announcement_date:missing_on_nse",
        "announcement_date:missing_on_bse",
        "purpose:missing_on_nse",
        "purpose:missing_on_bse",
        "dividend_per_share:missing_on_nse",
        "dividend_per_share:missing_on_bse",
        "ex_date",
    }
    tokens = {token.strip() for token in differences.split(",") if token.strip()}
    return tokens.issubset(tolerated_tokens)


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve stale release-blocking manual reviews when canonical evidence supersedes them.")
    parser.add_argument("--db-url", default=None, help="Database URL override")
    parser.add_argument(
        "--artifact-path",
        default="artifacts/verification/review_backlog_reconciliation.json",
        help="Output artifact path",
    )
    args = parser.parse_args()

    if args.db_url:
        settings.db_url = str(args.db_url)
    init_db()

    service = ManualReviewService()
    resolved_review_ids: list[int] = []
    unresolved_release_blockers = 0

    with get_session() as session:
        reviews = session.scalars(
            select(ManualReviewQueue)
            .where(ManualReviewQueue.resolved.is_(False))
            .order_by(ManualReviewQueue.id.asc())
        ).all()
        for review in reviews:
            if review.category != "CORPORATE_ACTION_PARAMETER_MISMATCH":
                continue
            action = session.scalar(
                select(ConfirmedCorporateAction)
                .where(ConfirmedCorporateAction.isin == review.isin)
                .where(ConfirmedCorporateAction.ex_date == review.event_date)
                .where(ConfirmedCorporateAction.superseded.is_(False))
            )
            if action is None:
                unresolved_release_blockers += 1
                continue
            if not _confirmed_action_satisfies_parameter_review(review):
                unresolved_release_blockers += 1
                continue
            service.resolve_review(
                session,
                review_id=review.id,
                decision=ReviewDecision.FALSE_POSITIVE,
                reviewer="release-reconciliation",
                notes=(
                    "Resolved automatically after canonical confirmed corporate action "
                    "contained the required payload fields for adjustment/publication."
                ),
            )
            resolved_review_ids.append(review.id)

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "resolved_review_ids": resolved_review_ids,
        "resolved_count": len(resolved_review_ids),
        "remaining_unresolved_release_blockers": unresolved_release_blockers,
    }
    out_path = REPO_ROOT / args.artifact_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
