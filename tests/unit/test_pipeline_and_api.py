from __future__ import annotations

import io
import json
import os
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

os.environ["OMEGA_DB_URL"] = "sqlite:///./test_api.db"

from omegadata.api import main as api_main
from omegadata.api.main import app
from omegadata.config import settings
from omegadata.db.models import (
    CorporateActionStaging,
    InstrumentMaster,
    ManualReviewQueue,
    PriceRecord,
)
from omegadata.db.session import get_session, init_db
from omegadata.domain import CorporateActionType, Exchange, InstrumentType, PublicationState
from omegadata.pipelines.sequential_pipeline import OmegaDataSequentialPipeline
from omegadata.track_a.download_manager import DownloadError, DownloadManager, FetchResult
from omegadata.track_a.trading_calendar import TradingCalendar
from omegadata.track_b.confidence import ConfidenceInputs, ConfidenceScorer
from omegadata.track_b.isin_master import ISINMasterService
from omegadata.track_b.review_policy import invalidate_review_policy_cache, load_review_policies


def test_api_threshold_enforcement(tmp_path: Path) -> None:
    db_path = tmp_path / "api_threshold.db"
    settings.db_url = f"sqlite:///{db_path}"
    init_db()
    scorer = ConfidenceScorer()
    with get_session() as session:
        session.execute(delete(InstrumentMaster))
        session.execute(delete(PriceRecord))
        session.add_all(
            [
                InstrumentMaster(
                    isin="INE009A01021",
                    instrument_type=InstrumentType.EQUITY,
                    primary_exchange=Exchange.NSE,
                    company_name="Aqylon Nexus Ltd",
                    listed_date=date(2020, 1, 1),
                    active=True,
                ),
                PriceRecord(
                    isin="INE009A01021",
                    exchange=Exchange.NSE,
                    trade_date=date(2024, 1, 1),
                    open_price=Decimal("100"),
                    high_price=Decimal("100"),
                    low_price=Decimal("100"),
                    close_price=Decimal("100"),
                    volume=Decimal("1000"),
                    raw_source="nse_bhavcopy",
                    confidence_score=scorer.compute_score(
                        ConfidenceInputs(
                            is_secondary_source=False,
                            cross_validation_available=True,
                            cross_validation_discrepancy_pct=Decimal("0.0"),
                            cross_validation_failed=False,
                            has_medium_ca=False,
                            has_low_ca=False,
                            rights_subscription_fallback_zero=False,
                            is_gap_fill=False,
                            is_reconstructed_universe=False,
                            discontinuity_category=None,
                        )
                    ),
                ),
                PriceRecord(
                    isin="INE009A01021",
                    exchange=Exchange.NSE,
                    trade_date=date(2024, 1, 2),
                    open_price=Decimal("100"),
                    high_price=Decimal("100"),
                    low_price=Decimal("100"),
                    close_price=Decimal("100"),
                    volume=Decimal("1000"),
                    raw_source="secondary_source",
                    confidence_score=scorer.compute_score(
                        ConfidenceInputs(
                            is_secondary_source=True,
                            cross_validation_available=False,
                            cross_validation_discrepancy_pct=None,
                            cross_validation_failed=False,
                            has_medium_ca=False,
                            has_low_ca=False,
                            rights_subscription_fallback_zero=False,
                            is_gap_fill=False,
                            is_reconstructed_universe=False,
                            discontinuity_category=None,
                        )
                    ),
                ),
            ]
        )

    with TestClient(app) as client:
        backtest = client.get("/prices/INE009A01021?context=BACKTEST&exchange=NSE")
        assert backtest.status_code == 200
        assert len(backtest.json()["records"]) >= 1
        assert backtest.json()["confidence_excluded_records"] == 0
        assert backtest.json()["blocked_records"] == 0

        live = client.get("/prices/INE009A01021?context=LIVE_SIGNAL&exchange=NSE")
        assert live.status_code == 200
        assert live.json()["excluded_records"] >= 1
        assert live.json()["confidence_excluded_records"] >= 1
        assert live.json()["blocked_records"] == 0


def test_verification_and_terminal_endpoints(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "verification"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(api_main, "ARTIFACT_DIR", root)
    (root / "implementation_audit.json").write_text(
        '{"generated_at":"now","counts":{"implemented":1,"partial":0,"missing":0},"severity_counts":{"critical":0,"high":0,"medium":0,"low":0,"none":1},"items":[]}',
        encoding="utf-8",
    )
    (root / "unit_test_results.txt").write_text("unit ok", encoding="utf-8")
    (root / "realdata_test_results.txt").write_text("real ok", encoding="utf-8")

    with TestClient(app) as client:
        headers = {"x-api-key": settings.api_key}
        audit = client.get("/implementation/audit", headers=headers)
        assert audit.status_code == 200
        assert audit.json()["counts"]["implemented"] == 1

        test_results = client.get("/implementation/test-results", headers=headers)
        assert test_results.status_code == 200
        assert "unit ok" in test_results.json()["unit"]

        terminal = client.get("/terminal")
        assert terminal.status_code == 200
        assert "OMEGADATA TERMINAL" in terminal.text


def test_bse_empty_meeting_rows_are_not_promoted_to_corporate_actions(db_session, tmp_path: Path) -> None:
    ISINMasterService().create_instrument(
        db_session,
        isin="INE009A01021",
        company_name="Aqylon Nexus Ltd",
        instrument_type=InstrumentType.EQUITY,
        primary_exchange=Exchange.NSE,
        listed_date=date(2020, 1, 1),
        symbol="AQYLON",
    )
    payload = [
        {
            "scrip_Code": "530943",
            "short_name": "AQYLON",
            "Long_Name": "Aqylon Nexus Ltd",
            "meeting_date": "11 Apr 2026",
            "URL": "https://www.bseindia.com/example",
        }
    ]
    path = tmp_path / "bse_rows.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = OmegaDataSequentialPipeline()._load_corporate_actions(db_session, Exchange.BSE, path)
    assert loaded == 0
    assert db_session.scalar(select(CorporateActionStaging)) is None


def test_nse_buyback_is_classified_without_unclassified_fallback(db_session, tmp_path: Path) -> None:
    payload = [
        {
            "isin": "INE000A01002",
            "symbol": "BUYBACKCO",
            "subject": "Buy Back",
            "exDate": "2026-04-17",
            "recDate": "2026-04-17",
        }
    ]
    path = tmp_path / "nse_rows.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = OmegaDataSequentialPipeline()._load_corporate_actions(db_session, Exchange.NSE, path)
    assert loaded == 1
    row = db_session.scalar(select(CorporateActionStaging))
    assert row is not None
    assert row.action_type == CorporateActionType.BUYBACK_OPEN_MARKET


def test_nse_subject_parsing_extracts_core_corporate_action_parameters(
    db_session,
    tmp_path: Path,
) -> None:
    payload = [
        {
            "isin": "INE219Y01018",
            "symbol": "RMDRIP",
            "subject": "Bonus 5:7",
            "exDate": "2026-04-10",
            "recDate": "2026-04-10",
        },
        {
            "isin": "INE124Y01010",
            "symbol": "PASHUPATI",
            "subject": "Face Value Split (Sub-Division) - From Rs 10/- Per Share To Re 1/- Per Share",
            "exDate": "2026-04-17",
            "recDate": "2026-04-17",
        },
        {
            "isin": "INE039O01011",
            "symbol": "JASH",
            "subject": "Interim Dividend - Re 0.60 Per Share",
            "exDate": "2026-04-10",
            "recDate": "2026-04-10",
        },
    ]
    path = tmp_path / "nse_subject_rows.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = OmegaDataSequentialPipeline()._load_corporate_actions(db_session, Exchange.NSE, path)
    assert loaded == 3

    rows = db_session.scalars(
        select(CorporateActionStaging).order_by(CorporateActionStaging.isin.asc())
    ).all()
    assert len(rows) == 3

    by_isin = {row.isin: row for row in rows}
    bonus = by_isin["INE219Y01018"]
    split = by_isin["INE124Y01010"]
    dividend = by_isin["INE039O01011"]

    assert bonus.action_type == CorporateActionType.BONUS
    assert bonus.payload["bonus_ratio_numerator"] == "5"
    assert bonus.payload["bonus_ratio_denominator"] == "7"

    assert split.action_type == CorporateActionType.SPLIT
    assert split.payload["old_face_value"] == "10"
    assert split.payload["new_face_value"] == "1"

    assert dividend.action_type == CorporateActionType.DIVIDEND_CASH
    assert dividend.payload["dividend_per_share"] == "0.60"


def test_run_track_b_preserves_failed_cross_source_validation_penalty(tmp_path: Path) -> None:
    db_path = tmp_path / "trackb_penalty.db"
    settings.db_url = f"sqlite:///{db_path}"
    settings.market_proxy_isin = "MARKET000001"
    init_db()

    with get_session() as session:
        session.execute(delete(PriceRecord))
        session.add_all(
            [
                PriceRecord(
                    isin="INE009A01021",
                    exchange=Exchange.NSE,
                    trade_date=date(2024, 1, 1),
                    open_price=Decimal("100"),
                    high_price=Decimal("100"),
                    low_price=Decimal("100"),
                    close_price=Decimal("100"),
                    volume=Decimal("100"),
                    raw_source="nse_bhavcopy",
                    confidence_score=Decimal("1.00"),
                ),
                PriceRecord(
                    isin="INE009A01021",
                    exchange=Exchange.BSE,
                    trade_date=date(2024, 1, 1),
                    open_price=Decimal("110"),
                    high_price=Decimal("110"),
                    low_price=Decimal("110"),
                    close_price=Decimal("110"),
                    volume=Decimal("100"),
                    raw_source="bse_bhavcopy",
                    confidence_score=Decimal("1.00"),
                ),
                PriceRecord(
                    isin="MARKET000001",
                    exchange=Exchange.NSE,
                    trade_date=date(2024, 1, 1),
                    open_price=Decimal("200"),
                    high_price=Decimal("200"),
                    low_price=Decimal("200"),
                    close_price=Decimal("200"),
                    volume=Decimal("100"),
                    raw_source="nse_bhavcopy",
                    confidence_score=Decimal("1.00"),
                ),
            ]
        )

    OmegaDataSequentialPipeline().run_track_b(as_of=date(2024, 1, 1), market_isin="MARKET000001")

    with get_session() as session:
        row = session.scalar(
            select(PriceRecord)
            .where(PriceRecord.isin == "INE009A01021")
            .where(PriceRecord.exchange == Exchange.NSE)
            .where(PriceRecord.trade_date == date(2024, 1, 1))
        )
        assert row is not None
        assert Decimal(str(row.confidence_score)) == Decimal("0.00")


def test_run_track_b_requires_explicit_market_proxy(tmp_path: Path) -> None:
    db_path = tmp_path / "trackb_market_proxy.db"
    settings.db_url = f"sqlite:///{db_path}"
    settings.market_proxy_isin = ""
    init_db()

    with get_session() as session:
        session.execute(delete(PriceRecord))
        session.add(
            PriceRecord(
                isin="INE009A01021",
                exchange=Exchange.NSE,
                trade_date=date(2024, 1, 1),
                open_price=Decimal("100"),
                high_price=Decimal("100"),
                low_price=Decimal("100"),
                close_price=Decimal("100"),
                volume=Decimal("100"),
                raw_source="nse_bhavcopy",
                confidence_score=Decimal("1.00"),
            )
        )

    try:
        OmegaDataSequentialPipeline().run_track_b(as_of=date(2024, 1, 1), market_isin=None)
        raise AssertionError("expected ValueError when market proxy is absent")
    except ValueError as exc:
        assert "market_isin is required" in str(exc)


def test_bse_bhavcopy_loader_preserves_official_ohlc(tmp_path: Path, db_session) -> None:
    csv_payload = (
        "SC_CODE,SC_NAME,OPEN,HIGH,LOW,CLOSE,NO_OF_SHRS,ISIN_CODE\n"
        "500112,SBI,601.5,612.0,598.0,610.25,250000,INE062A01020\n"
    )
    zip_path = tmp_path / "bse.zip"
    import zipfile

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("EQ_ISINCODE_010124.CSV", csv_payload)

    loaded = OmegaDataSequentialPipeline()._load_bse_bhavcopy_prices(
        db_session,
        zip_path,
        date(2024, 1, 1),
    )
    row = db_session.scalar(select(PriceRecord).where(PriceRecord.exchange == Exchange.BSE))
    assert loaded == 1
    assert row is not None
    assert Decimal(str(row.open_price)) == Decimal("601.5")
    assert Decimal(str(row.high_price)) == Decimal("612.0")
    assert Decimal(str(row.low_price)) == Decimal("598.0")
    assert Decimal(str(row.close_price)) == Decimal("610.25")
    assert row.raw_source == "bse_bhavcopy"


def test_download_manager_stores_versioned_immutable_artifacts(tmp_path: Path, monkeypatch) -> None:
    settings.raw_root = str(tmp_path)
    manager = DownloadManager()
    payloads = [b"first-payload", b"second-payload"]

    def fake_request(*args, **kwargs):
        return FetchResult(
            payload=payloads.pop(0),
            status_code=200,
            content_type="application/octet-stream",
            transport="test",
        )

    monkeypatch.setattr(manager, "_bootstrap_nse_session", lambda client: None)
    monkeypatch.setattr(manager, "_request_with_workarounds", fake_request)
    monkeypatch.setattr(manager, "_validate_payload", lambda source_key, payload, **kwargs: None)

    first = manager.download("NSE_EQUITY_BHAVCOPY", date(2024, 1, 2))
    second = manager.download("NSE_EQUITY_BHAVCOPY", date(2024, 1, 2))

    assert first.path != second.path
    assert first.path.exists()
    assert second.path.exists()
    assert first.manifest_path.exists()
    assert second.manifest_path.exists()


def test_prices_endpoint_requires_canonical_exchange_when_primary_missing(tmp_path: Path) -> None:
    db_path = tmp_path / "api_missing_exchange.db"
    settings.db_url = f"sqlite:///{db_path}"
    init_db()
    with get_session() as session:
        session.execute(delete(PriceRecord))
        session.execute(delete(InstrumentMaster))
        session.add(
            PriceRecord(
                isin="INE000A01010",
                exchange=Exchange.NSE,
                trade_date=date(2024, 1, 1),
                open_price=Decimal("10"),
                high_price=Decimal("10"),
                low_price=Decimal("10"),
                close_price=Decimal("10"),
                volume=Decimal("100"),
                raw_source="nse_bhavcopy",
                confidence_score=Decimal("1.00"),
            )
        )

    with TestClient(app) as client:
        response = client.get("/prices/INE000A01010")
        assert response.status_code == 400
        assert "exchange is required" in response.json()["detail"]


def test_prices_endpoint_does_not_mix_exchanges_and_defaults_to_primary_exchange(tmp_path: Path) -> None:
    db_path = tmp_path / "api_canonical_exchange.db"
    settings.db_url = f"sqlite:///{db_path}"
    init_db()
    with get_session() as session:
        session.execute(delete(PriceRecord))
        session.execute(delete(InstrumentMaster))
        session.add(
            InstrumentMaster(
                isin="INE111A01010",
                instrument_type=InstrumentType.EQUITY,
                primary_exchange=Exchange.NSE,
                company_name="Canon Co",
                listed_date=date(2020, 1, 1),
                active=True,
            )
        )
        session.add_all(
            [
                PriceRecord(
                    isin="INE111A01010",
                    exchange=Exchange.NSE,
                    trade_date=date(2024, 1, 1),
                    open_price=Decimal("100"),
                    high_price=Decimal("101"),
                    low_price=Decimal("99"),
                    close_price=Decimal("100"),
                    volume=Decimal("100"),
                    raw_source="nse_bhavcopy",
                    confidence_score=Decimal("1.00"),
                ),
                PriceRecord(
                    isin="INE111A01010",
                    exchange=Exchange.BSE,
                    trade_date=date(2024, 1, 1),
                    open_price=Decimal("200"),
                    high_price=Decimal("201"),
                    low_price=Decimal("199"),
                    close_price=Decimal("200"),
                    volume=Decimal("100"),
                    raw_source="bse_bhavcopy",
                    confidence_score=Decimal("1.00"),
                ),
            ]
        )

    with TestClient(app) as client:
        response = client.get("/prices/INE111A01010")
        assert response.status_code == 200
        payload = response.json()
        assert payload["exchange"] == "NSE"
        assert len(payload["records"]) == 1
        assert payload["records"][0]["close_price"] == "100.000000"


def test_publication_status_blocks_forward_series_and_reprocess_workflow(tmp_path: Path) -> None:
    db_path = tmp_path / "api_publication_workflow.db"
    settings.db_url = f"sqlite:///{db_path}"
    init_db()
    with get_session() as session:
        session.execute(delete(ManualReviewQueue))
        session.execute(delete(PriceRecord))
        session.execute(delete(InstrumentMaster))
        session.add(
            InstrumentMaster(
                isin="INE222A01010",
                instrument_type=InstrumentType.EQUITY,
                primary_exchange=Exchange.NSE,
                company_name="Blocked Co",
                listed_date=date(2020, 1, 1),
                active=True,
            )
        )
        session.add_all(
            [
                PriceRecord(
                    isin="INE222A01010",
                    exchange=Exchange.NSE,
                    trade_date=date(2024, 1, 1),
                    open_price=Decimal("10"),
                    high_price=Decimal("10"),
                    low_price=Decimal("10"),
                    close_price=Decimal("10"),
                    volume=Decimal("100"),
                    raw_source="nse_bhavcopy",
                    confidence_score=Decimal("1.00"),
                ),
                PriceRecord(
                    isin="INE222A01010",
                    exchange=Exchange.NSE,
                    trade_date=date(2024, 1, 2),
                    open_price=Decimal("11"),
                    high_price=Decimal("11"),
                    low_price=Decimal("11"),
                    close_price=Decimal("11"),
                    volume=Decimal("100"),
                    raw_source="nse_bhavcopy",
                    confidence_score=Decimal("1.00"),
                ),
            ]
        )
        session.add(
            ManualReviewQueue(
                category="CORPORATE_ACTION_REQUIRED_FIELDS",
                isin="INE222A01010",
                event_date=date(2024, 1, 1),
                reason="Missing required fields in corporate action payload",
                payload={
                    "requires_reprocess": True,
                    "block_scope": "FORWARD_SERIES",
                    "reprocess_status": "REVIEW_PENDING",
                },
                resolved=False,
            )
        )

    headers = {"x-api-key": settings.api_key}
    with TestClient(app) as client:
        prices = client.get("/prices/INE222A01010?exchange=NSE&context=BACKTEST")
        assert prices.status_code == 200
        assert prices.json()["records"] == []
        assert prices.json()["blocked_records"] == 2
        assert prices.json()["confidence_excluded_records"] == 0
        assert prices.json()["excluded_date_range"] == ["2024-01-01", "2024-01-02"]

        status = client.get("/publication/status/INE222A01010?exchange=NSE", headers=headers)
        assert status.status_code == 200
        assert status.json()["state"] == PublicationState.BLOCKED.value
        assert status.json()["blocked_records"] == 2
        assert status.json()["blocked_dates"] == 2

        open_reviews = client.get("/reviews/open", headers=headers)
        assert open_reviews.status_code == 200
        review_id = open_reviews.json()[0]["id"]

        resolution = client.post(
            f"/reviews/{review_id}/resolve",
            headers=headers,
            json={"decision": "REMEDIATED", "reviewer": "ops", "notes": "fixed input and replay queued"},
        )
        assert resolution.status_code == 200
        assert resolution.json()["reprocess_status"] == "PENDING"

        still_blocked = client.get("/publication/status/INE222A01010?exchange=NSE", headers=headers)
        assert still_blocked.json()["blocked_records"] == 2

        completed = client.post(
            f"/reviews/{review_id}/reprocess-complete",
            headers=headers,
            json={"completed_by": "ops", "notes": "full replay complete"},
        )
        assert completed.status_code == 200

        released = client.get("/publication/status/INE222A01010?exchange=NSE", headers=headers)
        assert released.json()["state"] == PublicationState.PUBLISHABLE.value
        prices_after = client.get("/prices/INE222A01010?exchange=NSE&context=BACKTEST")
        assert len(prices_after.json()["records"]) == 2


def test_false_positive_resolution_unblocks_without_reprocess(tmp_path: Path) -> None:
    db_path = tmp_path / "api_false_positive.db"
    settings.db_url = f"sqlite:///{db_path}"
    init_db()
    with get_session() as session:
        session.execute(delete(ManualReviewQueue))
        session.execute(delete(PriceRecord))
        session.execute(delete(InstrumentMaster))
        session.add(
            InstrumentMaster(
                isin="INE333A01010",
                instrument_type=InstrumentType.EQUITY,
                primary_exchange=Exchange.NSE,
                company_name="False Positive Co",
                listed_date=date(2020, 1, 1),
                active=True,
            )
        )
        session.add(
            PriceRecord(
                isin="INE333A01010",
                exchange=Exchange.NSE,
                trade_date=date(2024, 1, 1),
                open_price=Decimal("10"),
                high_price=Decimal("10"),
                low_price=Decimal("10"),
                close_price=Decimal("10"),
                volume=Decimal("100"),
                raw_source="nse_bhavcopy",
                confidence_score=Decimal("1.00"),
            )
        )
        session.add(
            ManualReviewQueue(
                category="CORPORATE_ACTION_UNMATCHED",
                isin="INE333A01010",
                event_date=date(2024, 1, 1),
                reason="Unmatched staging record older than 48 hours",
                payload={
                    "requires_reprocess": True,
                    "block_scope": "FORWARD_SERIES",
                    "reprocess_status": "REVIEW_PENDING",
                },
                resolved=False,
            )
        )

    headers = {"x-api-key": settings.api_key}
    with TestClient(app) as client:
        before = client.get("/publication/status/INE333A01010?exchange=NSE", headers=headers)
        assert before.json()["state"] == PublicationState.BLOCKED.value

        open_reviews = client.get("/reviews/open", headers=headers)
        review_id = next(item["id"] for item in open_reviews.json() if item["isin"] == "INE333A01010")

        resolution = client.post(
            f"/reviews/{review_id}/resolve",
            headers=headers,
            json={"decision": "FALSE_POSITIVE", "reviewer": "ops", "notes": "source mismatch alert was incorrect"},
        )
        assert resolution.status_code == 200
        assert resolution.json()["reprocess_status"] == "NOT_REQUIRED"

        after = client.get("/publication/status/INE333A01010?exchange=NSE", headers=headers)
        assert after.json()["state"] == PublicationState.PUBLISHABLE.value

        rejected = client.post(
            f"/reviews/{review_id}/reprocess-complete",
            headers=headers,
            json={"completed_by": "ops", "notes": "should not be allowed"},
        )
        assert rejected.status_code == 400


def test_complete_reprocess_requires_pending_request_artifact(tmp_path: Path) -> None:
    db_path = tmp_path / "api_reprocess_validation.db"
    settings.db_url = f"sqlite:///{db_path}"
    settings.reprocess_root = str(tmp_path / "reprocess_queue")
    init_db()
    with get_session() as session:
        session.execute(delete(ManualReviewQueue))
        session.execute(delete(InstrumentMaster))
        session.add(
            InstrumentMaster(
                isin="INE444A01010",
                instrument_type=InstrumentType.EQUITY,
                primary_exchange=Exchange.NSE,
                company_name="Reprocess Guard Co",
                listed_date=date(2020, 1, 1),
                active=True,
            )
        )
        session.add(
            ManualReviewQueue(
                category="CORPORATE_ACTION_REQUIRED_FIELDS",
                isin="INE444A01010",
                event_date=date(2024, 1, 1),
                reason="Missing required fields in corporate action payload",
                payload={
                    "requires_reprocess": True,
                    "block_scope": "FORWARD_SERIES",
                    "reprocess_status": "PENDING",
                    "resolution": {
                        "decision": "REMEDIATED",
                        "reviewer": "ops",
                        "notes": "fixed",
                        "resolved_at": "2026-04-13T00:00:00+00:00",
                    },
                },
                resolved=True,
            )
        )

    headers = {"x-api-key": settings.api_key}
    with TestClient(app) as client:
        rejected = client.post(
            "/reviews/1/reprocess-complete",
            headers=headers,
            json={"completed_by": "ops", "notes": "missing request artifact"},
        )
        assert rejected.status_code == 400


def test_run_track_a_requires_bse_bhavcopy(monkeypatch, tmp_path: Path) -> None:
    pipeline = OmegaDataSequentialPipeline()

    def fake_ingest(source: str, as_of: date) -> str:
        if source == "BSE_EQUITY_BHAVCOPY":
            raise DownloadError(f"{source} unavailable for {as_of.isoformat()}")
        return str(tmp_path / f"{source}.bin")

    monkeypatch.setattr(pipeline.ingestor, "ingest_raw_source", fake_ingest)

    with pytest.raises(DownloadError):
        pipeline.run_track_a(date(2026, 4, 13))


def test_bse_candidate_extraction_uses_live_page_patterns() -> None:
    html = """
    <a href="https://www.bseindia.com/download/BhavCopy/Equity/BhavCopy_BSE_CM_0_0_0_20260410_F_0000.CSV">csv</a>
    <a href="https://www.bseindia.com/download/BhavCopy/Equity/EQ_ISINCODE_100426_T0.CSV">isin</a>
    <a href="https://www.bseindia.com/download/BhavCopy/Equity/BSE_EQ_BHAVCOPY_10042026_T0.ZIP">zip</a>
    """
    urls = DownloadManager._extract_bse_equity_urls(html, date(2026, 4, 10))
    assert urls == [
        "https://www.bseindia.com/download/BhavCopy/Equity/BhavCopy_BSE_CM_0_0_0_20260410_F_0000.CSV",
        "https://www.bseindia.com/download/BhavCopy/Equity/EQ_ISINCODE_100426_T0.CSV",
        "https://www.bseindia.com/download/BhavCopy/Equity/BSE_EQ_BHAVCOPY_10042026_T0.ZIP",
    ]


def test_bse_candidate_extraction_supports_relative_paths() -> None:
    html = """
    <a href="/download/BhavCopy/Equity/BhavCopy_BSE_CM_0_0_0_20260410_F_0000.CSV">csv</a>
    <div data-url="/download/BhavCopy/Equity/EQ_ISINCODE_100426_T0.CSV"></div>
    <script>const zip = "/download/BhavCopy/Equity/BSE_EQ_BHAVCOPY_10042026_T0.ZIP";</script>
    """
    urls = DownloadManager._extract_bse_equity_urls(html, date(2026, 4, 10))
    assert urls == [
        "https://www.bseindia.com/download/BhavCopy/Equity/BhavCopy_BSE_CM_0_0_0_20260410_F_0000.CSV",
        "https://www.bseindia.com/download/BhavCopy/Equity/EQ_ISINCODE_100426_T0.CSV",
        "https://www.bseindia.com/download/BhavCopy/Equity/BSE_EQ_BHAVCOPY_10042026_T0.ZIP",
    ]


def test_bse_candidate_detection_allows_bse_subdomains() -> None:
    assert DownloadManager._looks_like_bse_equity_url(
        "https://cdn.bseindia.com/download/BhavCopy/Equity/EQ_ISINCODE_100426_T0.CSV",
        date(2026, 4, 10),
    )


def test_bse_source_registry_primary_format_is_csv() -> None:
    from omegadata.track_a.source_registry import SOURCE_REGISTRY

    assert SOURCE_REGISTRY["BSE_EQUITY_BHAVCOPY"].eras[0].file_format == "csv"


def test_bse_zip_payload_validation_checks_contents() -> None:
    import zipfile

    bad_zip = io.BytesIO()
    with zipfile.ZipFile(bad_zip, "w") as zf:
        zf.writestr("unexpected.txt", "not a csv")

    with pytest.raises(DownloadError):
        DownloadManager._validate_payload("BSE_EQUITY_BHAVCOPY", bad_zip.getvalue())


def test_bse_zip_payload_validation_selects_expected_member_by_date() -> None:
    import zipfile

    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as zf:
        zf.writestr("other_file.csv", "junk,data\n1,2\n")
        zf.writestr(
            "BSE_EQ_BHAVCOPY_10042026_T0.csv",
            "SC_CODE,SC_NAME,OPEN,HIGH,LOW,CLOSE,LAST,PREVCLOSE,NO_TRADES,NO_OF_SHRS,NET_TURNOV,TDCLOINDI,ISIN_CODE\n"
            "500112,SBI,1,1,1,1,1,1,1,1,1,I,INE062A01020\n",
        )

    DownloadManager._validate_payload("BSE_EQUITY_BHAVCOPY", payload.getvalue(), as_of=date(2026, 4, 10))


def test_review_policy_cache_reloads_on_file_change(tmp_path: Path, monkeypatch) -> None:
    policy_path = tmp_path / "review_policies.json"
    policy_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "policies": {
                    "CROSS_SOURCE_VALIDATION_FAIL": {
                        "blocks_publication": True,
                        "scope": "RECORD",
                        "requires_reprocess": False,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "review_policy_path", str(policy_path))
    invalidate_review_policy_cache()

    first = load_review_policies()
    assert first.version == "v1"

    policy_path.write_text(
        json.dumps(
            {
                "version": "v2",
                "policies": {
                    "CROSS_SOURCE_VALIDATION_FAIL": {
                        "blocks_publication": True,
                        "scope": "INSTRUMENT",
                        "requires_reprocess": False,
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    second = load_review_policies()
    assert second.version == "v2"
    assert second.for_category("CROSS_SOURCE_VALIDATION_FAIL").scope.value == "INSTRUMENT"


def test_trading_calendar_skips_configured_holidays() -> None:
    calendar = TradingCalendar(
        holidays_by_exchange={
            "BSE": {date(2026, 4, 10)},
        }
    )
    days = calendar.recent_trading_days("BSE", anchor_date=date(2026, 4, 13), limit=2)
    assert days == [date(2026, 4, 9), date(2026, 4, 8)]
