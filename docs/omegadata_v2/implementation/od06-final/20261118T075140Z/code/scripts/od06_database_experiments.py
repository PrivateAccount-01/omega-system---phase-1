"""Anonymous disposable SQLite process experiments, never a financial fixture."""

from __future__ import annotations

import json
import os
import sys
import time
from contextlib import suppress
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from od06_experiment_contract import experiment_stage_accepted as experiment_stage_accepted

from omegadata.identity import Evidence, IdentifierClaim, Issuer, Listing, Security
from omegadata.identity_repository import PersistentRepository


def shared_contract() -> dict[str, Any]:
    return {
        "schema_version": "od06.shared-canary/v1",
        "market_data": False,
        "financial_eligible": False,
    }


def run(config: dict[str, Any]) -> int:
    import od05x_isolated_runner as boundary

    capability = boundary.assert_boundary()
    root = Path("/work/shared-db")
    assert json.loads((root / "NON_MARKET_DATABASE.json").read_bytes()) == shared_contract()
    out = Path("/work/job")
    out.mkdir()
    db = PersistentRepository(
        "sqlite+pysqlite:////work/shared-db/ledger.sqlite", disposable_root=root
    )
    e = Evidence("canary-e", "NON_MARKET_CANARY", "UNVERIFIED", "PERMITTED", "canary-review")
    c = IdentifierClaim(
        "claim-a",
        "listing-a",
        "CANARY-X",
        "TOKEN",
        "SERIES",
        date(2001, 1, 1),
        None,
        datetime(2001, 1, 1, tzinfo=UTC),
        None,
        e,
    )
    job = config["job"]
    status = "PASS"
    if job == "dbinit":
        db.append_entities(
            (Issuer("issuer-a"),),
            (Security("security-a", "issuer-a"),),
            (Listing("listing-a", "security-a", "CANARY-X"),),
        )
        db.append_identity_claim(c)
    elif job == "dbcrash":
        import omegadata.identity_repository as module

        original = db._put

        def pause(
            conn: Any, table: Any, key: str, value: Any, extra: Any, idempotent: bool = False
        ) -> bool:
            result = original(conn, table, key, value, extra, idempotent)
            if table is module.claims:
                (root / "write-ready.json").write_text(
                    json.dumps({"stage": "UNCOMMITTED_INSERT", "pid": os.getpid()})
                )
                while True:
                    time.sleep(0.02)
            return result

        db._put = pause  # type: ignore[method-assign]
        db.append_identity_correction(
            replace(
                c,
                claim_id="uncommitted",
                known_from=c.known_from + timedelta(days=1),
                supersedes_claim_id="claim-a",
            )
        )
    elif job == "dbrecover":
        assert db.get_claim_revisions("claim-a") == (c,)
        assert db.serialize_history().find("uncommitted") == -1
        assert (
            db.resolve_listing(
                "CANARY-X", "TOKEN", "SERIES", c.valid_from, c.known_from, "CANARY_ONLY"
            ).state
            == "RESOLVED"
        )
    elif job in {"dbcompete-a", "dbcompete-b"}:
        correction = replace(
            c,
            claim_id=job,
            known_from=c.known_from + timedelta(days=1),
            supersedes_claim_id="claim-a",
        )
        try:
            db.append_identity_correction(correction)
            status = "COMMITTED"
        except ValueError:
            status = "REFUSED_COMPETING_SUCCESSOR"
    elif job == "dbfinal":
        family = db.get_claim_revisions("claim-a")
        assert len(family) == 2 and family[1].claim_id in {"dbcompete-a", "dbcompete-b"}
        assert not db.validate_identity_consistency()
    else:
        raise ValueError("UNREVIEWED_DATABASE_EXPERIMENT")
    db.close()
    result = {
        "job": job,
        "exit_code": 0,
        "counts": {},
        "status": status,
        "python": sys.version,
        "boundary": capability,
        "stdout_stderr": "NON_MARKET_CANARY_SQLITE_ONLY",
        "pid": os.getpid(),
    }
    (out / "result.json").write_text(json.dumps(result, indent=2))
    return 0


def run_performance(config: dict[str, Any]) -> int:
    """Measure anonymous software operations; no financial scale claim."""
    import hashlib
    import statistics

    import od05x_isolated_runner as boundary
    from test_od06_contracts import calendar_system, system

    cap = boundary.assert_boundary()
    out = Path("/work/job")
    out.mkdir()
    _, _, base, c = system()
    assert c.known_from is not None
    url = "sqlite+pysqlite:////work/job/performance-canary.sqlite"
    db = PersistentRepository(url, disposable_root=out)
    db.append_entities(base.issuers, base.securities, base.listings)
    samples: dict[str, list[float]] = {}

    def measure(name: str, call: Any) -> Any:
        start = time.perf_counter()
        value = call()
        samples.setdefault(name, []).append(time.perf_counter() - start)
        return value

    measure("repository_insertion", lambda: db.append_identity_claim(c))
    for i in range(128):
        claim = replace(c, claim_id=f"anonymous-{i}", symbol=f"NON_MARKET_TOKEN_{i}")
        measure("repository_insertion", lambda claim=claim: db.append_identity_claim(claim))
    for _ in range(40):
        measure(
            "single_identity_lookup",
            lambda: db.resolve_listing(
                "CANARY-X", "TOKEN", "SERIES", c.valid_from, c.known_from, "CANARY_ONLY"
            ),
        )
    parent = c
    for i in range(1, 33):
        child = replace(
            c,
            claim_id=f"revision-{i}",
            known_from=c.known_from + timedelta(days=i),
            supersedes_claim_id=parent.claim_id,
        )
        measure("correction_append", lambda child=child: db.append_identity_correction(child))
        parent = child
    for _ in range(40):
        measure(
            "historical_lookup",
            lambda: db.resolve_listing(
                "CANARY-X", "TOKEN", "SERIES", c.valid_from, c.known_from, "CANARY_ONLY"
            ),
        )
        measure("large_history_lookup", lambda: db.get_claim_revisions(parent.claim_id))
    _, session, _ = calendar_system()
    db.append_session(session)
    for _ in range(40):
        measure(
            "calendar_query",
            lambda: db.calendar().query(
                "CANARY-X", session.session_date, c.known_from, "CANARY_ONLY"
            ),
        )
    before = db.serialize_history()

    def rollback() -> None:
        with suppress(RuntimeError):
            db.append_identity_correction(
                replace(
                    c,
                    claim_id="interrupted",
                    known_from=parent.known_from + timedelta(days=1),
                    supersedes_claim_id=parent.claim_id,
                ),
                _interrupt_after_insert=True,
            )
        assert before == db.serialize_history()

    measure("transaction_rollback", rollback)
    db.close()
    start = time.perf_counter()
    db = PersistentRepository(url, disposable_root=out)
    assert db.serialize_history() == before
    samples["restart_recovery"] = [time.perf_counter() - start]
    with db.engine.connect() as connection:
        plan = connection.exec_driver_sql(
            "EXPLAIN QUERY PLAN SELECT id FROM od06_claim WHERE exchange='CANARY-X' AND symbol='TOKEN' AND series='SERIES' AND valid_from<='2001-01-01'"
        ).fetchall()
    db.close()
    result = {
        "job": "foundationperf",
        "exit_code": 0,
        "counts": {},
        "python": sys.version,
        "boundary": cap,
        "stdout_stderr": "NON_MARKET_CANARY_ONLY",
        "anonymous_claims": 161,
        "revision_depth": 33,
        "query_plan": [str(row) for row in plan],
        "timings": {
            name: {
                "samples": len(values),
                "median_seconds": statistics.median(values),
                "max_seconds": max(values),
                "p95_seconds": sorted(values)[max(0, int(len(values) * 0.95) - 1)],
            }
            for name, values in samples.items()
        },
        "history_sha256": hashlib.sha256(before.encode()).hexdigest(),
        "limitation": "Small anonymous control corpus, not realistic market scale; append validates complete ledger O(n); indexed lookup loads candidate listing histories only.",
    }
    (out / "result.json").write_text(json.dumps(result, indent=2))
    return 0
