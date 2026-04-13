from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from omegadata.db.models import (
    CorporateActionStaging,
    PriceRecord,
    ValidationAuditLog,
)
from omegadata.domain import Exchange, ValidationResult
from omegadata.track_b.corporate_action_matching import CorporateActionMatcher
from omegadata.track_b.manual_review import ManualReviewService


@dataclass(frozen=True)
class ValidationOutcome:
    data_date: date
    result: ValidationResult
    field: str
    difference_pct: Decimal


class CrossSourceValidator:
    def __init__(self) -> None:
        self.matcher = CorporateActionMatcher()
        self.review_service = ManualReviewService()

    @staticmethod
    def _audit_exists(
        session: Session,
        source_1: str,
        source_2: str,
        isin: str,
        data_date: date,
        field: str,
        left: str,
        right: str,
        result: ValidationResult,
    ) -> bool:
        row = session.scalar(
            select(ValidationAuditLog.id)
            .where(ValidationAuditLog.source_1 == source_1)
            .where(ValidationAuditLog.source_2 == source_2)
            .where(ValidationAuditLog.isin == isin)
            .where(ValidationAuditLog.data_date == data_date)
            .where(ValidationAuditLog.field_compared == field)
            .where(ValidationAuditLog.source_1_value == left)
            .where(ValidationAuditLog.source_2_value == right)
            .where(ValidationAuditLog.result == result)
        )
        return row is not None

    def validate_nse_bse_prices(self, session: Session, isin: str) -> list[ValidationOutcome]:
        nse_rows = session.scalars(
            select(PriceRecord)
            .where(PriceRecord.isin == isin)
            .where(PriceRecord.exchange == Exchange.NSE)
            .order_by(PriceRecord.trade_date.asc())
        ).all()
        bse_rows = session.scalars(
            select(PriceRecord)
            .where(PriceRecord.isin == isin)
            .where(PriceRecord.exchange == Exchange.BSE)
            .order_by(PriceRecord.trade_date.asc())
        ).all()
        bse_by_date = {r.trade_date: r for r in bse_rows}

        outcomes: list[ValidationOutcome] = []
        signed_diffs: list[tuple[date, Decimal]] = []
        for nse in nse_rows:
            bse = bse_by_date.get(nse.trade_date)
            if bse is None:
                continue
            synthetic_bse = str(bse.raw_source).lower().startswith("bse_stockreach_graph")
            fields = ("close_price",) if synthetic_bse else ("open_price", "high_price", "low_price", "close_price")
            for field in fields:
                outcome = self._compare_numeric(
                    session=session,
                    source_1="NSE",
                    source_2="BSE",
                    isin=isin,
                    data_date=nse.trade_date,
                    field=field,
                    left=Decimal(str(getattr(nse, field))),
                    right=Decimal(str(getattr(bse, field))),
                    tolerance=self._price_tolerance(nse=nse, bse=bse, field=field),
                )
                outcomes.append(outcome)
            signed_diffs.append((nse.trade_date, Decimal(str(nse.close_price)) - Decimal(str(bse.close_price))))

        self._detect_systematic_disagreement(session, isin, signed_diffs)
        return outcomes

    @staticmethod
    def _price_tolerance(*, nse: PriceRecord, bse: PriceRecord, field: str) -> Decimal:
        tolerance = Decimal("0.0010")
        synthetic_bse = str(bse.raw_source).lower().startswith("bse_stockreach_graph")
        if synthetic_bse:
            tolerance = Decimal("0.0040")

        max_close = max(Decimal(str(nse.close_price)), Decimal(str(bse.close_price)))
        max_volume = max(Decimal(str(nse.volume)), Decimal(str(bse.volume)))
        traded_notional = max_close * max_volume
        if traded_notional < Decimal("250000"):
            tolerance = max(tolerance, Decimal("0.0050"))
        elif traded_notional < Decimal("1000000"):
            tolerance = max(tolerance, Decimal("0.0025"))

        if field != "close_price":
            tolerance = max(tolerance, tolerance + Decimal("0.0005"))
        if nse.is_imputed or bse.is_imputed:
            tolerance = max(tolerance, Decimal("0.0030"))
        return tolerance

    def validate_monthly_flow_consistency(
        self,
        session: Session,
        *,
        data_date: date,
        nse_net_flow: Decimal,
        rbi_net_flow: Decimal,
        field: str = "monthly_net_flow",
    ) -> ValidationOutcome:
        return self._compare_numeric(
            session=session,
            source_1="NSE_FII_DII",
            source_2="RBI_DBIE",
            isin="MONTHLY_AGGREGATE",
            data_date=data_date,
            field=field,
            left=nse_net_flow,
            right=rbi_net_flow,
            tolerance=Decimal("0.05"),
        )

    def validate_implied_volatility_spot_check(
        self,
        session: Session,
        *,
        isin: str,
        data_date: date,
        omega_iv: Decimal,
        reference_iv: Decimal,
        reference_source: str = "OPSTRA",
    ) -> ValidationOutcome:
        return self._compare_numeric(
            session=session,
            source_1="OMEGADATA_IV",
            source_2=reference_source,
            isin=isin,
            data_date=data_date,
            field="implied_volatility",
            left=omega_iv,
            right=reference_iv,
            tolerance=Decimal("0.05"),
        )

    def validate_secondary_adjusted_price(
        self,
        session: Session,
        *,
        isin: str,
        data_date: date,
        omegadata_adjusted_price: Decimal,
        secondary_adjusted_price: Decimal,
        secondary_source: str = "YFINANCE",
    ) -> ValidationOutcome:
        return self._compare_numeric(
            session=session,
            source_1="OMEGADATA_ADJUSTED",
            source_2=secondary_source,
            isin=isin,
            data_date=data_date,
            field="adjusted_close_price",
            left=omegadata_adjusted_price,
            right=secondary_adjusted_price,
            tolerance=Decimal("0.05"),
        )

    def validate_corporate_actions(self, session: Session, isin: str) -> list[ValidationOutcome]:
        outcomes: list[ValidationOutcome] = []

        nse_rows = session.scalars(
            select(CorporateActionStaging)
            .where(CorporateActionStaging.isin == isin)
            .where(CorporateActionStaging.source == Exchange.NSE)
            .order_by(CorporateActionStaging.ex_date.asc())
        ).all()
        bse_rows = session.scalars(
            select(CorporateActionStaging)
            .where(CorporateActionStaging.isin == isin)
            .where(CorporateActionStaging.source.in_([Exchange.BSE, Exchange.BSE_ONLY]))
            .order_by(CorporateActionStaging.ex_date.asc())
        ).all()

        if not nse_rows:
            return outcomes

        pairs, unmatched_nse, _unmatched_bse = self.matcher.match_pairs(list(nse_rows), list(bse_rows))

        for staged_row in unmatched_nse:
            nse_date = self._event_date(staged_row)
            if nse_date is None:
                continue
            anchor_date = nse_date
            scored_candidates = [
                (candidate, self.matcher.relatedness_score(staged_row, candidate))
                for candidate in bse_rows
                if self._event_date(candidate) is not None
                and self._date_gap_days(anchor_date, self._event_date(candidate)) <= 10
            ]
            best_candidate: CorporateActionStaging | None = None
            best_score = -10_000
            if scored_candidates:
                best_candidate, best_score = max(scored_candidates, key=lambda item: item[1])
            if (
                best_candidate is not None
                and best_score >= 60
                and self.matcher.economic_overlap_count(staged_row, best_candidate) > 0
                and best_candidate.action_type != staged_row.action_type
            ):
                    outcomes.append(
                        self._persist_categorical_result(
                            session=session,
                            source_1="NSE",
                            source_2="BSE",
                            isin=isin,
                            data_date=anchor_date,
                            field="action_type",
                            left=staged_row.action_type.value,
                            right=best_candidate.action_type.value,
                            result=ValidationResult.FAIL,
                            diff_pct=Decimal("1"),
                            tolerance=Decimal("0"),
                            notes=(
                                "Corporate action type mismatch across high-similarity "
                                f"source candidates (score={best_score})"
                            ),
                        )
                    )
                    continue
            outcomes.append(
                self._persist_categorical_result(
                    session=session,
                    source_1="NSE",
                    source_2="BSE",
                    isin=isin,
                    data_date=anchor_date,
                    field="corporate_action_coverage",
                    left="present",
                    right="missing",
                    result=ValidationResult.WARN,
                    diff_pct=Decimal("1"),
                    tolerance=Decimal("0"),
                    notes=(
                        "No high-confidence BSE corporate action candidate for NSE action"
                        if best_candidate is not None
                        else "No BSE corporate action candidate for NSE action"
                    ),
                )
            )

        for pair in pairs:
            staged_row = pair.nse
            staging_pair = pair.bse
            nse_date = self._event_date(staged_row)
            if nse_date is None:
                continue
            pair_date = self._event_date(staging_pair)
            assert pair_date is not None

            if staged_row.action_type != staging_pair.action_type:
                outcomes.append(
                    self._persist_categorical_result(
                        session=session,
                        source_1="NSE",
                        source_2="BSE",
                        isin=staged_row.isin,
                        data_date=nse_date,
                        field="action_type",
                        left=staged_row.action_type.value,
                        right=staging_pair.action_type.value,
                        result=ValidationResult.FAIL,
                        diff_pct=Decimal("1"),
                        tolerance=Decimal("0"),
                        notes="Corporate action type mismatch across sources",
                    )
                )
                continue

            gap_days = self._date_gap_days(nse_date, pair_date)
            if gap_days <= 1:
                result = ValidationResult.PASS
            elif gap_days <= 5:
                result = ValidationResult.WARN
            else:
                result = ValidationResult.FAIL

            outcomes.append(
                    self._persist_categorical_result(
                        session=session,
                        source_1="NSE",
                        source_2="BSE",
                        isin=staged_row.isin,
                        data_date=nse_date,
                        field="action_date_alignment_days",
                        left=nse_date.isoformat(),
                    right=pair_date.isoformat(),
                    result=result,
                    diff_pct=Decimal(str(gap_days)),
                    tolerance=Decimal("1"),
                    notes=f"Nearest-date corporate action match gap={gap_days} days",
                )
            )

            for key, left_val in staged_row.payload.items():
                right_val = staging_pair.payload.get(key)
                if right_val in (None, "") or left_val in (None, ""):
                    continue
                try:
                    left = Decimal(str(left_val))
                    right = Decimal(str(right_val))
                except Exception:
                    continue
                data_date = staged_row.ex_date or nse_date
                outcomes.append(
                    self._compare_numeric(
                        session=session,
                        source_1="NSE",
                        source_2="BSE",
                        isin=staged_row.isin,
                        data_date=data_date,
                        field=key,
                        left=left,
                        right=right,
                        tolerance=Decimal("0.01"),
                    )
                )
        return outcomes

    @staticmethod
    def _event_date(row: CorporateActionStaging) -> date | None:
        return row.ex_date or row.announcement_date or row.record_date

    @staticmethod
    def _date_gap_days(left: date, right: date | None) -> int:
        if right is None:
            return 9999
        return abs((left - right).days)

    def _compare_numeric(
        self,
        session: Session,
        source_1: str,
        source_2: str,
        isin: str,
        data_date: date,
        field: str,
        left: Decimal,
        right: Decimal,
        tolerance: Decimal,
    ) -> ValidationOutcome:
        if right == 0:
            diff_pct = Decimal("0") if left == 0 else Decimal("1")
        else:
            diff_pct = abs((left - right) / right)

        if diff_pct <= tolerance:
            result = ValidationResult.PASS
        elif diff_pct <= tolerance * 2:
            result = ValidationResult.WARN
        else:
            result = ValidationResult.FAIL

        audit = ValidationAuditLog(
            source_1=source_1,
            source_2=source_2,
            isin=isin,
            data_date=data_date,
            field_compared=field,
            source_1_value=str(left),
            source_2_value=str(right),
            difference_absolute=abs(left - right),
            difference_pct=diff_pct,
            tolerance_applied=tolerance,
            result=result,
            resolution_status="OPEN" if result != ValidationResult.PASS else "CLOSED",
            resolution_notes=None,
        )
        if self._audit_exists(
            session=session,
            source_1=source_1,
            source_2=source_2,
            isin=isin,
            data_date=data_date,
            field=field,
            left=str(left),
            right=str(right),
            result=result,
        ):
            return ValidationOutcome(data_date=data_date, result=result, field=field, difference_pct=diff_pct)

        session.add(audit)

        if result == ValidationResult.FAIL:
            self.review_service.queue_review(
                session,
                category="CROSS_SOURCE_VALIDATION_FAIL",
                isin=isin,
                event_date=data_date,
                reason=f"{field} exceeds 2x tolerance",
                payload={"left": str(left), "right": str(right), "diff_pct": str(diff_pct), "field": field},
            )
        return ValidationOutcome(data_date=data_date, result=result, field=field, difference_pct=diff_pct)

    def _persist_categorical_result(
        self,
        session: Session,
        source_1: str,
        source_2: str,
        isin: str,
        data_date: date,
        field: str,
        left: str,
        right: str,
        result: ValidationResult,
        diff_pct: Decimal,
        tolerance: Decimal,
        notes: str,
    ) -> ValidationOutcome:
        audit = ValidationAuditLog(
            source_1=source_1,
            source_2=source_2,
            isin=isin,
            data_date=data_date,
            field_compared=field,
            source_1_value=left,
            source_2_value=right,
            difference_absolute=abs(diff_pct),
            difference_pct=diff_pct,
            tolerance_applied=tolerance,
            result=result,
            resolution_status="CLOSED" if result == ValidationResult.PASS else "OPEN",
            resolution_notes=notes,
        )
        if self._audit_exists(
            session=session,
            source_1=source_1,
            source_2=source_2,
            isin=isin,
            data_date=data_date,
            field=field,
            left=left,
            right=right,
            result=result,
        ):
            return ValidationOutcome(data_date=data_date, result=result, field=field, difference_pct=diff_pct)

        session.add(audit)

        if result == ValidationResult.FAIL:
            self.review_service.queue_review(
                session,
                category="CORPORATE_ACTION_TYPE_FAIL",
                isin=isin,
                event_date=data_date,
                reason=notes,
                payload={"left": left, "right": right, "field": field},
            )

        return ValidationOutcome(data_date=data_date, result=result, field=field, difference_pct=diff_pct)

    def _detect_systematic_disagreement(
        self,
        session: Session,
        isin: str,
        signed_diffs: list[tuple[date, Decimal]],
    ) -> None:
        if len(signed_diffs) < 5:
            return
        ordered = sorted(signed_diffs, key=lambda item: item[0])
        last_five = ordered[-5:]
        values = [diff for _trade_date, diff in last_five]
        same_sign = all(x > 0 for x in values) or all(x < 0 for x in values)
        if same_sign:
            self.review_service.queue_review(
                session,
                category="SYSTEMATIC_DISAGREEMENT",
                isin=isin,
                event_date=None,
                reason="Consecutive directional disagreement across five observations",
                payload={
                    "last_five": [
                        {"trade_date": trade_date.isoformat(), "signed_diff": str(diff)}
                        for trade_date, diff in last_five
                    ]
                },
            )
