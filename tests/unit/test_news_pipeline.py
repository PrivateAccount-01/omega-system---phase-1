from __future__ import annotations

from datetime import UTC, datetime

from omegadata.track_a.news_pipeline import EventImpactEngine, NewsEvent


class FakeCache:
    def __init__(self) -> None:
        self.items: dict[str, tuple[dict[str, object], object]] = {}

    def set_json(self, key: str, value: dict[str, object], ttl) -> None:  # noqa: ANN001
        self.items[key] = (value, ttl)


def test_processing_deadlines_follow_spec() -> None:
    engine = EventImpactEngine(cache=FakeCache())
    market_event = NewsEvent(
        event_id="evt-1",
        event_type="MONETARY_POLICY_CHANGE",
        timestamp=datetime(2026, 4, 10, 8, 0, tzinfo=UTC),
        magnitude_score=0.9,
        direction=1.0,
        source="RBI",
    )
    sector_event = NewsEvent(
        event_id="evt-2",
        event_type="COMMODITY_SHOCK",
        timestamp=datetime(2026, 4, 10, 8, 0, tzinfo=UTC),
        magnitude_score=0.7,
        direction=-1.0,
        source="GOV",
        sector="AUTO",
    )
    company_event = NewsEvent(
        event_id="evt-3",
        event_type="EARNINGS_RELEASE",
        timestamp=datetime(2026, 4, 10, 8, 0, tzinfo=UTC),
        magnitude_score=0.5,
        direction=1.0,
        source="NSE",
        isin="INE009A01021",
    )
    gdelt_event = NewsEvent(
        event_id="evt-4",
        event_type="REGULATORY_CHANGE",
        timestamp=datetime(2026, 4, 10, 8, 0, tzinfo=UTC),
        magnitude_score=0.4,
        direction=-1.0,
        source="GDELT",
        sector="BANKS",
    )

    assert engine.processing_deadline_minutes(market_event) == 2
    assert engine.processing_deadline_minutes(sector_event) == 10
    assert engine.processing_deadline_minutes(company_event) == 30
    assert engine.processing_deadline_minutes(gdelt_event) == 20


def test_event_impact_cached_in_required_redis_shape() -> None:
    cache = FakeCache()
    engine = EventImpactEngine(cache=cache)
    as_of = datetime(2026, 4, 10, 12, 0, tzinfo=UTC)
    events = [
        NewsEvent(
            event_id="evt-market",
            event_type="GLOBAL_RISK_OFF",
            timestamp=datetime(2026, 4, 10, 11, 0, tzinfo=UTC),
            magnitude_score=0.8,
            direction=-1.0,
            source="GDELT",
        ),
        NewsEvent(
            event_id="evt-company",
            event_type="MANAGEMENT_CHANGE",
            timestamp=datetime(2026, 4, 10, 11, 30, tzinfo=UTC),
            magnitude_score=0.3,
            direction=1.0,
            source="NSE",
            isin="INE009A01021",
        ),
    ]

    snapshot = engine.cache_current_impact(
        isin="INE009A01021",
        sector="IT",
        events=events,
        as_of=as_of,
    )

    assert snapshot is not None
    payload, ttl = cache.items["signal:event_impact:INE009A01021:current"]
    assert payload["dominant_event"] == "evt-market"
    assert payload["event_type"] == "GLOBAL_RISK_OFF"
    assert payload["score"] < 0
    assert payload["confidence"] == 1.0
    assert ttl.total_seconds() == 4 * 60 * 60
