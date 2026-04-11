from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from omegadata.db.base import Base


@pytest.fixture()
def db_session(tmp_path: Path) -> Session:
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(bind=engine)
    Local = sessionmaker(bind=engine, autoflush=True, autocommit=False)
    session = Local()
    try:
        yield session
        session.commit()
    finally:
        session.close()
        engine.dispose()
