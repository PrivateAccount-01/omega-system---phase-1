from __future__ import annotations

import json
import os
from datetime import date
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

os.environ["OMEGA_DB_URL"] = "sqlite:///./test_api.db"

from omegadata.api import main as api_main
from omegadata.api.main import app
from omegadata.config import settings
from omegadata.db.models import CorporateActionStaging, PriceRecord
from omegadata.db.session import get_session, init_db
from omegadata.domain import CorporateActionType, Exchange, InstrumentType
from omegadata.pipelines.sequential_pipeline import OmegaDataSequentialPipeline
from omegadata.track_a.download_manager import DownloadManager
from omegadata.track_b.confidence import ConfidenceInputs, ConfidenceScorer
from omegadata.track_b.isin_master import ISINMasterService


def test_api_threshold_enforcement() -> None:
    settings.db_url = "sqlite:///./test_api.db"
    init_db()
    scorer = ConfidenceScorer()
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
        backtest = client.get("/prices/INE009A01021?context=BACKTEST")
        assert backtest.status_code == 200
        assert len(backtest.json()["records"]) >= 1

        live = client.get("/prices/INE009A01021?context=LIVE_SIGNAL")
        assert live.status_code == 200
        assert live.json()["excluded_records"] >= 1


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
        audit = client.get("/implementation/audit")
        assert audit.status_code == 200
        assert audit.json()["counts"]["implemented"] == 1

        test_results = client.get("/implementation/test-results")
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
        assert Decimal(str(row.confidence_score)) == Decimal("0.50")


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
        return payloads.pop(0)

    monkeypatch.setattr(manager, "_bootstrap_nse_session", lambda client: None)
    monkeypatch.setattr(manager, "_request_with_workarounds", fake_request)
    monkeypatch.setattr(manager, "_validate_payload", lambda source_key, payload: None)

    first = manager.download("NSE_EQUITY_BHAVCOPY", date(2024, 1, 2))
    second = manager.download("NSE_EQUITY_BHAVCOPY", date(2024, 1, 2))

    assert first.path != second.path
    assert first.path.exists()
    assert second.path.exists()
    assert first.manifest_path.exists()
    assert second.manifest_path.exists()
