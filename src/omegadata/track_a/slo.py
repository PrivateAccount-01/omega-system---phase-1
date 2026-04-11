from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from statistics import quantiles


@dataclass(frozen=True)
class SLOSnapshot:
    window_minutes: int
    total_requests: int
    availability: float
    p95_latency_ms: float
    availability_target: float
    p95_target_ms: float
    availability_breach: bool
    latency_breach: bool


class SLOTracker:
    def __init__(self, window_minutes: int = 5, availability_target: float = 0.995, p95_target_ms: float = 750.0):
        self.window_minutes = window_minutes
        self.availability_target = availability_target
        self.p95_target_ms = p95_target_ms
        self._events: deque[tuple[datetime, int, float]] = deque()

    def record(self, status_code: int, latency_ms: float) -> None:
        now = datetime.now(UTC)
        self._events.append((now, status_code, latency_ms))
        self._evict_old(now)

    def snapshot(self) -> SLOSnapshot:
        now = datetime.now(UTC)
        self._evict_old(now)
        if not self._events:
            return SLOSnapshot(
                window_minutes=self.window_minutes,
                total_requests=0,
                availability=1.0,
                p95_latency_ms=0.0,
                availability_target=self.availability_target,
                p95_target_ms=self.p95_target_ms,
                availability_breach=False,
                latency_breach=False,
            )

        total = len(self._events)
        successes = sum(1 for _, status, _ in self._events if status < 500)
        availability = successes / total
        latencies = [latency for _, _, latency in self._events]
        p95 = quantiles(latencies, n=100)[94] if len(latencies) >= 20 else max(latencies)

        return SLOSnapshot(
            window_minutes=self.window_minutes,
            total_requests=total,
            availability=availability,
            p95_latency_ms=p95,
            availability_target=self.availability_target,
            p95_target_ms=self.p95_target_ms,
            availability_breach=availability < self.availability_target,
            latency_breach=p95 > self.p95_target_ms,
        )

    def _evict_old(self, now: datetime) -> None:
        threshold = now - timedelta(minutes=self.window_minutes)
        while self._events and self._events[0][0] < threshold:
            self._events.popleft()
