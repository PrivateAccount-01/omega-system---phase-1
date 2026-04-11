from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import exp

from omegadata.track_a.redis_cache import RedisCache

MARKET_WIDE_EVENT_TYPES = {
    "MONETARY_POLICY_CHANGE",
    "MONETARY_POLICY_GUIDANCE",
    "FISCAL_POLICY_BUDGET",
    "MARKET_CIRCUIT_BREAKER",
    "GLOBAL_RISK_OFF",
    "CURRENCY_STRESS",
}

SECTOR_EVENT_TYPES = {
    "REGULATORY_CHANGE",
    "COMMODITY_SHOCK",
    "CREDIT_EVENT",
    "POLICY_ANNOUNCEMENT",
}

COMPANY_EVENT_TYPES = {
    "EARNINGS_RELEASE",
    "PROMOTER_TRANSACTION",
    "BULK_BLOCK_DEAL",
    "CORPORATE_ACTION",
    "REGULATORY_ACTION",
    "MANAGEMENT_CHANGE",
}

DECAY_LAMBDA = 0.1
DEFAULT_TTL = timedelta(hours=4)


@dataclass(frozen=True)
class NewsEvent:
    event_id: str
    event_type: str
    timestamp: datetime
    magnitude_score: float
    direction: float
    source: str
    sector: str | None = None
    isin: str | None = None
    confidence: float = 1.0


@dataclass(frozen=True)
class EventImpact:
    isin: str
    score: float
    dominant_event: str
    event_type: str
    event_timestamp: str
    confidence: float
    expires_at: str


class EventImpactEngine:
    def __init__(self, cache: RedisCache | None = None) -> None:
        self.cache = cache or RedisCache()

    @staticmethod
    def processing_deadline_minutes(event: NewsEvent) -> int:
        if event.source.upper() == "GDELT":
            return 20
        if event.event_type in MARKET_WIDE_EVENT_TYPES:
            return 2
        if event.event_type in SECTOR_EVENT_TYPES:
            return 10
        return 30

    @staticmethod
    def relevance_score(
        event: NewsEvent,
        *,
        isin: str,
        sector: str | None,
    ) -> float:
        if event.event_type in MARKET_WIDE_EVENT_TYPES:
            return 1.0
        if event.event_type in SECTOR_EVENT_TYPES:
            return 1.0 if sector and event.sector and sector == event.sector else 0.1
        if event.event_type in COMPANY_EVENT_TYPES:
            return 1.0 if event.isin == isin else 0.0
        return 0.0

    @staticmethod
    def recency_weight(event_timestamp: datetime, as_of: datetime) -> float:
        if event_timestamp.tzinfo is None:
            event_timestamp = event_timestamp.replace(tzinfo=UTC)
        if as_of.tzinfo is None:
            as_of = as_of.replace(tzinfo=UTC)
        hours_since_event = max((as_of - event_timestamp).total_seconds() / 3600.0, 0.0)
        return float(exp(-DECAY_LAMBDA * hours_since_event))

    def compute_impact(
        self,
        event: NewsEvent,
        *,
        isin: str,
        sector: str | None,
        as_of: datetime,
    ) -> float:
        relevance = self.relevance_score(event, isin=isin, sector=sector)
        if relevance <= 0.0:
            return 0.0
        recency = self.recency_weight(event.timestamp, as_of=as_of)
        raw_score = event.direction * event.magnitude_score * relevance * recency
        return max(min(raw_score, 1.0), -1.0)

    def build_current_impact(
        self,
        *,
        isin: str,
        sector: str | None,
        events: Iterable[NewsEvent],
        as_of: datetime,
    ) -> EventImpact | None:
        ranked: list[tuple[float, NewsEvent]] = []
        for event in events:
            score = self.compute_impact(event, isin=isin, sector=sector, as_of=as_of)
            if abs(score) < 0.01:
                continue
            ranked.append((score, event))

        if not ranked:
            return None

        ranked.sort(key=lambda item: abs(item[0]), reverse=True)
        score, dominant = ranked[0]
        expires_at = as_of + DEFAULT_TTL
        return EventImpact(
            isin=isin,
            score=round(score, 6),
            dominant_event=dominant.event_id,
            event_type=dominant.event_type,
            event_timestamp=dominant.timestamp.astimezone(UTC).isoformat(),
            confidence=round(dominant.confidence, 6),
            expires_at=expires_at.astimezone(UTC).isoformat(),
        )

    def cache_current_impact(
        self,
        *,
        isin: str,
        sector: str | None,
        events: Iterable[NewsEvent],
        as_of: datetime,
    ) -> EventImpact | None:
        snapshot = self.build_current_impact(isin=isin, sector=sector, events=events, as_of=as_of)
        if snapshot is None:
            return None

        self.cache.set_json(
            f"signal:event_impact:{isin}:current",
            {
                "score": snapshot.score,
                "dominant_event": snapshot.dominant_event,
                "event_type": snapshot.event_type,
                "event_timestamp": snapshot.event_timestamp,
                "confidence": snapshot.confidence,
                "expires_at": snapshot.expires_at,
            },
            ttl=DEFAULT_TTL,
        )
        return snapshot
