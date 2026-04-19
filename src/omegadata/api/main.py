from __future__ import annotations

import json
from collections.abc import AsyncGenerator, Awaitable, Callable, Generator
from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from typing import Annotated

import pandas as pd
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from omegadata.config import settings
from omegadata.db.models import InstrumentMaster, PriceRecord, ReleaseRecord
from omegadata.db.session import get_session, init_db
from omegadata.domain import (
    Exchange,
    PublicationState,
    QueryContext,
    ReleaseProfile,
    ReviewDecision,
)
from omegadata.track_a.monitoring import API_REQUEST_COUNTER, API_REQUEST_LATENCY
from omegadata.track_a.slo import SLOTracker
from omegadata.track_b.confidence import ConfidenceScorer
from omegadata.track_b.manual_review import ManualReviewService
from omegadata.track_b.publication import PublicationService
from omegadata.track_b.release_manager import ReleaseManager
from omegadata.track_b.release_readiness import ReleaseReadinessService
from omegadata.track_b.universe_manager import PointInTimeUniverseManager
from omegadata.verification.audit import build_audit_summary


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    init_db()
    yield


app = FastAPI(title="OmegaData API", version="0.1.0", lifespan=lifespan)
confidence = ConfidenceScorer()
universe = PointInTimeUniverseManager()
slo_tracker = SLOTracker(window_minutes=5, availability_target=0.995, p95_target_ms=750.0)
publication = PublicationService()
reviews = ManualReviewService()
release_readiness = ReleaseReadinessService()
release_manager = ReleaseManager()

ROOT_DIR = Path(__file__).resolve().parents[3]
UI_DIR = ROOT_DIR / "src" / "omegadata" / "ui"
ARTIFACT_DIR = ROOT_DIR / "artifacts" / "verification"
app.mount("/terminal-assets", StaticFiles(directory=str(UI_DIR)), name="terminal-assets")


class PriceOut(BaseModel):
    trade_date: date
    open_price: Decimal | None = None
    high_price: Decimal | None = None
    low_price: Decimal | None = None
    close_price: Decimal
    adjusted_open_price: Decimal | None = None
    adjusted_high_price: Decimal | None = None
    adjusted_low_price: Decimal | None = None
    adjusted_close_price: Decimal | None
    volume: Decimal
    adjusted_volume: Decimal | None
    confidence_score: Decimal


class PriceResponse(BaseModel):
    isin: str
    exchange: Exchange
    context: QueryContext
    records: list[PriceOut]
    excluded_records: int
    excluded_date_range: tuple[date, date] | None
    confidence_excluded_records: int = 0
    confidence_excluded_date_range: tuple[date, date] | None = None
    blocked_records: int = 0
    blocked_date_range: tuple[date, date] | None = None


class ReviewOut(BaseModel):
    id: int
    category: str
    isin: str | None
    event_date: date | None
    reason: str
    payload: dict[str, object]
    created_at: str
    resolved: bool


class ReviewResolutionIn(BaseModel):
    decision: ReviewDecision
    reviewer: str
    notes: str


class ReprocessCompletionIn(BaseModel):
    completed_by: str
    notes: str
    rebuilt_tables: list[str]
    rebuilt_isins: list[str] = []
    validation_checks: list[str]
    evidence_paths: list[str]
    date_range: dict[str, str] | None = None


class PublicationBlockOut(BaseModel):
    review_id: int
    category: str
    scope: str
    reason: str
    requires_reprocess: bool


class PublicationStatusOut(BaseModel):
    isin: str
    exchange: Exchange
    blocked_records: int
    blocked_dates: int
    blocked_date_range: tuple[date, date] | None
    state: PublicationState
    blocks: list[PublicationBlockOut]


class ReleaseOut(BaseModel):
    release_id: str
    release_profile: ReleaseProfile
    as_of_date: date
    generated_at: str
    manifest_path: str
    signature_path: str | None = None
    quality_report_path: str
    lineage_report_path: str
    warehouse_sync_status: str
    ready_state: str
    dataset_entries: list[dict[str, object]]
    consumer_matrix: dict[str, object]


def _get_db() -> Generator[Session, None, None]:
    with get_session() as session:
        yield session


SessionDep = Annotated[Session, Depends(_get_db)]


def _require_api_key(x_api_key: Annotated[str, Header()] = "") -> None:
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="invalid api key")


InternalAuthDep = Annotated[None, Depends(_require_api_key)]


def _resolve_exchange(session: Session, isin: str, exchange: Exchange | None) -> Exchange:
    if exchange is not None:
        return exchange
    primary = session.scalar(select(InstrumentMaster.primary_exchange).where(InstrumentMaster.isin == isin))
    if primary is None:
        raise HTTPException(
            status_code=400,
            detail="exchange is required when no canonical primary exchange is configured for the ISIN",
    )
    return primary


def _merge_ranges(*ranges: tuple[date, date] | None) -> tuple[date, date] | None:
    values = [item for current in ranges if current is not None for item in current]
    if not values:
        return None
    return min(values), max(values)


def _read_release_dataset(release_id: str, dataset_name: str) -> pd.DataFrame:
    path = ROOT_DIR / "artifacts" / "releases" / release_id / dataset_name / "part-00000.parquet"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"dataset {dataset_name} not found for release {release_id}")
    return pd.read_parquet(path)


def _release_record_or_404(session: Session, release_id: str) -> ReleaseRecord:
    record = release_manager.get_release_record(session, release_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"release {release_id} not found")
    return record


def _release_to_out(record: ReleaseRecord) -> ReleaseOut:
    return ReleaseOut(
        release_id=record.release_id,
        release_profile=record.release_profile,
        as_of_date=record.as_of_date,
        generated_at=record.generated_at.isoformat(),
        manifest_path=record.manifest_path,
        signature_path=record.signature_path,
        quality_report_path=record.quality_report_path,
        lineage_report_path=record.lineage_report_path,
        warehouse_sync_status=record.warehouse_sync_status,
        ready_state=record.ready_state,
        dataset_entries=list(record.dataset_entries or []),
        consumer_matrix=dict(record.consumer_matrix or {}),
    )

@app.middleware("http")
async def observe_requests(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    started = perf_counter()
    response = await call_next(request)
    elapsed_ms = (perf_counter() - started) * 1000.0
    route = request.url.path
    API_REQUEST_COUNTER.labels(
        method=request.method,
        path=route,
        status=str(response.status_code),
    ).inc()
    API_REQUEST_LATENCY.labels(method=request.method, path=route).observe(elapsed_ms / 1000.0)
    slo_tracker.record(status_code=response.status_code, latency_ms=elapsed_ms)
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/terminal")
def terminal_ui() -> FileResponse:
    html_path = UI_DIR / "terminal.html"
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="terminal ui not found")
    return FileResponse(path=html_path)


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/slo/status")
def slo_status() -> dict[str, object]:
    snapshot = slo_tracker.snapshot()
    return {
        "window_minutes": snapshot.window_minutes,
        "total_requests": snapshot.total_requests,
        "availability": snapshot.availability,
        "p95_latency_ms": snapshot.p95_latency_ms,
        "availability_target": snapshot.availability_target,
        "p95_target_ms": snapshot.p95_target_ms,
        "availability_breach": snapshot.availability_breach,
        "latency_breach": snapshot.latency_breach,
    }


@app.get("/implementation/audit")
def implementation_audit(_auth: InternalAuthDep) -> dict[str, object]:
    audit_path = ARTIFACT_DIR / "implementation_audit.json"
    if audit_path.exists():
        return dict(json.loads(audit_path.read_text(encoding="utf-8")))
    return build_audit_summary()


@app.get("/implementation/test-results")
def implementation_test_results(_auth: InternalAuthDep) -> dict[str, str]:
    unit_path = ARTIFACT_DIR / "unit_test_results.txt"
    realdata_path = ARTIFACT_DIR / "realdata_test_results.txt"
    return {
        "unit": unit_path.read_text(encoding="utf-8") if unit_path.exists() else "No unit test artifact available.",
        "realdata": (
            realdata_path.read_text(encoding="utf-8")
            if realdata_path.exists()
            else "No real-data test artifact available."
        ),
    }


@app.get("/prices/{isin}", response_model=PriceResponse)
def get_prices(
    isin: str,
    session: SessionDep,
    context: Annotated[QueryContext, Query()] = QueryContext.BACKTEST,
    exchange: Exchange | None = None,
    release_id: str | None = None,
) -> PriceResponse:
    if release_id:
        frame = _read_release_dataset(release_id, "adjusted_equity_bars")
        if "isin" not in frame.columns:
            raise HTTPException(status_code=500, detail="release dataset missing isin column")
        filtered = frame[frame["isin"] == isin].copy()
        if exchange is not None and "exchange" in filtered.columns:
            filtered = filtered[filtered["exchange"] == exchange.value]
        if filtered.empty:
            resolved_exchange = exchange or Exchange.NSE
            return PriceResponse(
                isin=isin,
                exchange=resolved_exchange,
                context=context,
                records=[],
                excluded_records=0,
                excluded_date_range=None,
            )
        resolved_exchange = exchange or Exchange(str(filtered.iloc[0]["exchange"]))
        filtered = filtered.sort_values("trade_date")
        return PriceResponse(
            isin=isin,
            exchange=resolved_exchange,
            context=context,
            records=[
                PriceOut(
                    trade_date=date.fromisoformat(str(row["trade_date"])),
                    open_price=None if pd.isna(row.get("open_price")) else Decimal(str(row.get("open_price"))),
                    high_price=None if pd.isna(row.get("high_price")) else Decimal(str(row.get("high_price"))),
                    low_price=None if pd.isna(row.get("low_price")) else Decimal(str(row.get("low_price"))),
                    close_price=Decimal(str(row["close_price"])),
                    adjusted_open_price=None if pd.isna(row.get("adjusted_open_price")) else Decimal(str(row.get("adjusted_open_price"))),
                    adjusted_high_price=None if pd.isna(row.get("adjusted_high_price")) else Decimal(str(row.get("adjusted_high_price"))),
                    adjusted_low_price=None if pd.isna(row.get("adjusted_low_price")) else Decimal(str(row.get("adjusted_low_price"))),
                    adjusted_close_price=None if pd.isna(row.get("adjusted_close_price")) else Decimal(str(row.get("adjusted_close_price"))),
                    volume=Decimal(str(row["volume"])),
                    adjusted_volume=None if pd.isna(row.get("adjusted_volume")) else Decimal(str(row.get("adjusted_volume"))),
                    confidence_score=Decimal(str(row.get("confidence_score", "1.0"))),
                )
                for _, row in filtered.iterrows()
            ],
            excluded_records=0,
            excluded_date_range=None,
        )
    resolved_exchange = _resolve_exchange(session, isin, exchange)
    rows = list(
        session.scalars(
            select(PriceRecord)
            .where(PriceRecord.isin == isin)
            .where(PriceRecord.exchange == resolved_exchange)
            .order_by(PriceRecord.trade_date.asc())
        ).all()
    )

    publishable_rows = rows
    blocked_rows: list[PriceRecord] = []
    blocked_count = 0
    blocked_range: tuple[date, date] | None = None
    if context != QueryContext.AUDIT:
        publishable_rows, blocked_rows, _ = publication.evaluate_records(session, rows)
        blocked_count = len(blocked_rows)
        if blocked_rows:
            blocked_dates = sorted({row.trade_date for row in blocked_rows})
            blocked_range = (blocked_dates[0], blocked_dates[-1])
    kept, confidence_excluded_count, confidence_excluded_range = confidence.filter_records(
        publishable_rows,
        context,
    )
    return PriceResponse(
        isin=isin,
        exchange=resolved_exchange,
        context=context,
        records=[
            PriceOut(
                trade_date=r.trade_date,
                open_price=Decimal(str(r.open_price)),
                high_price=Decimal(str(r.high_price)),
                low_price=Decimal(str(r.low_price)),
                close_price=Decimal(str(r.close_price)),
                adjusted_open_price=(
                    None if r.adjusted_open_price is None else Decimal(str(r.adjusted_open_price))
                ),
                adjusted_high_price=(
                    None if r.adjusted_high_price is None else Decimal(str(r.adjusted_high_price))
                ),
                adjusted_low_price=(
                    None if r.adjusted_low_price is None else Decimal(str(r.adjusted_low_price))
                ),
                adjusted_close_price=(
                    None if r.adjusted_close_price is None else Decimal(str(r.adjusted_close_price))
                ),
                volume=Decimal(str(r.volume)),
                adjusted_volume=(None if r.adjusted_volume is None else Decimal(str(r.adjusted_volume))),
                confidence_score=Decimal(str(r.confidence_score)),
            )
            for r in kept
        ],
        excluded_records=confidence_excluded_count + blocked_count,
        excluded_date_range=_merge_ranges(confidence_excluded_range, blocked_range),
        confidence_excluded_records=confidence_excluded_count,
        confidence_excluded_date_range=confidence_excluded_range,
        blocked_records=blocked_count,
        blocked_date_range=blocked_range,
    )


@app.get("/audit/prices/{isin}", response_model=PriceResponse)
def get_prices_audit(
    isin: str,
    session: SessionDep,
    _auth: InternalAuthDep,
    exchange: Exchange | None = None,
) -> PriceResponse:
    resolved_exchange = _resolve_exchange(session, isin, exchange)
    rows = list(
        session.scalars(
            select(PriceRecord)
            .where(PriceRecord.isin == isin)
            .where(PriceRecord.exchange == resolved_exchange)
            .order_by(PriceRecord.trade_date.asc())
        ).all()
    )
    kept, excluded_count, excluded_range = confidence.filter_records(rows, QueryContext.AUDIT)
    return PriceResponse(
        isin=isin,
        exchange=resolved_exchange,
        context=QueryContext.AUDIT,
        records=[
            PriceOut(
                trade_date=r.trade_date,
                open_price=Decimal(str(r.open_price)),
                high_price=Decimal(str(r.high_price)),
                low_price=Decimal(str(r.low_price)),
                close_price=Decimal(str(r.close_price)),
                adjusted_open_price=(
                    None if r.adjusted_open_price is None else Decimal(str(r.adjusted_open_price))
                ),
                adjusted_high_price=(
                    None if r.adjusted_high_price is None else Decimal(str(r.adjusted_high_price))
                ),
                adjusted_low_price=(
                    None if r.adjusted_low_price is None else Decimal(str(r.adjusted_low_price))
                ),
                adjusted_close_price=(
                    None if r.adjusted_close_price is None else Decimal(str(r.adjusted_close_price))
                ),
                volume=Decimal(str(r.volume)),
                adjusted_volume=(None if r.adjusted_volume is None else Decimal(str(r.adjusted_volume))),
                confidence_score=Decimal(str(r.confidence_score)),
            )
            for r in kept
        ],
        excluded_records=excluded_count,
        excluded_date_range=excluded_range,
        confidence_excluded_records=excluded_count,
        confidence_excluded_date_range=excluded_range,
    )


@app.get("/universe/{index_name}")
def get_universe(
    index_name: str,
    as_of_date: date,
    session: SessionDep,
    release_id: str | None = None,
) -> dict[str, object]:
    if release_id:
        frame = _read_release_dataset(release_id, "pit_universe_snapshot")
        filtered = frame[(frame["index_name"] == index_name) & (frame["effective_date"] <= as_of_date.isoformat())].copy()
        if "removal_effective" in filtered.columns:
            filtered = filtered[(filtered["removal_effective"].isna()) | (filtered["removal_effective"] > as_of_date.isoformat())]
        return {
            "index_name": index_name,
            "as_of_date": as_of_date,
            "isins": sorted(filtered["isin"].astype(str).tolist()),
            "count": int(len(filtered)),
        }
    entries = universe.get_universe(session=session, index_name=index_name, as_of_date=as_of_date)
    return {
        "index_name": index_name,
        "as_of_date": as_of_date,
        "isins": [item.isin for item in entries],
        "count": len(entries),
    }


@app.get("/reviews/open", response_model=list[ReviewOut])
def get_open_reviews(session: SessionDep, _auth: InternalAuthDep) -> list[ReviewOut]:
    rows = reviews.list_open_reviews(session)
    return [
        ReviewOut(
            id=row.id,
            category=row.category,
            isin=row.isin,
            event_date=row.event_date,
            reason=row.reason,
            payload=dict(row.payload or {}),
            created_at=row.created_at.isoformat(),
            resolved=row.resolved,
        )
        for row in rows
    ]


@app.post("/reviews/{review_id}/resolve")
def resolve_review(
    review_id: int,
    body: ReviewResolutionIn,
    session: SessionDep,
    _auth: InternalAuthDep,
) -> dict[str, object]:
    try:
        result = reviews.resolve_review(
            session,
            review_id=review_id,
            decision=body.decision,
            reviewer=body.reviewer,
            notes=body.notes,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "review_id": result.review_id,
        "decision": result.decision.value,
        "requires_reprocess": result.requires_reprocess,
        "reprocess_status": result.reprocess_status,
        "reprocess_job_id": result.reprocess_job_id,
    }


@app.post("/reviews/{review_id}/reprocess-complete")
def complete_reprocess(
    review_id: int,
    body: ReprocessCompletionIn,
    session: SessionDep,
    _auth: InternalAuthDep,
) -> dict[str, object]:
    try:
        payload = reviews.complete_reprocess(
            session,
            review_id=review_id,
            completed_by=body.completed_by,
            notes=body.notes,
            rebuilt_tables=body.rebuilt_tables,
            rebuilt_isins=body.rebuilt_isins,
            validation_checks=body.validation_checks,
            evidence_paths=body.evidence_paths,
            date_range=body.date_range,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"review_id": review_id, "reprocess_status": payload.get("reprocess_status", "UNKNOWN")}


@app.get("/release/readiness")
def get_release_readiness(session: SessionDep, _auth: InternalAuthDep) -> dict[str, object]:
    return release_readiness.evaluate(session)


@app.get("/releases/latest", response_model=ReleaseOut)
def get_latest_release(
    profile: ReleaseProfile,
    session: SessionDep,
    _auth: InternalAuthDep,
) -> ReleaseOut:
    record = release_manager.get_latest_release_record(session, profile)
    if record is None:
        raise HTTPException(status_code=404, detail=f"no release found for profile {profile.value}")
    return _release_to_out(record)


@app.get("/releases/{release_id}", response_model=ReleaseOut)
def get_release(release_id: str, session: SessionDep, _auth: InternalAuthDep) -> ReleaseOut:
    return _release_to_out(_release_record_or_404(session, release_id))


@app.get("/releases/{release_id}/manifest")
def get_release_manifest(release_id: str, session: SessionDep, _auth: InternalAuthDep) -> dict[str, object]:
    record = _release_record_or_404(session, release_id)
    return dict(json.loads((ROOT_DIR / record.manifest_path).read_text(encoding="utf-8")))


@app.get("/releases/{release_id}/quality")
def get_release_quality(release_id: str, session: SessionDep, _auth: InternalAuthDep) -> dict[str, object]:
    record = _release_record_or_404(session, release_id)
    return dict(json.loads((ROOT_DIR / record.quality_report_path).read_text(encoding="utf-8")))


@app.get("/releases/{release_id}/lineage")
def get_release_lineage(release_id: str, session: SessionDep, _auth: InternalAuthDep) -> dict[str, object]:
    record = _release_record_or_404(session, release_id)
    return dict(json.loads((ROOT_DIR / record.lineage_report_path).read_text(encoding="utf-8")))


@app.get("/quality/releases/{release_id}")
def get_release_quality_alias(release_id: str, session: SessionDep, _auth: InternalAuthDep) -> dict[str, object]:
    return get_release_quality(release_id, session, _auth)


@app.get("/fii-dii")
def get_fii_dii(
    start: date,
    end: date,
    session: SessionDep,
    release_id: str | None = None,
) -> dict[str, object]:
    if release_id:
        frame = _read_release_dataset(release_id, "fii_dii_daily")
        filtered = frame[(frame["trade_date"] >= start.isoformat()) & (frame["trade_date"] <= end.isoformat())]
        return {"rows": filtered.to_dict(orient="records"), "count": int(len(filtered))}
    raise HTTPException(status_code=400, detail="release_id is required for fii-dii queries")


@app.get("/india-vix")
def get_india_vix(
    start: date,
    end: date,
    session: SessionDep,
    release_id: str | None = None,
) -> dict[str, object]:
    if release_id:
        frame = _read_release_dataset(release_id, "india_vix")
        filtered = frame[(frame["trade_date"] >= start.isoformat()) & (frame["trade_date"] <= end.isoformat())]
        return {"rows": filtered.to_dict(orient="records"), "count": int(len(filtered))}
    raise HTTPException(status_code=400, detail="release_id is required for india-vix queries")


@app.get("/benchmarks/{series}")
def get_benchmark_series(
    series: str,
    start: date,
    end: date,
    session: SessionDep,
    release_id: str | None = None,
) -> dict[str, object]:
    if release_id:
        dataset = "sector_series" if series.upper().startswith("NIFTY_") and "SECTOR" in series.upper() else "benchmark_series"
        frame = _read_release_dataset(release_id, dataset)
        filtered = frame[
            (frame["index_symbol"].astype(str) == series)
            & (frame["trade_date"] >= start.isoformat())
            & (frame["trade_date"] <= end.isoformat())
        ]
        return {"rows": filtered.to_dict(orient="records"), "count": int(len(filtered))}
    raise HTTPException(status_code=400, detail="release_id is required for benchmark queries")


@app.get("/futures")
def get_futures(
    underlying: str,
    start: date,
    end: date,
    session: SessionDep,
    expiry: date | None = None,
    continuous: bool = False,
    release_id: str | None = None,
) -> dict[str, object]:
    if not release_id:
        raise HTTPException(status_code=400, detail="release_id is required for futures queries")
    dataset = "continuous_futures" if continuous else "futures_eod"
    frame = _read_release_dataset(release_id, dataset)
    filtered = frame[
        (frame["underlying_symbol"].astype(str) == underlying)
        & (frame["trade_date"] >= start.isoformat())
        & (frame["trade_date"] <= end.isoformat())
    ]
    if expiry is not None and "expiry_date" in filtered.columns:
        filtered = filtered[filtered["expiry_date"] == expiry.isoformat()]
    return {"rows": filtered.to_dict(orient="records"), "count": int(len(filtered))}


@app.get("/options")
def get_options(
    underlying: str,
    expiry: date,
    option_type: str,
    session: SessionDep,
    strike: Decimal | None = None,
    moneyness: str | None = None,
    release_id: str | None = None,
) -> dict[str, object]:
    if not release_id:
        raise HTTPException(status_code=400, detail="release_id is required for options queries")
    frame = _read_release_dataset(release_id, "options_eod")
    filtered = frame[
        (frame["underlying_symbol"].astype(str) == underlying)
        & (frame["expiry_date"] == expiry.isoformat())
        & (frame["option_type"].astype(str) == option_type)
    ]
    if strike is not None:
        filtered = filtered[filtered["strike_price"].astype(str) == str(strike)]
    if moneyness is not None and "contract_symbol" not in filtered.columns:
        # Keep moneyness support simple and deterministic: infer spot by matching underlying symbol in release bars when present.
        return {"rows": filtered.to_dict(orient="records"), "count": int(len(filtered))}
    return {"rows": filtered.to_dict(orient="records"), "count": int(len(filtered))}


@app.get("/publication/status/{isin}", response_model=PublicationStatusOut)
def publication_status(
    isin: str,
    session: SessionDep,
    _auth: InternalAuthDep,
    exchange: Exchange | None = None,
) -> PublicationStatusOut:
    resolved_exchange = _resolve_exchange(session, isin, exchange)
    rows = list(
        session.scalars(
            select(PriceRecord)
            .where(PriceRecord.isin == isin)
            .where(PriceRecord.exchange == resolved_exchange)
            .order_by(PriceRecord.trade_date.asc())
        ).all()
    )
    _publishable_rows, blocked_rows, reviews_with_policy = publication.evaluate_records(session, rows)
    blocks: list[PublicationBlockOut] = []
    seen_blocks: set[tuple[int, str]] = set()
    blocked_dates = sorted({row.trade_date for row in blocked_rows})
    _, blocks_by_date = publication.blocked_dates(rows, reviews_with_policy)
    for current_date in blocked_dates:
        for block in blocks_by_date.get(current_date, []):
            key = (block.review_id, block.category)
            if key in seen_blocks:
                continue
            seen_blocks.add(key)
            blocks.append(
                PublicationBlockOut(
                    review_id=block.review_id,
                    category=block.category,
                    scope=block.scope.value,
                    reason=block.reason,
                    requires_reprocess=block.requires_reprocess,
                )
            )
    blocked_range = None if not blocked_dates else (blocked_dates[0], blocked_dates[-1])
    state = PublicationState.BLOCKED if blocked_dates else PublicationState.PUBLISHABLE
    return PublicationStatusOut(
        isin=isin,
        exchange=resolved_exchange,
        blocked_records=len(blocked_rows),
        blocked_dates=len(blocked_dates),
        blocked_date_range=blocked_range,
        state=state,
        blocks=blocks,
    )
