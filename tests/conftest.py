from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from omegadata.db.base import Base


@pytest.fixture()
def synthetic_source_policy_provider():
    """Explicit SYNTHETIC_TEST_ONLY permission, never installed as runtime policy."""
    from datetime import UTC, datetime
    from urllib.parse import urlsplit

    from omegadata.track_a.source_registry import SOURCE_REGISTRY
    from omegadata.track_a.source_rights import (
        SourceOperation,
        SourcePolicy,
        SourcePolicyRegister,
        SourceTransport,
    )

    policies = []
    for key, source in SOURCE_REGISTRY.items():
        hosts = {urlsplit(era.url_pattern).hostname for era in source.eras}
        hosts.update(urlsplit(url).hostname for url in source.failover_url_patterns)
        hosts.update({"www.nseindia.com", "example.invalid"})
        policy = SourcePolicy(
            schema_version="source-policy/v1",
            source_key=key,
            policy_id="SYNTHETIC_TEST_ONLY-" + key,
            policy_revision=1,
            status="APPROVED",
            created_at=datetime(2020, 1, 1, tzinfo=UTC),
            change_reason="SYNTHETIC_TEST_ONLY: mock transports only",
            revision_hash="0" * 64,
            source_entity="SYNTHETIC_TEST_ONLY",
            source_terms_url="https://example.invalid/terms",
            terms_sha256="a" * 64,
            terms_retrieved_at=datetime(2020, 1, 1, tzinfo=UTC),
            approval_evidence_ref="SYNTHETIC_TEST_ONLY/mock-permission",
            approved_by="SYNTHETIC_TEST_ONLY",
            approved_at=datetime(2020, 1, 1, tzinfo=UTC),
            valid_from=datetime(2020, 1, 1, tzinfo=UTC),
            valid_until=datetime(2100, 1, 1, tzinfo=UTC),
            permitted_operations=tuple(SourceOperation),
            permitted_transports=tuple(t for t in SourceTransport if t != SourceTransport.BROWSER),
            allowed_hosts=tuple(sorted(h for h in hosts if h)),
        )
        policies.append(policy.model_copy(update={"revision_hash": policy.canonical_hash()}))
    register = SourcePolicyRegister(schema_version="source-policy/v1", policies=tuple(policies))
    return lambda: register


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
