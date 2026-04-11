from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from omegadata.config import settings
from omegadata.db.models import ConfirmedCorporateAction, PriceRecord, ValidationAuditLog
from omegadata.domain import ConfidenceLevel, CorporateActionType, Exchange, ValidationResult
from omegadata.track_a.alerting import AlertEvent, AlertRouter
from omegadata.track_a.download_manager import DownloadManager
from omegadata.track_a.quality_reporting import MonthlyDataQualityReporter
from omegadata.track_a.slo import SLOTracker


def test_slo_tracker_breach_flags() -> None:
    tracker = SLOTracker(window_minutes=5, availability_target=0.995, p95_target_ms=200)
    for _ in range(30):
        tracker.record(status_code=200, latency_ms=100)
    for _ in range(2):
        tracker.record(status_code=500, latency_ms=450)
    snapshot = tracker.snapshot()
    assert snapshot.total_requests == 32
    assert snapshot.availability_breach is True
    assert snapshot.latency_breach is True


def test_alert_router_suppressed_without_webhook() -> None:
    original_webhook = settings.alert_webhook_url
    original_min = settings.alert_min_severity
    settings.alert_webhook_url = ""
    settings.alert_min_severity = "WARN"
    try:
        router = AlertRouter()
        sent = router.route(
            AlertEvent(
                severity="INFO",
                title="info",
                message="suppressed",
                source="test",
                created_at=datetime.utcnow(),
            )
        )
        assert sent is False
    finally:
        settings.alert_webhook_url = original_webhook
        settings.alert_min_severity = original_min


def test_monthly_quality_report_generation(db_session, tmp_path) -> None:
    original_report_root = settings.report_root
    settings.report_root = str(tmp_path)
    try:
        db_session.add(
            PriceRecord(
                isin="INE009A01021",
                exchange=Exchange.NSE,
                trade_date=date(2026, 3, 10),
                open_price=Decimal("100"),
                high_price=Decimal("101"),
                low_price=Decimal("99"),
                close_price=Decimal("100"),
                volume=Decimal("1000"),
                raw_source="nse_bhavcopy",
                confidence_score=Decimal("0.00"),
            )
        )
        db_session.add(
            ValidationAuditLog(
                validation_date=datetime(2026, 3, 12),
                source_1="NSE",
                source_2="BSE",
                isin="INE009A01021",
                data_date=date(2026, 3, 10),
                field_compared="close_price",
                source_1_value="100",
                source_2_value="101",
                difference_absolute=Decimal("1"),
                difference_pct=Decimal("0.0099"),
                tolerance_applied=Decimal("0.001"),
                result=ValidationResult.FAIL,
                resolution_status="OPEN",
                resolution_notes=None,
            )
        )
        db_session.add(
            ConfirmedCorporateAction(
                isin="INE009A01021",
                action_type=CorporateActionType.BONUS,
                confidence=ConfidenceLevel.HIGH,
                announcement_date=date(2026, 3, 1),
                ex_date=date(2026, 3, 20),
                record_date=date(2026, 3, 21),
                parameters={"bonus_ratio_numerator": "1", "bonus_ratio_denominator": "1"},
                source_preference=Exchange.NSE,
                superseded=False,
                created_at=datetime(2026, 3, 21),
            )
        )
        reporter = MonthlyDataQualityReporter()
        result = reporter.generate(db_session, year=2026, month=3)
        assert result.path.exists()
    finally:
        settings.report_root = original_report_root


def test_download_manager_candidate_urls_include_failover() -> None:
    manager = DownloadManager()
    candidates = manager._candidate_urls("NSE_CORPORATE_ACTIONS", date(2026, 4, 7))
    assert len(candidates) >= 2
    assert any("corporate-announcements" in url for url in candidates)
