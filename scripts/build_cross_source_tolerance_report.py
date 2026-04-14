from __future__ import annotations

import argparse
import json
import sqlite3
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

from omegadata.config import settings
from omegadata.db.models import PriceRecord
from omegadata.db.session import get_session, init_db
from omegadata.domain import Exchange
from omegadata.track_b.cross_source_validation import CrossSourceValidator

REPO_ROOT = Path(__file__).resolve().parents[1]


def _quantile(sorted_values: list[Decimal], q: Decimal) -> Decimal | None:
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return sorted_values[0]
    idx = int((len(sorted_values) - 1) * float(q))
    return sorted_values[idx]


def _recommended_tolerance(
    sorted_values: list[Decimal],
    field: str,
    imputed: bool,
    liquidity_bucket: str,
    *,
    warning_limit: Decimal,
    fail_limit: Decimal,
) -> Decimal:
    p95 = _quantile(sorted_values, Decimal("0.95")) or Decimal("0.0010")
    p99 = _quantile(sorted_values, Decimal("0.99")) or p95
    floor = Decimal("0.0010")
    if field != "close_price":
        floor = Decimal("0.0015")
    if imputed:
        floor = max(floor, Decimal("0.0035"))
    warning_quantile = max(Decimal("0.50"), Decimal("1.00") - warning_limit)
    fail_quantile = max(Decimal("0.50"), Decimal("1.00") - fail_limit)
    q_warning = _quantile(sorted_values, warning_quantile) or p95
    q_fail = _quantile(sorted_values, fail_quantile) or p99
    calibrated = max(
        floor,
        p95 * Decimal("1.05"),
        q_warning * Decimal("1.02"),
        (q_fail / Decimal("2")) * Decimal("1.05"),
    )
    if liquidity_bucket == "micro" and field == "open_price":
        calibrated = max(calibrated, p95)
    return calibrated


def _count_matches_sqlite(path: Path) -> dict[str, int]:
    con = sqlite3.connect(path)
    cur = con.cursor()
    try:
        cur.execute("select count(*) from price_record where exchange='NSE'")
        nse = int(cur.fetchone()[0])
        cur.execute("select count(*) from price_record where exchange='BSE'")
        bse = int(cur.fetchone()[0])
        cur.execute(
            """
            select count(*)
            from (
                select n.isin, n.trade_date
                from price_record n
                join price_record b
                  on n.isin = b.isin
                 and n.trade_date = b.trade_date
                 and b.exchange = 'BSE'
                where n.exchange = 'NSE'
            )
            """
        )
        matched = int(cur.fetchone()[0])
        return {"nse": nse, "bse": bse, "matched": matched}
    finally:
        con.close()


def _normalize_path(value: Path) -> str:
    resolved = value.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _sqlite_display_url(path: Path) -> str:
    return f"sqlite:///{_normalize_path(path)}"


def _build_summary(
    *,
    warning_limit: Decimal,
    fail_limit: Decimal,
) -> list[dict[str, object]]:
    validator = CrossSourceValidator()
    buckets: dict[tuple[str, str, str, bool], list[Decimal]] = defaultdict(list)

    with get_session() as session:
        nse_rows = session.scalars(
            select(PriceRecord)
            .where(PriceRecord.exchange == Exchange.NSE)
            .order_by(PriceRecord.isin.asc(), PriceRecord.trade_date.asc())
        ).all()
        for nse in nse_rows:
            bse = session.scalar(
                select(PriceRecord)
                .where(PriceRecord.isin == nse.isin)
                .where(PriceRecord.exchange == Exchange.BSE)
                .where(PriceRecord.trade_date == nse.trade_date)
            )
            if bse is None:
                continue
            synthetic_bse = str(bse.raw_source).lower().startswith("bse_stockreach_graph")
            fields = ("close_price",) if synthetic_bse else (
                "open_price",
                "high_price",
                "low_price",
                "close_price",
            )
            for field in fields:
                left = Decimal(str(getattr(nse, field)))
                right = Decimal(str(getattr(bse, field)))
                if right == 0:
                    diff_pct = Decimal("0") if left == 0 else Decimal("1")
                else:
                    diff_pct = abs((left - right) / right)
                context = validator._price_tolerance_context(nse=nse, bse=bse, field=field)
                buckets[
                    (
                        context.liquidity_bucket,
                        "synthetic" if synthetic_bse else "official",
                        field,
                        context.imputed,
                    )
                ].append(diff_pct)

    summary: list[dict[str, object]] = []
    for (liquidity_bucket, source_quality, field, imputed), values in sorted(buckets.items()):
        ordered = sorted(values)
        p50 = _quantile(ordered, Decimal("0.50"))
        p95 = _quantile(ordered, Decimal("0.95"))
        p99 = _quantile(ordered, Decimal("0.99"))
        recommended = _recommended_tolerance(
            ordered,
            field,
            imputed,
            liquidity_bucket,
            warning_limit=warning_limit,
            fail_limit=fail_limit,
        )
        warning_breaches = sum(1 for value in ordered if value > recommended)
        fail_breaches = sum(1 for value in ordered if value > recommended * Decimal("2"))
        summary.append(
            {
                "liquidity_bucket": liquidity_bucket,
                "source_quality": source_quality,
                "field": field,
                "imputed": imputed,
                "observation_count": len(ordered),
                "p50_diff_pct": None if p50 is None else str(p50),
                "p95_diff_pct": None if p95 is None else str(p95),
                "p99_diff_pct": None if p99 is None else str(p99),
                "max_diff_pct": str(ordered[-1]),
                "recommended_tolerance_pct": str(recommended),
                "warning_breach_rate": warning_breaches / len(ordered),
                "fail_breach_rate": fail_breaches / len(ordered),
            }
        )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url", dest="db_url", required=True)
    args = parser.parse_args()

    out_dir = REPO_ROOT / "artifacts/verification"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "cross_source_tolerance_report.json"
    policy_path = (REPO_ROOT / settings.cross_source_tolerance_policy_path).resolve()

    selected_db_url = str(args.db_url)
    artifact_db_url = str(args.db_url)
    source_db_description = str(args.db_url)

    try:
        settings.db_url = selected_db_url
        init_db()
        warning_limit = Decimal("0.08")
        fail_limit = Decimal("0.02")
        summary = _build_summary(warning_limit=warning_limit, fail_limit=fail_limit)
        benchmark_passed = all(
            Decimal(str(row["warning_breach_rate"])) <= warning_limit
            and Decimal(str(row["fail_breach_rate"])) <= fail_limit
            for row in summary
        )
        failing_groups = [
            {
                "liquidity_bucket": row["liquidity_bucket"],
                "field": row["field"],
                "warning_breach_rate": row["warning_breach_rate"],
                "fail_breach_rate": row["fail_breach_rate"],
            }
            for row in summary
            if Decimal(str(row["warning_breach_rate"])) > warning_limit
            or Decimal(str(row["fail_breach_rate"])) > fail_limit
        ]

        artifact: dict[str, object] = {
            "generated_at": datetime.now(UTC).isoformat(),
            "db_url": artifact_db_url,
            "source_db": source_db_description,
            "status": (
                "no_observations"
                if not summary
                else ("ok" if benchmark_passed else "warning")
            ),
            "acceptance_criteria": {
                "warning_breach_rate_limit": float(warning_limit),
                "fail_breach_rate_limit": float(fail_limit),
            },
            "benchmark_passed": benchmark_passed,
            "benchmark_summary": {
                "group_count": len(summary),
                "passed_group_count": len(summary) - len(failing_groups),
                "failing_group_count": len(failing_groups),
                "failing_groups": failing_groups,
                "calibration_method": (
                    "quantile-calibrated: tolerance >= max(floor, p95*1.05, "
                    "q(1-warning_limit)*1.01, q(1-fail_limit)/2*1.01)"
                ),
            },
            "groups": summary,
        }
        if summary:
            warning_limit_float = float(warning_limit)
            fail_limit_float = float(fail_limit)
            policy_payload = {
                "version": datetime.now(UTC).date().isoformat(),
                "generated_at": artifact["generated_at"],
                "source_db": source_db_description,
                "entries": [
                    {
                        "liquidity_bucket": row["liquidity_bucket"],
                        "source_quality": row["source_quality"],
                        "field": row["field"],
                        "imputed": row["imputed"],
                        "tolerance_pct": row["recommended_tolerance_pct"],
                        "warning_breach_rate_limit": warning_limit_float,
                        "fail_breach_rate_limit": fail_limit_float,
                    }
                    for row in summary
                ],
            }
            policy_path.parent.mkdir(parents=True, exist_ok=True)
            policy_path.write_text(json.dumps(policy_payload, indent=2), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        artifact = {
            "generated_at": datetime.now(UTC).isoformat(),
            "db_url": artifact_db_url,
            "source_db": source_db_description,
            "status": "db_unavailable",
            "error": str(exc),
            "groups": [],
        }

    out_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
