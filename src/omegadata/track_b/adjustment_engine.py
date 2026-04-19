from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal, getcontext

from sqlalchemy import select
from sqlalchemy.orm import Session

from omegadata.db.models import ConfirmedCorporateAction, PriceRecord
from omegadata.domain import CorporateActionType, Exchange

getcontext().prec = 28


@dataclass(frozen=True)
class AdjustmentFactor:
    price_factor: Decimal
    volume_factor: Decimal
    metadata: dict[str, str | bool]


class PriceAdjustmentEngine:
    def recompute_adjusted_series(self, session: Session, isin: str, exchange: Exchange = Exchange.NSE) -> int:
        self.refresh_demerger_actuals(session=session, isin=isin, exchange=exchange)

        prices = session.scalars(
            select(PriceRecord)
            .where(PriceRecord.isin == isin)
            .where(PriceRecord.exchange == exchange)
            .order_by(PriceRecord.trade_date.asc())
        ).all()
        if not prices:
            return 0

        actions = session.scalars(
            select(ConfirmedCorporateAction)
            .where(ConfirmedCorporateAction.isin == isin)
            .where(ConfirmedCorporateAction.superseded.is_(False))
            .order_by(ConfirmedCorporateAction.ex_date.asc())
        ).all()

        factors_by_action_id: dict[int, AdjustmentFactor] = {}
        by_date = {p.trade_date: p for p in prices}
        for action in actions:
            factor = self._compute_factor(action, by_date)
            if factor is not None:
                factors_by_action_id[action.id] = factor

        for row in prices:
            cumulative_price = Decimal("1")
            cumulative_volume = Decimal("1")
            chain: list[dict[str, str | float | int | bool]] = []
            for action in actions:
                if action.ex_date is None or row.trade_date >= action.ex_date:
                    continue
                factor = factors_by_action_id.get(action.id)
                if factor is None:
                    continue
                cumulative_price *= factor.price_factor
                cumulative_volume *= factor.volume_factor
                chain.append(
                    {
                        "corporate_action_id": action.id,
                        "action_type": action.action_type.value,
                        "ex_date": action.ex_date.isoformat(),
                        "adjustment_factor_applied": float(factor.price_factor),
                        "cumulative_factor_at_this_point": float(cumulative_price),
                        **factor.metadata,
                    }
                )

            raw_open = Decimal(str(row.open_price))
            raw_high = Decimal(str(row.high_price))
            raw_low = Decimal(str(row.low_price))
            raw_close = Decimal(str(row.close_price))
            raw_volume = Decimal(str(row.volume))
            row.adjusted_open_price = (raw_open * cumulative_price).quantize(
                Decimal("0.000001"),
                rounding=ROUND_HALF_UP,
            )
            row.adjusted_high_price = (raw_high * cumulative_price).quantize(
                Decimal("0.000001"),
                rounding=ROUND_HALF_UP,
            )
            row.adjusted_low_price = (raw_low * cumulative_price).quantize(
                Decimal("0.000001"),
                rounding=ROUND_HALF_UP,
            )
            row.adjusted_close_price = (raw_close * cumulative_price).quantize(
                Decimal("0.000001"),
                rounding=ROUND_HALF_UP,
            )
            row.adjusted_volume = (raw_volume * cumulative_volume).quantize(
                Decimal("0.0001"),
                rounding=ROUND_HALF_UP,
            )
            row.cumulative_price_factor = cumulative_price
            row.cumulative_volume_factor = cumulative_volume
            row.adjustment_chain = chain

        return len(prices)

    def refresh_demerger_actuals(
        self,
        session: Session,
        isin: str,
        exchange: Exchange = Exchange.NSE,
    ) -> int:
        actions = session.scalars(
            select(ConfirmedCorporateAction)
            .where(ConfirmedCorporateAction.isin == isin)
            .where(ConfirmedCorporateAction.action_type == CorporateActionType.DEMERGER_PARENT)
            .where(ConfirmedCorporateAction.superseded.is_(False))
            .order_by(ConfirmedCorporateAction.ex_date.asc())
        ).all()

        refreshed = 0
        for action in actions:
            params = dict(action.parameters or {})
            if params.get("actual_spinoff_listing_price") not in (None, ""):
                continue

            spinoff_isin = str(params.get("spinoff_isin") or "").strip()
            if not spinoff_isin or action.ex_date is None:
                continue

            candidates = session.scalars(
                select(PriceRecord)
                .where(PriceRecord.isin == spinoff_isin)
                .where(PriceRecord.trade_date >= action.ex_date)
                .order_by(PriceRecord.trade_date.asc())
            ).all()
            if not candidates:
                continue

            first_trade_date = candidates[0].trade_date
            same_day = [row for row in candidates if row.trade_date == first_trade_date]
            chosen = next((row for row in same_day if row.exchange == exchange), same_day[0])

            params["actual_spinoff_listing_price"] = str(chosen.close_price)
            params["actual_spinoff_listing_date"] = chosen.trade_date.isoformat()
            params["actual_spinoff_exchange"] = chosen.exchange.value
            params["demerger_adjustment_stage"] = "FINAL"
            action.parameters = params
            refreshed += 1

        return refreshed

    def _compute_factor(
        self,
        action: ConfirmedCorporateAction,
        by_date: dict[date, PriceRecord],
    ) -> AdjustmentFactor | None:
        action_type = action.action_type
        params = action.parameters

        if action_type in {
            CorporateActionType.DIVIDEND_CASH,
            CorporateActionType.DIVIDEND_SPECIAL,
            CorporateActionType.BUYBACK_OPEN_MARKET,
            CorporateActionType.BUYBACK_TENDER,
            CorporateActionType.SUSPENSION,
            CorporateActionType.REINSTATEMENT,
            CorporateActionType.RECLASSIFICATION,
            CorporateActionType.MERGER_ACQUIRER,
            CorporateActionType.MERGER_TARGET,
            CorporateActionType.DELISTING_VOLUNTARY,
            CorporateActionType.DELISTING_REGULATORY,
            CorporateActionType.DELISTING_MERGER,
        }:
            return None

        if action_type == CorporateActionType.BONUS:
            numerator = Decimal(str(params.get("bonus_ratio_numerator", "0")))
            denominator = Decimal(str(params.get("bonus_ratio_denominator", "1")))
            if denominator <= 0:
                return None
            ratio = numerator / denominator
            price_factor = Decimal("1") / (Decimal("1") + ratio)
            volume_factor = Decimal("1") / price_factor
            return AdjustmentFactor(
                price_factor=price_factor,
                volume_factor=volume_factor,
                metadata=self._base_metadata(action),
            )

        if action_type in {CorporateActionType.SPLIT, CorporateActionType.SPLIT_REVERSE}:
            old_fv = Decimal(str(params.get("old_face_value", "0")))
            new_fv = Decimal(str(params.get("new_face_value", "0")))
            if old_fv <= 0 or new_fv <= 0:
                return None
            price_factor = new_fv / old_fv
            volume_factor = old_fv / new_fv
            return AdjustmentFactor(
                price_factor=price_factor,
                volume_factor=volume_factor,
                metadata=self._base_metadata(action),
            )

        if action_type in {CorporateActionType.RIGHTS, CorporateActionType.RIGHTS_RENOUNCE}:
            if action.ex_date is None:
                return None
            prior_day = action.ex_date - timedelta(days=1)
            prior = by_date.get(prior_day)
            if prior is None:
                return None
            p = Decimal(str(prior.close_price))
            n = Decimal(str(params.get("rights_ratio_denominator", "1")))
            r = Decimal(str(params.get("rights_ratio_numerator", "0")))
            fallback_used = False
            issue_price_obj = params.get("issue_price")
            if issue_price_obj in (None, ""):
                s = Decimal("0")
                fallback_used = True
            else:
                s = Decimal(str(issue_price_obj))
            if n + r == 0 or p <= 0:
                return None
            terp = ((n * p) + (r * s)) / (n + r)
            price_factor = terp / p
            metadata = self._base_metadata(action)
            metadata["subscription_price_fallback_zero"] = fallback_used
            return AdjustmentFactor(
                price_factor=price_factor,
                volume_factor=Decimal("1"),
                metadata=metadata,
            )

        if action_type == CorporateActionType.DEMERGER_PARENT:
            parent_pre = Decimal(str(params.get("parent_value_pre_demerger", "0")))
            actual_spinoff_value = params.get("actual_spinoff_listing_price")
            if actual_spinoff_value in (None, ""):
                spinoff_value = Decimal(str(params.get("spinoff_value", "0")))
                stage = "PRELIMINARY"
                value_source = "theoretical_spinoff_value"
            else:
                spinoff_value = Decimal(str(actual_spinoff_value))
                stage = "FINAL"
                value_source = "actual_listing_price"

            if parent_pre <= 0:
                return None
            price_factor = Decimal("1") - (spinoff_value / parent_pre)
            if price_factor <= 0:
                return None
            metadata = self._base_metadata(action)
            metadata["demerger_adjustment_stage"] = stage
            metadata["demerger_value_source"] = value_source
            return AdjustmentFactor(
                price_factor=price_factor,
                volume_factor=Decimal("1"),
                metadata=metadata,
            )

        return None

    @staticmethod
    def _base_metadata(action: ConfirmedCorporateAction) -> dict[str, str | bool]:
        return {
            "ca_confidence": action.confidence.value,
            "ca_source_preference": action.source_preference.value,
        }
