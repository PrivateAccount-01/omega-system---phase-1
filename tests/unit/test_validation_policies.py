from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import delete

from omegadata.api.main import app
from omegadata.config import settings
from omegadata.db.models import InstrumentMaster, ManualReviewQueue, PriceRecord, ReprocessJob
from omegadata.db.session import get_session, init_db
from omegadata.domain import CorporateActionType, Exchange, InstrumentType
from omegadata.track_b.corporate_action_matching import CorporateActionMatcher
from omegadata.track_b.cross_source_validation import CrossSourceValidator
from omegadata.track_b.matching_policy import invalidate_matching_policy_cache
from omegadata.track_b.tolerance_policy import invalidate_tolerance_policy_cache


def test_cross_source_validator_uses_loaded_tolerance_policy(tmp_path: Path, monkeypatch) -> None:
    policy_path = tmp_path / "tolerance_policy.json"
    policy_path.write_text(
        json.dumps(
            {
                "version": "test",
                "entries": [
                    {
                        "liquidity_bucket": "micro",
                        "source_quality": "official",
                        "field": "close_price",
                        "imputed": False,
                        "tolerance_pct": "0.0099",
                        "warning_breach_rate_limit": 0.08,
                        "fail_breach_rate_limit": 0.02,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "cross_source_tolerance_policy_path", str(policy_path))
    invalidate_tolerance_policy_cache()

    row = PriceRecord(
        isin="INETEST00001",
        exchange=Exchange.NSE,
        trade_date=date(2026, 4, 10),
        open_price=Decimal("100"),
        high_price=Decimal("100"),
        low_price=Decimal("100"),
        close_price=Decimal("10"),
        volume=Decimal("1000"),
        raw_source="nse_bhavcopy",
        confidence_score=Decimal("1.00"),
    )
    peer = PriceRecord(
        isin="INETEST00001",
        exchange=Exchange.BSE,
        trade_date=date(2026, 4, 10),
        open_price=Decimal("100"),
        high_price=Decimal("100"),
        low_price=Decimal("100"),
        close_price=Decimal("10"),
        volume=Decimal("1000"),
        raw_source="bse_bhavcopy",
        confidence_score=Decimal("1.00"),
    )
    context = CrossSourceValidator._price_tolerance_context(nse=row, bse=peer, field="close_price")
    assert context.tolerance == Decimal("0.0099")


def test_corporate_action_matcher_uses_policy_thresholds(tmp_path: Path, monkeypatch) -> None:
    policy_path = tmp_path / "matching_policy.json"
    policy_path.write_text(
        json.dumps(
            {
                "version": "test",
                "pair_max_gap_days": 5,
                "related_candidate_gap_days": 3,
                "high_similarity_threshold": 90,
                "ambiguous_similarity_threshold": 40,
                "pair_min_score": 50,
                "economic_overlap_bonus": 5,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "corporate_action_matching_policy_path", str(policy_path))
    invalidate_matching_policy_cache()
    matcher = CorporateActionMatcher()

    left = SimpleNamespace(
        id=1,
        isin="INE536H01010",
        action_type=CorporateActionType.DIVIDEND_CASH,
        announcement_date=date(2026, 3, 19),
        ex_date=date(2026, 4, 22),
        record_date=None,
        payload={"dividend_per_share": "7"},
    )
    right = SimpleNamespace(
        id=2,
        isin="INE536H01010",
        action_type=CorporateActionType.DIVIDEND_CASH,
        announcement_date=date(2026, 3, 19),
        ex_date=date(2026, 4, 29),
        record_date=None,
        payload={},
    )
    assert matcher.relatedness_score(left, right) < 0


def test_release_readiness_blocks_on_overdue_review(tmp_path: Path) -> None:
    db_path = tmp_path / "readiness.db"
    settings.db_url = f"sqlite:///{db_path}"
    init_db()
    artifacts_dir = Path("artifacts/verification")
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.joinpath("source_probe_report.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-13T00:00:00+00:00",
                "calendar_config_state": "loaded",
                "summary": {
                    "bse_primary_validated": True,
                    "healthy_fallback_count": 1,
                    "failed_fallback_count": 0,
                },
            }
        ),
        encoding="utf-8",
    )
    artifacts_dir.joinpath("cross_source_tolerance_report.json").write_text(
        json.dumps({"generated_at": "2026-04-13T00:00:00+00:00", "status": "ok"}),
        encoding="utf-8",
    )
    artifacts_dir.joinpath("corporate_action_matching_report.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-13T00:00:00+00:00",
                "status": "ok",
                "metrics": {"benchmark_passed": True, "precision": 1.0, "recall": 1.0},
            }
        ),
        encoding="utf-8",
    )

    with get_session() as session:
        session.execute(delete(ReprocessJob))
        session.execute(delete(ManualReviewQueue))
        session.execute(delete(PriceRecord))
        session.execute(delete(InstrumentMaster))
        session.add(
            InstrumentMaster(
                isin="INEREADY0001",
                instrument_type=InstrumentType.EQUITY,
                primary_exchange=Exchange.NSE,
                company_name="Readiness Co",
                listed_date=date(2020, 1, 1),
                active=True,
            )
        )
        session.add(
            ManualReviewQueue(
                category="CROSS_SOURCE_VALIDATION_FAIL",
                isin="INEREADY0001",
                event_date=date(2026, 4, 10),
                reason="Mismatch",
                payload={"sla_breached": True, "requires_reprocess": False},
                resolved=False,
            )
        )

    headers = {"x-api-key": settings.api_key}
    with TestClient(app) as client:
        response = client.get("/release/readiness", headers=headers)
        assert response.status_code == 200
        payload = response.json()
        assert payload["ready"] is False
        assert any(check["name"] == "overdue_blocking_reviews" and not check["passed"] for check in payload["checks"])
