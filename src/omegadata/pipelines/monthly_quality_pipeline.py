from __future__ import annotations

from datetime import date

from omegadata.db.session import get_session
from omegadata.track_a.quality_reporting import MonthlyDataQualityReporter, ReportResult


def run_monthly_quality_report(as_of: date) -> ReportResult:
    reporter = MonthlyDataQualityReporter()
    with get_session() as session:
        return reporter.run_for_previous_month(session=session, as_of=as_of)
