"""Explicit compatibility inventory. No legacy service instantiation or side effects."""

from decimal import Decimal

from omegadata.track_b.tolerance_policy import TolerancePolicySet

REUSE_DECISIONS = {
    "CrossSourceValidator": "LEGACY_RISK_RETAINED",
    "ConfidenceScorer": "WRAP",
    "TolerancePolicySet": "WRAP",
    "ManualReviewService": "OPT_IN_REPLACEMENT",
    "CorporateActionMatcher": "REUSE",
    "SourceDependentCalibration": "BLOCKED_EXTERNAL",
}


def legacy_tolerance_snapshot(
    policy: TolerancePolicySet,
) -> tuple[tuple[str, str, str, bool, Decimal], ...]:
    """Convert an already supplied immutable legacy policy. No settings/path loading."""
    return tuple(
        (e.liquidity_bucket, e.source_quality, e.field, e.imputed, Decimal(e.tolerance_pct))
        for e in policy.entries
    )
