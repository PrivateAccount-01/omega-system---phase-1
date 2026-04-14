from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from omegadata.db.models import (
    ConfirmedCorporateAction,
    DiscontinuityEvent,
    ExclusionDate,
    InstrumentMaster,
    ManualReviewQueue,
    PriceRecord,
)
from omegadata.domain import DiscontinuityCategory, Exchange


@dataclass(frozen=True)
class DetectionOutcome:
    isin: str
    event_date: date
    category: DiscontinuityCategory
    idiosyncratic_return: Decimal
    is_new: bool


class DiscontinuityDetector:
    @staticmethod
    def _review_exists(
        session: Session,
        *,
        isin: str,
        event_date: date,
        reason: str,
    ) -> bool:
        return (
            session.scalar(
                select(ManualReviewQueue.id)
                .where(ManualReviewQueue.category == "DISCONTINUITY_REVIEW")
                .where(ManualReviewQueue.isin == isin)
                .where(ManualReviewQueue.event_date == event_date)
                .where(ManualReviewQueue.reason == reason)
                .limit(1)
            )
            is not None
        )

    def _estimate_beta(self, stock_returns: list[float], market_returns: list[float]) -> Decimal | None:
        obs = min(len(stock_returns), len(market_returns))
        if obs >= 60:
            x = np.array(market_returns[-252:])
            y = np.array(stock_returns[-252:])
            if np.var(x) > 0:
                beta = np.cov(y, x, ddof=1)[0, 1] / np.var(x, ddof=1)
                return Decimal(str(float(beta)))
        if obs >= 40:
            x = np.array(market_returns[-126:])
            y = np.array(stock_returns[-126:])
            if np.var(x) > 0:
                beta = np.cov(y, x, ddof=1)[0, 1] / np.var(x, ddof=1)
                return Decimal(str(float(beta)))
        return None

    def _compute_beta(
        self,
        stock_returns: list[float],
        market_returns: list[float],
        fallback_beta: Decimal,
    ) -> Decimal:
        estimated = self._estimate_beta(stock_returns, market_returns)
        if estimated is None:
            return fallback_beta
        return estimated

    @staticmethod
    def _median(values: list[Decimal]) -> Decimal | None:
        if not values:
            return None
        ordered = sorted(values)
        mid = len(ordered) // 2
        if len(ordered) % 2 == 1:
            return ordered[mid]
        return (ordered[mid - 1] + ordered[mid]) / Decimal("2")

    @staticmethod
    def _integrity_fail(row: PriceRecord) -> bool:
        open_p = Decimal(str(row.open_price))
        high_p = Decimal(str(row.high_price))
        low_p = Decimal(str(row.low_price))
        close_p = Decimal(str(row.close_price))
        return high_p < max(open_p, close_p) or low_p > min(open_p, close_p) or low_p > high_p

    def _build_fallback_betas(
        self,
        session: Session,
        market_map: dict[date, Decimal],
        market_isin: str,
        exchange: Exchange,
    ) -> tuple[dict[str, str], dict[str, Decimal], Decimal | None]:
        sector_rows = session.execute(
            select(InstrumentMaster.isin, InstrumentMaster.sector_name)
        ).all()
        sectors = {str(isin): str(sector or "") for isin, sector in sector_rows}

        sector_samples: dict[str, list[Decimal]] = {}
        all_estimates: list[Decimal] = []
        isins = [row[0] for row in session.execute(select(PriceRecord.isin).distinct()).all()]
        for isin in isins:
            if isin == market_isin:
                continue
            rows = session.scalars(
                select(PriceRecord)
                .where(PriceRecord.isin == isin)
                .where(PriceRecord.exchange == exchange)
                .order_by(PriceRecord.trade_date.asc())
            ).all()
            if len(rows) < 2:
                continue

            stock_history: list[float] = []
            market_history: list[float] = []
            for idx in range(1, len(rows)):
                prev = Decimal(str(rows[idx - 1].close_price))
                cur = Decimal(str(rows[idx].close_price))
                if prev == 0:
                    continue
                market_ret = market_map.get(rows[idx].trade_date)
                if market_ret is None:
                    continue
                stock_history.append(float((cur - prev) / prev))
                market_history.append(float(market_ret))

            estimated = self._estimate_beta(stock_history, market_history)
            if estimated is None:
                continue

            all_estimates.append(estimated)
            sector = sectors.get(str(isin), "")
            if sector:
                sector_samples.setdefault(sector, []).append(estimated)

        sector_medians = {
            sector: median
            for sector, values in sector_samples.items()
            if (median := self._median(values)) is not None
        }
        return sectors, sector_medians, self._median(all_estimates)

    def detect(
        self,
        session: Session,
        market_isin: str,
        exchange: Exchange = Exchange.NSE,
    ) -> list[DetectionOutcome]:
        outcomes: list[DetectionOutcome] = []

        market_rows = session.scalars(
            select(PriceRecord)
            .where(PriceRecord.isin == market_isin)
            .where(PriceRecord.exchange == exchange)
            .order_by(PriceRecord.trade_date.asc())
        ).all()
        market_map: dict[date, Decimal] = {}
        for idx in range(1, len(market_rows)):
            prev = Decimal(str(market_rows[idx - 1].close_price))
            cur = Decimal(str(market_rows[idx].close_price))
            if prev == 0:
                continue
            market_map[market_rows[idx].trade_date] = (cur - prev) / prev

        isins = [row[0] for row in session.execute(select(PriceRecord.isin).distinct()).all()]
        exclusion_dates = {
            r.event_date for r in session.scalars(select(ExclusionDate)).all()
        }
        sectors, sector_medians, overall_median = self._build_fallback_betas(
            session=session,
            market_map=market_map,
            market_isin=market_isin,
            exchange=exchange,
        )

        for isin in isins:
            if isin == market_isin:
                continue
            rows = session.scalars(
                select(PriceRecord)
                .where(PriceRecord.isin == isin)
                .where(PriceRecord.exchange == exchange)
                .order_by(PriceRecord.trade_date.asc())
            ).all()
            if len(rows) < 2:
                continue

            stock_history: list[float] = []
            market_history: list[float] = []

            for idx in range(1, len(rows)):
                prev = Decimal(str(rows[idx - 1].close_price))
                cur = Decimal(str(rows[idx].close_price))
                if prev == 0:
                    continue

                event_date = rows[idx].trade_date
                overnight = (cur - prev) / prev
                market_ret = market_map.get(event_date)
                if market_ret is None:
                    continue

                if self._integrity_fail(rows[idx]):
                    outcomes.append(
                        self._persist_event(
                            session,
                            isin=isin,
                            event_date=event_date,
                            overnight=overnight,
                            market_ret=market_ret,
                            beta=Decimal("0"),
                            idio=Decimal("0"),
                            category=DiscontinuityCategory.C,
                            review=True,
                            auto_adjust=False,
                        )
                    )
                    continue

                stock_history.append(float(overnight))
                market_history.append(float(market_ret))
                sector = sectors.get(str(isin), "")
                fallback_beta = sector_medians.get(sector)
                if fallback_beta is None:
                    fallback_beta = overall_median or Decimal("1")
                beta = self._compute_beta(stock_history, market_history, fallback_beta=fallback_beta)
                idio = overnight - (beta * market_ret)

                bonus_threshold = Decimal("-0.35")
                rights_threshold = Decimal("-0.10")
                positive_threshold = Decimal("0.25")
                if event_date in exclusion_dates:
                    bonus_threshold = Decimal("-0.50")
                    rights_threshold = Decimal("-0.15")
                    positive_threshold = Decimal("0.35")

                if idio < bonus_threshold:
                    has_action = session.scalar(
                        select(ConfirmedCorporateAction)
                        .where(ConfirmedCorporateAction.isin == isin)
                        .where(ConfirmedCorporateAction.ex_date == event_date)
                        .where(ConfirmedCorporateAction.superseded.is_(False))
                    )
                    outcomes.append(
                        self._persist_event(
                            session,
                            isin=isin,
                            event_date=event_date,
                            overnight=overnight,
                            market_ret=market_ret,
                            beta=beta,
                            idio=idio,
                            category=DiscontinuityCategory.A,
                            review=has_action is None,
                            auto_adjust=has_action is not None,
                        )
                    )
                    continue

                if idio < rights_threshold or idio > positive_threshold:
                    outcomes.append(
                        self._persist_event(
                            session,
                            isin=isin,
                            event_date=event_date,
                            overnight=overnight,
                            market_ret=market_ret,
                            beta=beta,
                            idio=idio,
                            category=DiscontinuityCategory.B,
                            review=True,
                            auto_adjust=False,
                        )
                    )

        return outcomes

    def _persist_event(
        self,
        session: Session,
        isin: str,
        event_date: date,
        overnight: Decimal,
        market_ret: Decimal,
        beta: Decimal,
        idio: Decimal,
        category: DiscontinuityCategory,
        review: bool,
        auto_adjust: bool,
    ) -> DetectionOutcome:
        existing = session.scalar(
            select(DiscontinuityEvent)
            .where(DiscontinuityEvent.isin == isin)
            .where(DiscontinuityEvent.event_date == event_date)
            .where(DiscontinuityEvent.category == category)
            .limit(1)
        )
        is_new = existing is None
        if existing is None:
            event = DiscontinuityEvent(
                isin=isin,
                event_date=event_date,
                overnight_return=overnight,
                market_return=market_ret,
                beta_used=beta,
                idiosyncratic_return=idio,
                category=category,
                review_required=review,
                auto_adjust_queued=auto_adjust,
            )
            session.add(event)
        else:
            existing.overnight_return = overnight
            existing.market_return = market_ret
            existing.beta_used = beta
            existing.idiosyncratic_return = idio
            existing.review_required = review
            existing.auto_adjust_queued = auto_adjust

        if review:
            reason = f"Discontinuity category {category.value}"
            if not self._review_exists(session, isin=isin, event_date=event_date, reason=reason):
                session.add(
                    ManualReviewQueue(
                        category="DISCONTINUITY_REVIEW",
                        isin=isin,
                        event_date=event_date,
                        reason=reason,
                        payload={
                            "idiosyncratic_return": str(idio),
                            "overnight_return": str(overnight),
                        },
                    )
                )
        return DetectionOutcome(
            isin=isin,
            event_date=event_date,
            category=category,
            idiosyncratic_return=idio,
            is_new=is_new,
        )
