"""Bounded anonymous bookkeeping benchmark; no financial histories or market-scale claim."""

import json
import sys
import time
import tracemalloc
from dataclasses import replace
from pathlib import Path


def run(config):
    import od05x_isolated_runner as boundary

    boundary.assert_boundary()
    from test_od09_reconciliation import controls

    from omegadata.reconciliation.contracts import fingerprint
    from omegadata.reconciliation.engine import match_candidates, reconcile_context
    from omegadata.reconciliation.repository import ReconciliationRepository

    root = Path("/work/job")
    root.mkdir()
    c, x, left, right = controls()
    measurements = []
    for size in (10, 40, 100):
        rows = tuple(
            replace(
                left,
                field_name="control-field-" + str(i),
                availability=replace(left.availability, observation_id="left-" + str(i)),
            )
            for i in range(size)
        )
        counterparts = tuple(
            replace(
                right,
                field_name="control-field-" + str(i),
                availability=replace(right.availability, observation_id="right-" + str(i)),
            )
            for i in range(size)
        )
        case = replace(x, left=rows, right=counterparts, maximum_matches=size)
        tick = time.perf_counter()
        pairs = match_candidates(case)
        matching = time.perf_counter() - tick
        tracemalloc.start()
        tick = time.perf_counter()
        out = reconcile_context(case)
        elapsed = time.perf_counter() - tick
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        assert len(pairs) == len(out) == size and all(r.outcome == "UNCOMPARABLE" for r in out)
        measurements.append(
            {
                "groups": size,
                "observations": 2 * size,
                "matching_seconds": matching,
                "reconciliation_seconds": elapsed,
                "peak_traced_bytes": peak,
                "serialized_bytes": len(
                    __import__("omegadata.universe.repository", fromlist=["pack"])
                    .pack(out)
                    .encode()
                ),
                "digest": fingerprint(out),
            }
        )
    db = ReconciliationRepository(
        "sqlite:///" + str(root / "benchmark.sqlite"), disposable_root=root
    )
    tick = time.perf_counter()
    for i in range(30):
        case = replace(x, context_id="context-" + str(i))
        db.pin_comparison(case)
        db.admit_results(case.context_id, reconcile_context(case))
    insertion = time.perf_counter() - tick
    with db.transaction() as con:
        plans = con.exec_driver_sql(
            "EXPLAIN QUERY PLAN SELECT context FROM od09_input_index WHERE observation_digest=?",
            (fingerprint(left),),
        ).fetchall()
    tick = time.perf_counter()
    db.close()
    db = ReconciliationRepository(
        "sqlite:///" + str(root / "benchmark.sqlite"), disposable_root=root
    )
    replayed = db.replay("context-0")
    assert replayed
    restart = time.perf_counter() - tick
    record = {
        "job": "od09perf",
        "exit_code": 0,
        "counts": {},
        "python": sys.version,
        "interpreter": sys.executable,
        "boundary": boundary.assert_boundary(),
        "scale": "NON_MARKET_STRUCTURAL_CONTROL only",
        "measurements": measurements,
        "context_insert_and_admit_30_seconds": insertion,
        "restart_and_replay_seconds": restart,
        "query_plan": [list(r) for r in plans],
        "stdout_stderr": "No authentic financial data or exchange-scale benchmark",
        "legacy_or_operational_db_access": False,
    }
    (root / "result.json").write_text(json.dumps(record, indent=2))
    return 0
