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
from omegadata.track_a.monitoring import CORPORATE_ACTION_UNMATCHED_COUNTER
from omegadata.track_b.corporate_action_matching import CorporateActionMatcher
from omegadata.track_b.corporate_actions import CorporateActionService
from omegadata.track_b.manual_review import ManualReviewService
from omegadata.track_b.tolerance_policy import load_tolerance_policy


@dataclass(frozen=True)
class ValidationOutcome:
    data_date: date
    result: ValidationResult
    field: str
    difference_pct: Decimal


@dataclass(frozen=True)
class PriceToleranceContext:
    tolerance: Decimal
    effective_notional: Decimal
    liquidity_bucket: str
    synthetic_bse: bool
    field: str
    source_quality: str
    imputed: bool


class CrossSourceValidator:
    def __init__(self) -> None:
        self.matcher = CorporateActionMatcher()
        self.review_service = ManualReviewService()
        self._audit_key_cache: set[tuple[str, str, str, date, str, str, str, ValidationResult]] = set()
        self._audit_db_checked = False
        self._audit_db_has_rows = False

    @staticmethod
    def _audit_key(
        *,
        source_1: str,
        source_2: str,
        isin: str,
        data_date: date,
        field: str,
        left: str,
        right: str,
        result: ValidationResult,
    ) -> tuple[str, str, str, date, str, str, str, ValidationResult]:
        return (source_1, source_2, isin, data_date, field, left, right, result)

    @staticmethod
    def _audit_exists(
        session: Session,
        audit_key_cache: set[tuple[str, str, str, date, str, str, str, ValidationResult]],
        audit_db_checked: bool,
        audit_db_has_rows: bool,
        source_1: str,
        source_2: str,
        isin: str,
        data_date: date,
        field: str,
        left: str,
        right: str,
        result: ValidationResult,
    ) -> tuple[bool, bool, bool]:
        key = CrossSourceValidator._audit_key(
            source_1=source_1,
            source_2=source_2,
            isin=isin,
            data_date=data_date,
            field=field,
            left=left,
            right=right,
            result=result,
        )
        if key in audit_key_cache:
            return True, audit_db_checked, audit_db_has_rows
        if not audit_db_checked:
            audit_db_has_rows = (
                session.scalar(select(ValidationAuditLog.id).limit(1)) is not None
            )
            audit_db_checked = True
        if not audit_db_has_rows:
            audit_key_cache.add(key)
            return False, audit_db_checked, audit_db_has_rows
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
        if row is not None:
            audit_key_cache.add(key)
            return True, audit_db_checked, audit_db_has_rows
        audit_key_cache.add(key)
        return False, audit_db_checked, audit_db_has_rows

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
        failed_by_date: dict[date, list[tuple[str, Decimal, Decimal, Decimal]]] = {}
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
                if outcome.result == ValidationResult.FAIL:
                    failed_by_date.setdefault(nse.trade_date, []).append(
                        (
                            field,
                            Decimal(str(getattr(nse, field))),
                            Decimal(str(getattr(bse, field))),
                            outcome.difference_pct,
                        )
                    )
            bse_close = Decimal(str(bse.close_price))
            nse_close = Decimal(str(nse.close_price))
            signed_diff_pct = (
                Decimal("0")
                if bse_close == 0
                else (nse_close - bse_close) / bse_close
            )
            signed_diffs.append((nse.trade_date, signed_diff_pct))

        for data_date, failures in failed_by_date.items():
            max_diff = max(item[3] for item in failures)
            self.review_service.queue_review(
                session,
                category="CROSS_SOURCE_VALIDATION_FAIL",
                isin=isin,
                event_date=data_date,
                reason="cross-source price validation exceeded 2x tolerance",
                payload={
                    "failed_fields": [item[0] for item in failures],
                    "max_diff_pct": str(max_diff),
                    "field_differences": [
                        {
                            "field": field,
                            "left": str(left),
                            "right": str(right),
                            "diff_pct": str(diff_pct),
                        }
                        for field, left, right, diff_pct in failures
                    ],
                },
            )

        self._detect_systematic_disagreement(session, isin, signed_diffs)
        return outcomes

    @staticmethod
    def _price_tolerance_context(*, nse: PriceRecord, bse: PriceRecord, field: str) -> PriceToleranceContext:
        tolerance = Decimal("0.0010")
        synthetic_bse = str(bse.raw_source).lower().startswith("bse_stockreach_graph")
        nse_notional = Decimal(str(nse.close_price)) * Decimal(str(nse.volume))
        bse_notional = Decimal(str(bse.close_price)) * Decimal(str(bse.volume))
        if nse_notional > 0 and bse_notional > 0:
            effective_notional = (Decimal("2") * nse_notional * bse_notional) / (nse_notional + bse_notional)
        else:
            effective_notional = min(nse_notional, bse_notional)

        if effective_notional < Decimal("250000"):
            tolerance = Decimal("0.0045")
            liquidity_bucket = "micro"
        elif effective_notional < Decimal("1000000"):
            tolerance = Decimal("0.0030")
            liquidity_bucket = "small"
        elif effective_notional < Decimal("5000000"):
            tolerance = Decimal("0.0020")
            liquidity_bucket = "mid"
        elif effective_notional < Decimal("20000000"):
            tolerance = Decimal("0.0015")
            liquidity_bucket = "large"
        else:
            liquidity_bucket = "mega"

        if synthetic_bse:
            tolerance = max(tolerance, Decimal("0.0040"))
        if field != "close_price":
            tolerance += Decimal("0.0005")
        imputed = nse.is_imputed or bse.is_imputed
        if imputed:
            tolerance = max(tolerance, Decimal("0.0035"))
        source_quality = "synthetic" if synthetic_bse else "official"
        policy = load_tolerance_policy()
        if policy is not None:
            matched = policy.match(
                liquidity_bucket=liquidity_bucket,
                source_quality=source_quality,
                field=field,
                imputed=imputed,
            )
            if matched is not None:
                tolerance = Decimal(matched.tolerance_pct)
        return PriceToleranceContext(
            tolerance=tolerance,
            effective_notional=effective_notional,
            liquidity_bucket=liquidity_bucket,
            synthetic_bse=synthetic_bse,
            field=field,
            source_quality=source_quality,
            imputed=imputed,
        )

    @staticmethod
    def _price_tolerance(*, nse: PriceRecord, bse: PriceRecord, field: str) -> Decimal:
        return CrossSourceValidator._price_tolerance_context(nse=nse, bse=bse, field=field).tolerance

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
                and self._date_gap_days(anchor_date, self._event_date(candidate))
                <= self.matcher.policy.related_candidate_gap_days
            ]
            best_candidate: CorporateActionStaging | None = None
            best_score = -10_000
            if scored_candidates:
                best_candidate, best_score = max(scored_candidates, key=lambda item: item[1])
            if (
                best_candidate is not None
                and best_score >= self.matcher.policy.high_similarity_threshold
                and self.matcher.has_economic_signal(staged_row, best_candidate)
                and best_candidate.action_type != staged_row.action_type
            ):
                    CORPORATE_ACTION_UNMATCHED_COUNTER.labels(classification="type_mismatch_fail").inc()
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
            if (
                best_candidate is not None
                and best_score >= self.matcher.policy.ambiguous_similarity_threshold
                and self.matcher.has_economic_signal(staged_row, best_candidate)
            ):
                CORPORATE_ACTION_UNMATCHED_COUNTER.labels(classification="ambiguous_near_candidate").inc()
                self.review_service.queue_review(
                    session,
                    category="CORPORATE_ACTION_FALSE_NEGATIVE_RISK",
                    isin=isin,
                    event_date=anchor_date,
                    reason="Potential corporate-action false negative risk from nearby economically related candidate",
                    payload={
                        "nse_action_type": staged_row.action_type.value,
                        "candidate_action_type": best_candidate.action_type.value,
                        "score": str(best_score),
                    },
                )
                outcomes.append(
                    self._persist_categorical_result(
                        session=session,
                        source_1="NSE",
                        source_2="BSE",
                        isin=isin,
                        data_date=anchor_date,
                        field="corporate_action_false_negative_risk",
                        left=staged_row.action_type.value,
                        right=best_candidate.action_type.value,
                        result=ValidationResult.WARN,
                        diff_pct=Decimal("1"),
                        tolerance=Decimal("0"),
                        notes=(
                            "Unmatched NSE action has an economically related BSE candidate below "
                            f"mismatch threshold (score={best_score})"
                        ),
                    )
                )
            else:
                CORPORATE_ACTION_UNMATCHED_COUNTER.labels(classification="no_candidate").inc()
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

            compared_keys = set(staged_row.payload) | set(staging_pair.payload)
            required_keys = set(CorporateActionService._validate_required_fields(staged_row.action_type, staged_row.payload))
            required_keys |= set(CorporateActionService._validate_required_fields(staging_pair.action_type, staging_pair.payload))
            for key in sorted(compared_keys | required_keys):
                right_val = staging_pair.payload.get(key)
                left_val = staged_row.payload.get(key)
                if left_val in (None, "") and right_val in (None, ""):
                    continue
                if left_val in (None, "") or right_val in (None, ""):
                    outcomes.append(
                        self._persist_categorical_result(
                            session=session,
                            source_1="NSE",
                            source_2="BSE",
                            isin=staged_row.isin,
                            data_date=staged_row.ex_date or nse_date,
                            field=key,
                            left="missing" if left_val in (None, "") else str(left_val),
                            right="missing" if right_val in (None, "") else str(right_val),
                            result=ValidationResult.FAIL,
                            diff_pct=Decimal("1"),
                            tolerance=Decimal("0"),
                            notes="Corporate action parameter missing on one side of a matched pair",
                        )
                    )
                    continue
                if right_val in (None, "") or left_val in (None, ""):
                    continue
                try:
                    left = Decimal(str(left_val))
                    right = Decimal(str(right_val))
                except Exception:
                    if str(left_val) != str(right_val):
                        outcomes.append(
                            self._persist_categorical_result(
                                session=session,
                                source_1="NSE",
                                source_2="BSE",
                                isin=staged_row.isin,
                                data_date=staged_row.ex_date or nse_date,
                                field=key,
                                left=str(left_val),
                                right=str(right_val),
                                result=ValidationResult.FAIL,
                                diff_pct=Decimal("1"),
                                tolerance=Decimal("0"),
                                notes="Corporate action categorical parameter mismatch across matched pair",
                            )
                        )
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
        elif diff_pct < tolerance * 2:
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
        exists, self._audit_db_checked, self._audit_db_has_rows = self._audit_exists(
            session=session,
            audit_key_cache=self._audit_key_cache,
            audit_db_checked=self._audit_db_checked,
            audit_db_has_rows=self._audit_db_has_rows,
            source_1=source_1,
            source_2=source_2,
            isin=isin,
            data_date=data_date,
            field=field,
            left=str(left),
            right=str(right),
            result=result,
        )
        if exists:
            return ValidationOutcome(data_date=data_date, result=result, field=field, difference_pct=diff_pct)

        session.add(audit)

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
        exists, self._audit_db_checked, self._audit_db_has_rows = self._audit_exists(
            session=session,
            audit_key_cache=self._audit_key_cache,
            audit_db_checked=self._audit_db_checked,
            audit_db_has_rows=self._audit_db_has_rows,
            source_1=source_1,
            source_2=source_2,
            isin=isin,
            data_date=data_date,
            field=field,
            left=left,
            right=right,
            result=result,
        )
        if exists:
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
        average_abs_pct = sum(abs(diff) for diff in values) / Decimal(len(values))
        min_abs_pct = min(abs(diff) for diff in values)
        if same_sign and average_abs_pct >= Decimal("0.01") and min_abs_pct >= Decimal("0.005"):
            self.review_service.queue_review(
                session,
                category="SYSTEMATIC_DISAGREEMENT",
                isin=isin,
                event_date=None,
                reason="Consecutive directional disagreement across five observations",
                payload={
                    "average_abs_diff_pct": str(average_abs_pct),
                    "min_abs_diff_pct": str(min_abs_pct),
                    "last_five": [
                        {"trade_date": trade_date.isoformat(), "signed_diff": str(diff)}
                        for trade_date, diff in last_five
                    ]
                },
            )
