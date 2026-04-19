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
    MarketIndexDaily,
    ParticipantFlowDaily,
    PriceRecord,
    ReleaseRecord,
    ReprocessJob,
    SymbolMap,
)
from omegadata.db.session import get_session, init_db
from omegadata.domain import (
    CorporateActionType,
    Exchange,
    InstrumentType,
    PublicationState,
    ReleaseProfile,
)
from omegadata.pipelines.sequential_pipeline import OmegaDataSequentialPipeline
from omegadata.track_a.download_manager import DownloadError, DownloadManager, FetchResult
from omegadata.track_a.trading_calendar import CalendarMaintenance, TradingCalendar
from omegadata.track_b.confidence import ConfidenceInputs, ConfidenceScorer
from omegadata.track_b.isin_master import ISINMasterService
from omegadata.track_b.release_manager import ReleaseManager
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


def test_ensure_instrument_is_idempotent_before_flush(db_session) -> None:
    pipe = OmegaDataSequentialPipeline()
    pipe._ensure_instrument(
        db_session,
        isin="INEIDEM00001",
        symbol="IDEMCO",
        trade_date=date(2026, 4, 10),
        exchange=Exchange.NSE,
    )
    pipe._ensure_instrument(
        db_session,
        isin="INEIDEM00001",
        symbol="IDEMCO",
        trade_date=date(2026, 4, 10),
        exchange=Exchange.NSE,
    )
    db_session.flush()
    assert db_session.scalar(select(InstrumentMaster).where(InstrumentMaster.isin == "INEIDEM00001")) is not None
    assert len(db_session.scalars(select(SymbolMap).where(SymbolMap.isin == "INEIDEM00001")).all()) == 1


def test_nse_request_workaround_can_fall_back_to_curl(monkeypatch) -> None:
    manager = DownloadManager()

    def fail_httpx(*args, **kwargs):  # noqa: ANN002, ANN003
        raise DownloadError("tls issue", stage="request")

    def fail_urllib(*args, **kwargs):  # noqa: ANN002, ANN003
        raise DownloadError("urllib issue", stage="request")

    def succeed_curl(*args, **kwargs):  # noqa: ANN002, ANN003
        return FetchResult(
            payload=b'{"ok": true}',
            status_code=200,
            content_type="application/json",
            transport="curl",
            request_attempts=1,
        )

    monkeypatch.setattr(manager, "_request", fail_httpx)
    monkeypatch.setattr(manager, "_request_via_urllib", fail_urllib)
    monkeypatch.setattr(manager, "_request_via_curl", succeed_curl)

    result = manager._request_with_workarounds(
        client=None,  # type: ignore[arg-type]
        url="https://www.nseindia.com/api/corporates-corporateActions?index=equities",
        request_headers={"User-Agent": "test"},
        timeout_seconds=1.0,
    )
    assert result.transport == "curl"


def test_nse_request_workaround_passes_bootstrapped_cookies_to_fallbacks(monkeypatch) -> None:
    manager = DownloadManager()
    seen_headers: dict[str, str] = {}

    def fail_httpx(*args, **kwargs):  # noqa: ANN002, ANN003
        raise DownloadError("tls issue", stage="request")

    def capture_urllib(*args, **kwargs):  # noqa: ANN002, ANN003
        seen_headers.update(kwargs["headers"])
        raise DownloadError("urllib issue", stage="request")

    def succeed_curl(*args, **kwargs):  # noqa: ANN002, ANN003
        seen_headers.update(kwargs["headers"])
        return FetchResult(
            payload=b'{"ok": true}',
            status_code=200,
            content_type="application/json",
            transport="curl",
            request_attempts=1,
        )

    monkeypatch.setattr(manager, "_request", fail_httpx)
    monkeypatch.setattr(manager, "_request_via_urllib", capture_urllib)
    monkeypatch.setattr(manager, "_request_via_curl", succeed_curl)

    class DummyClient:
        def __init__(self) -> None:
            self.cookies = {"bm_sv": "cookie123", "nsit": "cookie456"}

    result = manager._request_with_workarounds(
        client=DummyClient(),  # type: ignore[arg-type]
        url="https://www.nseindia.com/api/corporates-corporateActions?index=equities",
        request_headers={"User-Agent": "test"},
        timeout_seconds=1.0,
    )
    assert result.transport == "curl"
    assert "Cookie" in seen_headers
    assert "bm_sv=cookie123" in seen_headers["Cookie"]


def test_download_manager_reuses_cached_immutable_artifact(tmp_path: Path, monkeypatch) -> None:
    raw_root = tmp_path / "raw"
    monkeypatch.setattr(settings, "raw_root", str(raw_root))
    manager = DownloadManager()
    as_of = date(2026, 4, 13)
    out_dir = raw_root / "nse_corporate_actions" / "year=2026" / "month=04"
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact = out_dir / "20260413__cached.bin"
    artifact.write_bytes(b'{"ok": true}')
    checksum = manager._hash_content(artifact.read_bytes(), "sha256")
    manifest = {
        "source_key": "NSE_CORPORATE_ACTIONS",
        "as_of": as_of.isoformat(),
        "checksum": checksum,
        "artifact_path": artifact.as_posix().replace("/", "\\"),
        "bytes_downloaded": artifact.stat().st_size,
        "used_url": "https://www.nseindia.com/api/corporates-corporateActions?index=equities",
        "attempts": 1,
        "manifest_path": "20260413__cached.manifest.json",
    }
    latest = out_dir / "20260413.latest.json"
    latest.write_text(json.dumps(manifest), encoding="utf-8")

    def fail_fetch(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("network fetch should not be used when cache is valid")

    monkeypatch.setattr(manager, "_fetch_candidate", fail_fetch)
    cached = manager.download("NSE_CORPORATE_ACTIONS", as_of)
    assert cached.path == artifact
    assert cached.checksum == checksum


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


def test_side_feed_loaders_persist_structured_rows(db_session, tmp_path: Path) -> None:
    fii_payload = [
        {
            "category": "FII/FPI",
            "date": "10-Apr-2026",
            "buyValue": "18303.96",
            "sellValue": "17631.87",
            "netValue": "672.09",
        }
    ]
    index_payload = {
        "data": [
            {
                "key": "SECTORAL INDICES",
                "index": "NIFTY IT",
                "indexSymbol": "NIFTY IT",
                "last": 37500.25,
                "open": 37110.00,
                "high": 37610.00,
                "low": 37050.00,
                "previousClose": 37000.00,
                "percentChange": 1.35,
            },
            {
                "key": "INDICES ELIGIBLE IN DERIVATIVES",
                "index": "INDIA VIX",
                "indexSymbol": "INDIA VIX",
                "last": 12.55,
                "open": 12.10,
                "high": 12.80,
                "low": 12.00,
                "previousClose": 12.00,
                "percentChange": 4.58,
            },
        ]
    }
    fii_path = tmp_path / "fii.json"
    vix_path = tmp_path / "vix.json"
    fii_path.write_text(json.dumps(fii_payload), encoding="utf-8")
    vix_path.write_text(json.dumps(index_payload), encoding="utf-8")

    pipe = OmegaDataSequentialPipeline()
    assert pipe._load_fii_dii(db_session, fii_path) == 1
    assert pipe._load_market_indices(db_session, vix_path, date(2026, 4, 10)) == 2

    flow = db_session.scalar(select(ParticipantFlowDaily))
    assert flow is not None
    assert flow.participant_category == "FII/FPI"
    index_rows = db_session.scalars(select(MarketIndexDaily).order_by(MarketIndexDaily.index_symbol)).all()
    assert [row.index_kind for row in index_rows] == ["VIX", "SECTOR"]


def test_release_manager_builds_signed_release_artifact(db_session, tmp_path: Path, monkeypatch) -> None:
    db_session.add_all(
        [
            PriceRecord(
                isin="INE009A01021",
                exchange=Exchange.NSE,
                trade_date=date(2026, 4, 10),
                open_price=Decimal("100"),
                high_price=Decimal("105"),
                low_price=Decimal("95"),
                close_price=Decimal("102"),
                volume=Decimal("1000"),
                raw_source="nse_bhavcopy",
                adjusted_open_price=Decimal("90"),
                adjusted_high_price=Decimal("94.5"),
                adjusted_low_price=Decimal("85.5"),
                adjusted_close_price=Decimal("91.8"),
                adjusted_volume=Decimal("1100"),
                confidence_score=Decimal("1.00"),
                adjustment_chain=[],
            ),
            ParticipantFlowDaily(
                trade_date=date(2026, 4, 10),
                participant_category="FII/FPI",
                buy_value=Decimal("10"),
                sell_value=Decimal("8"),
                net_value=Decimal("2"),
                raw_source="nse_fii_dii",
                source_artifact_path="data/raw/nse_fii_dii/example.bin",
            ),
            MarketIndexDaily(
                trade_date=date(2026, 4, 10),
                index_name="INDIA VIX",
                index_symbol="INDIA VIX",
                index_kind="VIX",
                open_price=Decimal("10"),
                high_price=Decimal("11"),
                low_price=Decimal("9"),
                close_price=Decimal("10.5"),
                previous_close=Decimal("10"),
                change_pct=Decimal("5"),
                raw_source="india_vix_all_indices",
                source_artifact_path="data/raw/india_vix/example.bin",
            ),
        ]
    )
    monkeypatch.setattr(settings, "release_root", str(tmp_path / "releases"))

    def fake_sign(self, manifest_path: Path) -> Path:  # noqa: ANN001
        signature_path = manifest_path.with_suffix(".asc")
        signature_path.write_text("signed", encoding="utf-8")
        return signature_path

    monkeypatch.setattr(ReleaseManager, "_sign_manifest", fake_sign)
    monkeypatch.setattr(
        "omegadata.track_a.warehouse.ClickHouseWarehouseSync.sync_release_manifest",
        lambda *args, **kwargs: type("Result", (), {"status": "SYNCED", "details": "ok"})(),
    )

    manager = ReleaseManager()
    result = manager.build_release(db_session, as_of=date(2026, 4, 10), profile=ReleaseProfile.EQUITY_PLUS_SIDEFEEDS)
    assert result.manifest_path.exists()
    assert result.signature_path is not None and result.signature_path.exists()
    record = db_session.scalar(select(ReleaseRecord).where(ReleaseRecord.release_id == result.release_id))
    assert record is not None
    assert record.release_profile == ReleaseProfile.EQUITY_PLUS_SIDEFEEDS


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


def test_bse_bhavcopy_loader_supports_current_bse_primary_schema(tmp_path: Path, db_session) -> None:
    csv_payload = (
        "TradDt,BizDt,Sgmt,Src,FinInstrmTp,FinInstrmId,ISIN,TckrSymb,SctySrs,FinInstrmNm,OpnPric,HghPric,"
        "LwPric,ClsPric,TtlTradgVol\n"
        "2026-04-10,2026-04-10,CM,BSE,STK,500002,INE117A01022,ABB,A,ABB INDIA LIMITED,6665.25,6902.20,"
        "6615.00,6865.95,18932\n"
    )
    path = tmp_path / "bse_current.csv"
    path.write_text(csv_payload, encoding="utf-8")

    loaded = OmegaDataSequentialPipeline()._load_bse_bhavcopy_prices(
        db_session,
        path,
        date(2026, 4, 10),
    )
    row = db_session.scalar(
        select(PriceRecord)
        .where(PriceRecord.exchange == Exchange.BSE)
        .where(PriceRecord.isin == "INE117A01022")
    )
    assert loaded == 1
    assert row is not None
    assert Decimal(str(row.open_price)) == Decimal("6665.25")
    assert Decimal(str(row.high_price)) == Decimal("6902.20")
    assert Decimal(str(row.low_price)) == Decimal("6615.00")
    assert Decimal(str(row.close_price)) == Decimal("6865.95")
    assert Decimal(str(row.volume)) == Decimal("18932")


def test_download_manager_stores_versioned_immutable_artifacts(tmp_path: Path, monkeypatch) -> None:
    settings.raw_root = str(tmp_path)
    manager = DownloadManager()
    payloads = [b"first-payload"]

    def fake_request(*args, **kwargs):
        return FetchResult(
            payload=payloads.pop(0),
            status_code=200,
            content_type="application/octet-stream",
            transport="test",
            request_attempts=1,
        )

    monkeypatch.setattr(manager, "_bootstrap_nse_session", lambda client: None)
    monkeypatch.setattr(manager, "_request_with_workarounds", fake_request)
    monkeypatch.setattr(manager, "_validate_payload", lambda source_key, payload, **kwargs: None)

    first = manager.download("NSE_EQUITY_BHAVCOPY", date(2024, 1, 2))
    second = manager.download("NSE_EQUITY_BHAVCOPY", date(2024, 1, 2))

    assert first.path == second.path
    assert first.path.exists()
    assert second.path.exists()
    assert first.manifest_path.exists()
    assert second.manifest_path.exists()
    assert payloads == []


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


def test_prices_endpoint_excludes_synthetic_market_data_from_non_audit_contexts(tmp_path: Path) -> None:
    db_path = tmp_path / "api_synthetic_block.db"
    settings.db_url = f"sqlite:///{db_path}"
    init_db()
    with get_session() as session:
        session.execute(delete(PriceRecord))
        session.execute(delete(InstrumentMaster))
        session.add(
            InstrumentMaster(
                isin="INE555A01010",
                instrument_type=InstrumentType.EQUITY,
                primary_exchange=Exchange.BSE,
                company_name="Legacy Synthetic Co",
                listed_date=date(2020, 1, 1),
                active=True,
            )
        )
        session.add(
            PriceRecord(
                isin="INE555A01010",
                exchange=Exchange.BSE,
                trade_date=date(2024, 1, 1),
                open_price=Decimal("200"),
                high_price=Decimal("200"),
                low_price=Decimal("200"),
                close_price=Decimal("200"),
                volume=Decimal("100"),
                raw_source="bse_stockreach_graph",
                confidence_score=Decimal("1.00"),
            )
        )

    headers = {"x-api-key": settings.api_key}
    with TestClient(app) as client:
        blocked = client.get("/prices/INE555A01010?exchange=BSE&context=BACKTEST")
        assert blocked.status_code == 200
        assert blocked.json()["records"] == []
        assert blocked.json()["excluded_records"] == 1

        audit = client.get("/audit/prices/INE555A01010?exchange=BSE", headers=headers)
        assert audit.status_code == 200
        assert len(audit.json()["records"]) == 1


def test_publication_status_blocks_forward_series_and_reprocess_workflow(tmp_path: Path) -> None:
    db_path = tmp_path / "api_publication_workflow.db"
    settings.db_url = f"sqlite:///{db_path}"
    init_db()
    with get_session() as session:
        session.execute(delete(ManualReviewQueue))
        session.execute(delete(ReprocessJob))
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
        assert resolution.json()["reprocess_job_id"] is not None

        still_blocked = client.get("/publication/status/INE222A01010?exchange=NSE", headers=headers)
        assert still_blocked.json()["blocked_records"] == 2

        completed = client.post(
            f"/reviews/{review_id}/reprocess-complete",
            headers=headers,
            json={
                "completed_by": "ops",
                "notes": "full replay complete",
                "rebuilt_tables": ["price_record", "confirmed_corporate_action"],
                "rebuilt_isins": ["INE222A01010"],
                "validation_checks": ["cross_source_validation", "adjustment_chain_rebuild"],
                "evidence_paths": ["artifacts/verification/source_probe_report.json"],
                "date_range": {"start": "2024-01-01", "end": "2024-01-02"},
            },
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
        session.execute(delete(ReprocessJob))
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
            json={
                "completed_by": "ops",
                "notes": "should not be allowed",
                "rebuilt_tables": ["price_record"],
                "rebuilt_isins": ["INE333A01010"],
                "validation_checks": ["cross_source_validation"],
                "evidence_paths": ["artifacts/verification/source_probe_report.json"],
            },
        )
        assert rejected.status_code == 400


def test_complete_reprocess_requires_pending_request_artifact(tmp_path: Path) -> None:
    db_path = tmp_path / "api_reprocess_validation.db"
    settings.db_url = f"sqlite:///{db_path}"
    settings.reprocess_root = str(tmp_path / "reprocess_queue")
    init_db()
    with get_session() as session:
        session.execute(delete(ManualReviewQueue))
        session.execute(delete(ReprocessJob))
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
            json={
                "completed_by": "ops",
                "notes": "missing request artifact",
                "rebuilt_tables": ["price_record"],
                "rebuilt_isins": ["INE444A01010"],
                "validation_checks": ["cross_source_validation"],
                "evidence_paths": ["artifacts/verification/source_probe_report.json"],
            },
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

    source = SOURCE_REGISTRY["BSE_EQUITY_BHAVCOPY"]
    assert source.eras[0].file_format == "csv"
    assert source.failover_url_patterns == (
        "https://www.bseindia.com/download/BhavCopy/Equity/EQ_ISINCODE_{DDMMYY}_T0.CSV",
        "https://www.bseindia.com/download/BhavCopy/Equity/BSE_EQ_BHAVCOPY_{DDMMYYYY}_T0.ZIP",
    )
    assert source.deprecated_failover_url_patterns == (
        "https://www.bseindia.com/download/BhavCopy/Equity/EQ{DDMMYY}_CSV.ZIP",
        "https://www.bseindia.com/download/BhavCopy/Equity/eq{DDMMYY}_csv.zip",
        "https://www.bseindia.com/download/BhavCopy/Equity/EQ_ISINCODE_{DDMMYY}.ZIP",
    )


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
        },
        coverage_years_by_exchange={"BSE": {2026}},
    )
    days = calendar.recent_trading_days("BSE", anchor_date=date(2026, 4, 13), limit=2)
    assert days == [date(2026, 4, 9), date(2026, 4, 8)]


def test_trading_calendar_degrades_without_explicit_year_coverage() -> None:
    calendar = TradingCalendar(
        holidays_by_exchange={"BSE": {date(2026, 4, 10)}},
        coverage_years_by_exchange={"BSE": {2026}},
    )

    days = calendar.recent_trading_days("BSE", anchor_date=date(2027, 1, 5), limit=1)
    assert days == [date(2027, 1, 4)]

    with pytest.raises(ValueError):
        calendar.recent_trading_days("BSE", anchor_date=date(2027, 1, 5), limit=1, strict=True)


def test_trading_calendar_coverage_status_warns_near_expiry() -> None:
    calendar = TradingCalendar(
        holidays_by_exchange={"BSE": {date(2026, 12, 25)}},
        coverage_years_by_exchange={"BSE": {2026}},
    )

    status = calendar.coverage_status(
        "BSE",
        anchor_date=date(2026, 12, 1),
        warning_window_days=60,
    )

    assert status["status"] == "warning"
    assert status["warning"] is True
    assert status["latest_covered_year"] == 2026


def test_trading_calendar_loads_maintenance_metadata_from_config(tmp_path: Path, monkeypatch) -> None:
    holiday_path = tmp_path / "holidays.json"
    holiday_path.write_text(
        json.dumps(
            {
                "coverage_years": {"BSE": [2026]},
                "maintenance": {
                    "owner_role": "Market Ops",
                    "renewal_window_days": 45,
                    "runbook": "update annually",
                    "supported_exchanges": ["BSE"],
                },
                "holidays": {"BSE": ["2026-04-10"]},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "trading_holiday_path", str(holiday_path))

    calendar = TradingCalendar.from_config()
    assert calendar.maintenance.owner_role == "Market Ops"
    assert calendar.maintenance.renewal_window_days == 45
    assert calendar.maintenance.supported_exchanges == ("BSE",)


def test_trading_calendar_statuses_include_supported_exchanges_without_coverage() -> None:
    calendar = TradingCalendar(
        holidays_by_exchange={},
        coverage_years_by_exchange={},
        maintenance=CalendarMaintenance(supported_exchanges=("NSE", "BSE")),
    )

    statuses = calendar.all_coverage_statuses(
        anchor_date=date(2026, 4, 13),
        warning_window_days=60,
    )

    assert [status["exchange"] for status in statuses] == ["BSE", "NSE"]
    assert all(status["status"] == "missing" for status in statuses)


def test_trading_calendar_missing_config_still_reports_supported_exchange_statuses(
    tmp_path: Path,
    monkeypatch,
) -> None:
    missing_path = tmp_path / "missing_holidays.json"
    monkeypatch.setattr(settings, "trading_holiday_path", str(missing_path))

    calendar = TradingCalendar.from_config()
    assert calendar.config_state == "missing"
    assert calendar.config_path == missing_path.as_posix()
    statuses = calendar.all_coverage_statuses(
        anchor_date=date(2026, 4, 13),
        warning_window_days=calendar.maintenance.renewal_window_days,
    )

    by_exchange = {str(status["exchange"]): status for status in statuses}
    assert set(by_exchange) == {"BSE", "NSE"}
    assert all(status["status"] == "missing" for status in by_exchange.values())


def test_trading_calendar_invalid_config_reports_invalid_state(
    tmp_path: Path,
    monkeypatch,
) -> None:
    invalid_path = tmp_path / "invalid_holidays.json"
    invalid_path.write_text("{invalid json", encoding="utf-8")
    monkeypatch.setattr(settings, "trading_holiday_path", str(invalid_path))

    calendar = TradingCalendar.from_config()

    assert calendar.config_state == "invalid"
    assert calendar.config_path == invalid_path.as_posix()
    assert calendar.config_error is not None

    statuses = calendar.all_coverage_statuses(
        anchor_date=date(2026, 4, 13),
        warning_window_days=calendar.maintenance.renewal_window_days,
    )
    by_exchange = {str(status["exchange"]): status for status in statuses}
    assert set(by_exchange) == {"BSE", "NSE"}
    assert all(status["status"] == "invalid_config" for status in by_exchange.values())


def test_manual_review_open_listing_marks_sla_breach(tmp_path: Path) -> None:
    db_path = tmp_path / "review_sla.db"
    settings.db_url = f"sqlite:///{db_path}"
    init_db()
    with get_session() as session:
        session.execute(delete(ManualReviewQueue))
        session.add(
            ManualReviewQueue(
                category="CORPORATE_ACTION_FALSE_NEGATIVE_RISK",
                isin="INESLA000001",
                event_date=date(2026, 4, 10),
                reason="Potential unmatched nearby event",
                payload={
                    "sla_due_date": "2026-04-10",
                    "sla_business_days": 1,
                    "sla_exchange": "NSE",
                    "triage_instructions": "Triage within one business day.",
                },
                resolved=False,
            )
        )

    headers = {"x-api-key": settings.api_key}
    with TestClient(app) as client:
        response = client.get("/reviews/open", headers=headers)
        assert response.status_code == 200
        review = response.json()[0]
        assert review["payload"]["sla_status"] == "OVERDUE"
        assert review["payload"]["sla_breached"] is True
        assert review["payload"]["escalation_status"] == "ESCALATED"
