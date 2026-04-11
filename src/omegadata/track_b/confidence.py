from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from omegadata.db.models import PriceRecord
from omegadata.domain import DiscontinuityCategory, QueryContext


@dataclass(frozen=True)
class ConfidenceInputs:
    is_secondary_source: bool
    cross_validation_available: bool
    cross_validation_discrepancy_pct: Decimal | None
    has_medium_ca: bool
    has_low_ca: bool
    rights_subscription_fallback_zero: bool
    is_gap_fill: bool
    is_reconstructed_universe: bool
    discontinuity_category: DiscontinuityCategory | None


class ConfidenceScorer:
    THRESHOLDS: dict[QueryContext, Decimal] = {
        QueryContext.SIGNAL_COMPUTATION: Decimal("0.75"),
        QueryContext.REGIME_CLASSIFICATION: Decimal("0.85"),
        QueryContext.LIVE_SIGNAL: Decimal("0.90"),
        QueryContext.BACKTEST: Decimal("0.70"),
        QueryContext.RESEARCH: Decimal("0.50"),
        QueryContext.AUDIT: Decimal("0.00"),
    }

    def compute_score(self, inputs: ConfidenceInputs) -> Decimal:
        score = Decimal("1.00")
        if inputs.is_secondary_source:
            score -= Decimal("0.10")
        if not inputs.cross_validation_available:
            score -= Decimal("0.10")
        elif inputs.cross_validation_discrepancy_pct is not None:
            discrepancy = inputs.cross_validation_discrepancy_pct
            if Decimal("0.0005") <= discrepancy <= Decimal("0.005"):
                score -= Decimal("0.05")
            elif discrepancy > Decimal("0.005"):
                score -= Decimal("0.25")
        if inputs.has_medium_ca:
            score -= Decimal("0.15")
        if inputs.has_low_ca:
            score -= Decimal("0.30")
        if inputs.rights_subscription_fallback_zero:
            score -= Decimal("0.05")
        if inputs.is_gap_fill:
            score -= Decimal("0.20")
        if inputs.is_reconstructed_universe:
            score -= Decimal("0.10")
        if inputs.discontinuity_category == DiscontinuityCategory.B:
            score -= Decimal("0.50")
        if inputs.discontinuity_category == DiscontinuityCategory.C:
            score -= Decimal("1.00")
        if score < Decimal("0.00"):
            score = Decimal("0.00")
        return score.quantize(Decimal("0.01"))

    def enforce_context(self, score: Decimal, context: QueryContext) -> bool:
        return score >= self.THRESHOLDS[context]

    def filter_records(
        self,
        records: list[PriceRecord],
        context: QueryContext,
    ) -> tuple[list[PriceRecord], int, tuple[date, date] | None]:
        min_score = self.THRESHOLDS[context]
        kept = [r for r in records if Decimal(str(r.confidence_score)) >= min_score]
        excluded = [r for r in records if Decimal(str(r.confidence_score)) < min_score]
        if not excluded:
            return kept, 0, None
        dates = sorted(r.trade_date for r in excluded)
        return kept, len(excluded), (dates[0], dates[-1])

    def monthly_report(self, session: Session, year: int, month: int) -> dict[str, object]:
        rows = session.scalars(select(PriceRecord)).all()
        in_month = [
            r
            for r in rows
            if r.trade_date.year == year and r.trade_date.month == month
        ]
        if not in_month:
            return {
                "records": 0,
                "histogram": {},
                "below_thresholds": {},
                "zero_confidence_count": 0,
            }

        histogram: dict[str, int] = {}
        for row in in_month:
            bucket = f"{(Decimal(str(row.confidence_score)) * 10).to_integral_value() / 10:.1f}"
            histogram[bucket] = histogram.get(bucket, 0) + 1

        below = {
            "0.90": sum(1 for r in in_month if Decimal(str(r.confidence_score)) < Decimal("0.90")),
            "0.80": sum(1 for r in in_month if Decimal(str(r.confidence_score)) < Decimal("0.80")),
            "0.70": sum(1 for r in in_month if Decimal(str(r.confidence_score)) < Decimal("0.70")),
            "0.50": sum(1 for r in in_month if Decimal(str(r.confidence_score)) < Decimal("0.50")),
        }
        zero_conf = sum(1 for r in in_month if Decimal(str(r.confidence_score)) == Decimal("0.00"))

        return {
            "records": len(in_month),
            "histogram": histogram,
            "below_thresholds": below,
            "zero_confidence_count": zero_conf,
        }
