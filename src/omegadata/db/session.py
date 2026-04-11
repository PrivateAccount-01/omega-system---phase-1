from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import Engine, create_engine
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

    Base.metadata.create_all(bind=get_engine())


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
