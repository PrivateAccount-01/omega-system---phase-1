from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from omegadata.db.models import (
    CorporateActionStaging,
    ConfirmedCorporateAction,
    ManualReviewQueue,
    PriceRecord,
    ValidationAuditLog,
)
from omegadata.domain import Exchange, ValidationResult


@dataclass(frozen=True)
class ValidationOutcome:
    result: ValidationResult
    field: str
    difference_pct: Decimal


class CrossSourceValidator:
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
        ).all()
        bse_rows = session.scalars(
            select(PriceRecord)
            .where(PriceRecord.isin == isin)
            .where(PriceRecord.exchange == Exchange.BSE)
        ).all()
        bse_by_date = {r.trade_date: r for r in bse_rows}

        outcomes: list[ValidationOutcome] = []
        signed_diffs: list[Decimal] = []
        for nse in nse_rows:
            bse = bse_by_date.get(nse.trade_date)
            if bse is None:
                continue
            outcome = self._compare_numeric(
                session=session,
                source_1="NSE",
                source_2="BSE",
                isin=isin,
                data_date=nse.trade_date,
                field="close_price",
                left=Decimal(str(nse.close_price)),
                right=Decimal(str(bse.close_price)),
                tolerance=Decimal("0.0010"),
            )
            outcomes.append(outcome)
            signed_diffs.append(Decimal(str(nse.close_price)) - Decimal(str(bse.close_price)))

            if outcome.result == ValidationResult.FAIL:
                nse.confidence_score = Decimal("0.50")

        self._detect_systematic_disagreement(session, isin, signed_diffs)
        return outcomes

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

        # Keep strict confirmed-pair validation for cases where both sources are confirmed.
        confirmed_rows = session.scalars(
            select(ConfirmedCorporateAction)
            .where(ConfirmedCorporateAction.isin == isin)
            .where(ConfirmedCorporateAction.superseded.is_(False))
            .order_by(ConfirmedCorporateAction.ex_date.asc())
        ).all()
        nse_confirmed = [r for r in confirmed_rows if r.source_preference == Exchange.NSE]
        for row in nse_confirmed:
            pair = session.scalar(
                select(ConfirmedCorporateAction).where(
                    and_(
                        ConfirmedCorporateAction.isin == row.isin,
                        ConfirmedCorporateAction.ex_date == row.ex_date,
                        ConfirmedCorporateAction.source_preference == Exchange.BSE,
                        ConfirmedCorporateAction.superseded.is_(False),
                    )
                )
            )
            if pair is None:
                continue

            if row.action_type != pair.action_type:
                outcomes.append(
                    self._persist_categorical_result(
                        session=session,
                        source_1="NSE",
                        source_2="BSE",
                        isin=row.isin,
                        data_date=row.ex_date or row.announcement_date or row.record_date,
                        field="action_type",
                        left=row.action_type.value,
                        right=pair.action_type.value,
                        result=ValidationResult.FAIL,
                        diff_pct=Decimal("1"),
                        tolerance=Decimal("0"),
                        notes="Corporate action type mismatch across confirmed sources",
                    )
                )
                continue

            for key, left_val in row.parameters.items():
                right_val = pair.parameters.get(key)
                if right_val in (None, "") or left_val in (None, ""):
                    continue
                try:
                    left = Decimal(str(left_val))
                    right = Decimal(str(right_val))
                except Exception:
                    continue
                data_date = row.ex_date or row.announcement_date or row.record_date
                outcomes.append(
                    self._compare_numeric(
                        session=session,
                        source_1="NSE",
                        source_2="BSE",
                        isin=row.isin,
                        data_date=data_date,
                        field=key,
                        left=left,
                        right=right,
                        tolerance=Decimal("0.01"),
                    )
                )

        nse_rows = session.scalars(
            select(CorporateActionStaging)
            .where(CorporateActionStaging.isin == isin)
            .where(CorporateActionStaging.source == Exchange.NSE)
            .order_by(CorporateActionStaging.ex_date.asc())
        ).all()
        bse_rows = session.scalars(
            select(CorporateActionStaging)
            .where(CorporateActionStaging.isin == isin)
            .where(CorporateActionStaging.source == Exchange.BSE)
            .order_by(CorporateActionStaging.ex_date.asc())
        ).all()

        if not nse_rows:
            return outcomes

        for row in nse_rows:
            nse_date = self._event_date(row)
            if nse_date is None:
                continue
            candidates = [
                bse for bse in bse_rows if self._event_date(bse) is not None
            ]
            if not candidates:
                outcomes.append(
                    self._persist_categorical_result(
                        session=session,
                        source_1="NSE",
                        source_2="BSE",
                        isin=isin,
                        data_date=nse_date,
                        field="corporate_action_coverage",
                        left="present",
                        right="missing",
                        result=ValidationResult.WARN,
                        diff_pct=Decimal("1"),
                        tolerance=Decimal("0"),
                        notes="No BSE corporate action candidate for NSE action",
                    )
                )
                continue

            pair = min(
                candidates,
                key=lambda b: self._date_gap_days(nse_date, self._event_date(b)),
            )
            pair_date = self._event_date(pair)
            assert pair_date is not None

            if row.action_type != pair.action_type:
                outcomes.append(
                    self._persist_categorical_result(
                        session=session,
                        source_1="NSE",
                        source_2="BSE",
                        isin=row.isin,
                        data_date=nse_date,
                        field="action_type",
                        left=row.action_type.value,
                        right=pair.action_type.value,
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
                    isin=row.isin,
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

            for key, left_val in row.payload.items():
                right_val = pair.payload.get(key)
                if right_val in (None, "") or left_val in (None, ""):
                    continue
                try:
                    left = Decimal(str(left_val))
                    right = Decimal(str(right_val))
                except Exception:
                    continue
                data_date = row.ex_date or nse_date
                outcomes.append(
                    self._compare_numeric(
                        session=session,
                        source_1="NSE",
                        source_2="BSE",
                        isin=row.isin,
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
            return ValidationOutcome(result=result, field=field, difference_pct=diff_pct)

        session.add(audit)

        if result == ValidationResult.FAIL:
            session.add(
                ManualReviewQueue(
                    category="CROSS_SOURCE_VALIDATION_FAIL",
                    isin=isin,
                    event_date=data_date,
                    reason=f"{field} exceeds 2x tolerance",
                    payload={"left": str(left), "right": str(right), "diff_pct": str(diff_pct)},
                )
            )
        return ValidationOutcome(result=result, field=field, difference_pct=diff_pct)

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
            return ValidationOutcome(result=result, field=field, difference_pct=diff_pct)

        session.add(audit)

        if result == ValidationResult.FAIL:
            session.add(
                ManualReviewQueue(
                    category="CORPORATE_ACTION_TYPE_FAIL",
                    isin=isin,
                    event_date=data_date,
                    reason=notes,
                    payload={"left": left, "right": right, "field": field},
                )
            )

        return ValidationOutcome(result=result, field=field, difference_pct=diff_pct)

    def _detect_systematic_disagreement(
        self,
        session: Session,
        isin: str,
        signed_diffs: list[Decimal],
    ) -> None:
        if len(signed_diffs) < 5:
            return
        last_five = signed_diffs[-5:]
        same_sign = all(x > 0 for x in last_five) or all(x < 0 for x in last_five)
        if same_sign:
            session.add(
                ManualReviewQueue(
                    category="SYSTEMATIC_DISAGREEMENT",
                    isin=isin,
                    event_date=None,
                    reason="Consecutive directional disagreement across five observations",
                    payload={"last_five": [str(x) for x in last_five]},
                )
            )
