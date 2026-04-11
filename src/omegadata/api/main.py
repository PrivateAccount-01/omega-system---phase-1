from __future__ import annotations

import json
from collections.abc import AsyncGenerator, Awaitable, Callable, Generator
from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from omegadata.config import settings
from omegadata.db.models import PriceRecord
from omegadata.db.session import get_session, init_db
from omegadata.domain import QueryContext
from omegadata.track_a.monitoring import API_REQUEST_COUNTER, API_REQUEST_LATENCY
from omegadata.track_a.slo import SLOTracker
from omegadata.track_b.confidence import ConfidenceScorer
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

ROOT_DIR = Path(__file__).resolve().parents[3]
UI_DIR = ROOT_DIR / "src" / "omegadata" / "ui"
ARTIFACT_DIR = ROOT_DIR / "artifacts" / "verification"
app.mount("/terminal-assets", StaticFiles(directory=str(UI_DIR)), name="terminal-assets")


class PriceOut(BaseModel):
    trade_date: date
    close_price: Decimal
    adjusted_close_price: Decimal | None
    volume: Decimal
    adjusted_volume: Decimal | None
    confidence_score: Decimal


class PriceResponse(BaseModel):
    isin: str
    context: QueryContext
    records: list[PriceOut]
    excluded_records: int
    excluded_date_range: tuple[date, date] | None


def _get_db() -> Generator[Session, None, None]:
    with get_session() as session:
        yield session


SessionDep = Annotated[Session, Depends(_get_db)]

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
def implementation_audit() -> dict[str, object]:
    audit_path = ARTIFACT_DIR / "implementation_audit.json"
    if audit_path.exists():
        return dict(json.loads(audit_path.read_text(encoding="utf-8")))
    return build_audit_summary()


@app.get("/implementation/test-results")
def implementation_test_results() -> dict[str, str]:
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
) -> PriceResponse:
    rows = list(
        session.scalars(
        select(PriceRecord)
        .where(PriceRecord.isin == isin)
        .order_by(PriceRecord.trade_date.asc())
        ).all()
    )

    kept, excluded_count, excluded_range = confidence.filter_records(rows, context)
    return PriceResponse(
        isin=isin,
        context=context,
        records=[
            PriceOut(
                trade_date=r.trade_date,
                close_price=Decimal(str(r.close_price)),
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
    )


@app.get("/audit/prices/{isin}", response_model=PriceResponse)
def get_prices_audit(
    isin: str,
    session: SessionDep,
    x_api_key: Annotated[str, Header()] = "",
) -> PriceResponse:
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="invalid api key")
    rows = list(
        session.scalars(
        select(PriceRecord)
        .where(PriceRecord.isin == isin)
        .order_by(PriceRecord.trade_date.asc())
        ).all()
    )
    kept, excluded_count, excluded_range = confidence.filter_records(rows, QueryContext.AUDIT)
    return PriceResponse(
        isin=isin,
        context=QueryContext.AUDIT,
        records=[
            PriceOut(
                trade_date=r.trade_date,
                close_price=Decimal(str(r.close_price)),
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
    )


@app.get("/universe/{index_name}")
def get_universe(
    index_name: str,
    as_of_date: date,
    session: SessionDep,
) -> dict[str, object]:
    entries = universe.get_universe(session=session, index_name=index_name, as_of_date=as_of_date)
    return {
        "index_name": index_name,
        "as_of_date": as_of_date,
        "isins": [item.isin for item in entries],
        "count": len(entries),
    }
