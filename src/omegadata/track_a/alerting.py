from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import httpx

from omegadata.config import settings
from omegadata.track_a.monitoring import ALERT_COUNTER


@dataclass(frozen=True)
class AlertEvent:
    severity: str
    title: str
    message: str
    source: str
    created_at: datetime


class AlertRouter:
    def __init__(self) -> None:
        self.webhook_url = settings.alert_webhook_url
        self.min_severity = settings.alert_min_severity.upper()
        self.severity_rank = {"INFO": 10, "WARN": 20, "ERROR": 30, "CRITICAL": 40}

    def _should_send(self, severity: str) -> bool:
        incoming = self.severity_rank.get(severity.upper(), 0)
        threshold = self.severity_rank.get(self.min_severity, 20)
        return incoming >= threshold

    def route(self, event: AlertEvent) -> bool:
        if not self._should_send(event.severity):
            ALERT_COUNTER.labels(severity=event.severity, channel="webhook", status="suppressed").inc()
            return False
        if not self.webhook_url:
            ALERT_COUNTER.labels(severity=event.severity, channel="webhook", status="dropped").inc()
            return False

        payload = {
            "severity": event.severity,
            "title": event.title,
            "message": event.message,
            "source": event.source,
            "created_at": event.created_at.isoformat(),
        }
        try:
            response = httpx.post(self.webhook_url, json=payload, timeout=10.0)
            response.raise_for_status()
            ALERT_COUNTER.labels(severity=event.severity, channel="webhook", status="sent").inc()
            return True
        except Exception:  # noqa: BLE001
            ALERT_COUNTER.labels(severity=event.severity, channel="webhook", status="failed").inc()
            return False
