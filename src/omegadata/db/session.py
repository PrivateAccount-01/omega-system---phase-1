from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from omegadata.config import settings
from omegadata.db.base import Base


def _build_engine(db_url: str) -> Engine:
    if db_url.startswith("sqlite"):
        return create_engine(db_url, future=True)
    return create_engine(
        db_url,
        future=True,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=1800,
    )


_engine: Engine | None = None
_engine_url: str | None = None
_session_local: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine, _engine_url, _session_local
    if _engine is None or _engine_url != settings.db_url:
        _engine = _build_engine(settings.db_url)
        _engine_url = settings.db_url
        _session_local = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)
    return _engine


def get_sessionmaker() -> sessionmaker[Session]:
    get_engine()
    assert _session_local is not None
    return _session_local


def init_db() -> None:
    from omegadata.db import models  # noqa: F401

    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    _reconcile_schema(engine)


def _ensure_column(engine: Engine, table_name: str, column_name: str, ddl: str) -> None:
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns(table_name)}
    if column_name in columns:
        return
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}"))


def _reconcile_schema(engine: Engine) -> None:
    inspector = inspect(engine)
    if "price_record" in inspector.get_table_names():
        _ensure_column(engine, "price_record", "adjusted_open_price", "NUMERIC(20, 6)")
        _ensure_column(engine, "price_record", "adjusted_high_price", "NUMERIC(20, 6)")
        _ensure_column(engine, "price_record", "adjusted_low_price", "NUMERIC(20, 6)")


@contextmanager
def get_session() -> Iterator[Session]:
    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
