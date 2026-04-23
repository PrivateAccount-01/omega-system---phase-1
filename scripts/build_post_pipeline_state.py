from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = REPO_ROOT / "artifacts/verification/pipeline_run_work.sqlite"
OUTPUT_PATH = REPO_ROOT / "artifacts/verification/post_pipeline_state.json"


def _count(cursor: sqlite3.Cursor, sql: str, params: tuple[object, ...] = ()) -> int:
    row = cursor.execute(sql, params).fetchone()
    return int(row[0] or 0) if row else 0


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    sample_isins = [
        row[0]
        for row in cur.execute(
            "select distinct isin from price_record where exchange='NSE' order by isin limit 5"
        ).fetchall()
    ]
    latest_trade_date = cur.execute(
        "select max(trade_date) from price_record where exchange='NSE'"
    ).fetchone()[0]
    artifact = {
        "captured_at": datetime.now(UTC).isoformat(),
        "db": {
            "counts": {
                "price_records": _count(cur, "select count(*) from price_record"),
                "confirmed_corporate_actions": _count(cur, "select count(*) from confirmed_corporate_action"),
                "future_confirmed_corporate_actions": _count(
                    cur,
                    "select count(*) from confirmed_corporate_action where ex_date > ?",
                    (latest_trade_date,),
                )
                if latest_trade_date
                else 0,
                "discontinuity_events": _count(cur, "select count(*) from discontinuity_event"),
                "validation_logs": _count(cur, "select count(*) from validation_audit_log"),
                "adjusted_price_rows": _count(
                    cur,
                    "select count(*) from price_record where adjusted_close_price is not null",
                ),
            },
            "latest_trade_date": latest_trade_date,
            "sample_isins": sample_isins,
        },
        "note": (
            "This replaces the stale early-April post-pipeline snapshot with the current canonical verification DB state. "
            "Future-dated confirmed corporate actions are tracked explicitly so the current pipeline state remains truthful."
        ),
    }
    OUTPUT_PATH.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
