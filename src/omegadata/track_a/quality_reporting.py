from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from omegadata.config import settings
from omegadata.db.models import ConfirmedCorporateAction, ValidationAuditLog
from omegadata.domain import ConfidenceLevel, ValidationResult
from omegadata.track_a.alerting import AlertEvent, AlertRouter
from omegadata.track_b.confidence import ConfidenceScorer


@dataclass(frozen=True)
class ReportResult:
    year: int
    month: int
    path: Path


class MonthlyDataQualityReporter:
    def __init__(self) -> None:
        self.confidence = ConfidenceScorer()
        self.alert_router = AlertRouter()
        self.report_root = Path(settings.report_root)
        self.report_root.mkdir(parents=True, exist_ok=True)

    def generate(self, session: Session, year: int, month: int) -> ReportResult:
        current = self.confidence.monthly_report(session, year=year, month=month)
        prev = self._prev_month(year, month)
        previous = self.confidence.monthly_report(session, year=prev[0], month=prev[1])

        validation_stats = self._validation_summary(session, year, month)
        ca_coverage = self._corporate_action_coverage(session, year, month)

        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "period": {"year": year, "month": month},
            "records_processed": current["records"],
            "confidence_histogram": current["histogram"],
            "below_thresholds": current["below_thresholds"],
            "zero_confidence_count": current["zero_confidence_count"],
            "trend_vs_previous_month": {
                "records_delta": current["records"] - previous.get("records", 0),
                "zero_confidence_delta": current["zero_confidence_count"]
                - previous.get("zero_confidence_count", 0),
            },
            "validation_summary": validation_stats,
            "corporate_action_dual_source_coverage": ca_coverage,
        }

        out_dir = self.report_root / f"year={year:04d}" / f"month={month:02d}"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "data_quality_report.json"
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

        if current["records"] > 0:
            zero_rate = current["zero_confidence_count"] / current["records"]
            if zero_rate > 0.001:
                self.alert_router.route(
                    AlertEvent(
                        severity="ERROR",
                        title="OmegaData Quality Breach",
                        message=(
                            f"Zero-confidence record ratio {zero_rate:.4%} exceeds 0.10% monthly threshold"
                        ),
                        source="monthly_quality_report",
                        created_at=datetime.now(timezone.utc),
                    )
                )

        return ReportResult(year=year, month=month, path=out_path)

    @staticmethod
    def _prev_month(year: int, month: int) -> tuple[int, int]:
        if month == 1:
            return year - 1, 12
        return year, month - 1

    @staticmethod
    def _validation_summary(session: Session, year: int, month: int) -> dict[str, int]:
        counts = {
            ValidationResult.PASS.value: 0,
            ValidationResult.WARN.value: 0,
            ValidationResult.FAIL.value: 0,
        }
        rows = session.execute(
            select(ValidationAuditLog.result, func.count())
            .where(extract("year", ValidationAuditLog.validation_date) == year)
            .where(extract("month", ValidationAuditLog.validation_date) == month)
            .group_by(ValidationAuditLog.result)
        ).all()
        for result, count in rows:
            counts[result.value] = int(count)
        return counts

    @staticmethod
    def _corporate_action_coverage(session: Session, year: int, month: int) -> float:
        total = session.scalar(
            select(func.count())
            .select_from(ConfirmedCorporateAction)
            .where(extract("year", ConfirmedCorporateAction.created_at) == year)
            .where(extract("month", ConfirmedCorporateAction.created_at) == month)
        )
        high = session.scalar(
            select(func.count())
            .select_from(ConfirmedCorporateAction)
            .where(extract("year", ConfirmedCorporateAction.created_at) == year)
            .where(extract("month", ConfirmedCorporateAction.created_at) == month)
            .where(ConfirmedCorporateAction.confidence == ConfidenceLevel.HIGH)
        )
        if not total:
            return 0.0
        return float(high / total)

    def run_for_previous_month(self, session: Session, as_of: date) -> ReportResult:
        prev = self._prev_month(as_of.year, as_of.month)
        return self.generate(session=session, year=prev[0], month=prev[1])
