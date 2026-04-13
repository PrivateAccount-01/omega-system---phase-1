from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

from omegadata.config import settings
from omegadata.db.models import PriceRecord
from omegadata.db.session import get_session, init_db
from omegadata.domain import Exchange
from omegadata.pipelines.sequential_pipeline import OmegaDataSequentialPipeline
from omegadata.track_b.cross_source_validation import CrossSourceValidator


def _quantile(sorted_values: list[Decimal], q: Decimal) -> Decimal | None:
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return sorted_values[0]
    idx = int((len(sorted_values) - 1) * float(q))
    return sorted_values[idx]


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


def _discover_sqlite_candidates() -> list[Path]:
    excluded_parts = {".venv", ".git", ".mypy_cache", "__pycache__", "node_modules"}
    excluded_paths = {
        Path("artifacts/verification/tolerance_calibration.sqlite").resolve(),
    }
    candidates: list[Path] = []
    for path in Path(".").rglob("*.db"):
        if any(part in excluded_parts for part in path.parts):
            continue
        if path.resolve() in excluded_paths:
            continue
        candidates.append(path)
    for path in Path(".").rglob("*.sqlite"):
        if any(part in excluded_parts for part in path.parts):
            continue
        if path.resolve() in excluded_paths:
            continue
        candidates.append(path)
    for path in Path(".").rglob("*.sqlite3"):
        if any(part in excluded_parts for part in path.parts):
            continue
        if path.resolve() in excluded_paths:
            continue
        candidates.append(path)
    return sorted(set(candidates))


def _best_sqlite_candidate() -> tuple[Path | None, dict[str, int] | None]:
    ranked: list[tuple[int, int, Path, dict[str, int]]] = []
    for path in _discover_sqlite_candidates():
        try:
            counts = _count_matches_sqlite(path)
        except Exception:
            continue
        ranked.append((counts["matched"], counts["nse"], path, counts))
    if not ranked:
        return None, None
    ranked.sort(key=lambda item: (item[0], item[1], str(item[2])), reverse=True)
    _, _, best_path, counts = ranked[0]
    return best_path, counts


def _local_bse_artifacts() -> list[tuple[date, Path]]:
    latest_files = sorted(Path("data/raw/bse_equity_bhavcopy").rglob("*.latest.json"))
    artifacts: list[tuple[date, Path]] = []
    for latest in latest_files:
        payload = json.loads(latest.read_text(encoding="utf-8"))
        as_of = date.fromisoformat(str(payload["as_of"]))
        artifact_path = Path(str(payload["artifact_path"]).replace("\\", "/"))
        if artifact_path.exists():
            artifacts.append((as_of, artifact_path))
    return artifacts


def _build_calibration_sqlite(base_db: Path) -> tuple[Path, int]:
    out_dir = Path("artifacts/verification")
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "tolerance_calibration.sqlite"
    shutil.copyfile(base_db, target)

    settings.db_url = f"sqlite:///{target.as_posix()}"
    init_db()
    pipeline = OmegaDataSequentialPipeline()
    loaded = 0
    with get_session() as session:
        for trade_date, artifact_path in _local_bse_artifacts():
            loaded += pipeline._load_bse_bhavcopy_prices(session, artifact_path, trade_date)
    return target, loaded


def _normalize_path(value: Path) -> str:
    resolved = value.resolve()
    try:
        return resolved.relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def _build_summary() -> list[dict[str, object]]:
    validator = CrossSourceValidator()
    buckets: dict[tuple[str, str, str], list[Decimal]] = defaultdict(list)

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
                    (context.liquidity_bucket, "synthetic" if synthetic_bse else "official", field)
                ].append(diff_pct)

    summary: list[dict[str, object]] = []
    for (liquidity_bucket, source_quality, field), values in sorted(buckets.items()):
        ordered = sorted(values)
        p50 = _quantile(ordered, Decimal("0.50"))
        p95 = _quantile(ordered, Decimal("0.95"))
        summary.append(
            {
                "liquidity_bucket": liquidity_bucket,
                "source_quality": source_quality,
                "field": field,
                "observation_count": len(ordered),
                "p50_diff_pct": None if p50 is None else str(p50),
                "p95_diff_pct": None if p95 is None else str(p95),
                "max_diff_pct": str(ordered[-1]),
            }
        )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url", dest="db_url", default=None)
    args = parser.parse_args()

    out_dir = Path("artifacts/verification")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "cross_source_tolerance_report.json"

    selected_db_url = settings.db_url
    source_db_description = "configured_db_url"
    enrichment: dict[str, object] | None = None

    try:
        if args.db_url:
            selected_db_url = str(args.db_url)
        else:
            best_path, best_counts = _best_sqlite_candidate()
            if best_path is not None:
                if best_counts is not None and best_counts["matched"] > 0:
                    selected_db_url = f"sqlite:///{best_path.as_posix()}"
                    source_db_description = _normalize_path(best_path)
                elif best_counts is not None and best_counts["nse"] > 0:
                    calibration_db, loaded = _build_calibration_sqlite(best_path)
                    calibration_counts = _count_matches_sqlite(calibration_db)
                    selected_db_url = f"sqlite:///{calibration_db.as_posix()}"
                    source_db_description = _normalize_path(calibration_db)
                    enrichment = {
                        "base_db": _normalize_path(best_path),
                        "bse_rows_loaded": loaded,
                        "matched_after_enrichment": calibration_counts["matched"],
                    }

        settings.db_url = selected_db_url
        init_db()
        summary = _build_summary()

        artifact: dict[str, object] = {
            "generated_at": datetime.now(UTC).isoformat(),
            "db_url": selected_db_url,
            "source_db": source_db_description,
            "status": "ok" if summary else "no_observations",
            "groups": summary,
        }
        if enrichment is not None:
            artifact["enrichment"] = enrichment
    except Exception as exc:  # noqa: BLE001
        artifact = {
            "generated_at": datetime.now(UTC).isoformat(),
            "db_url": selected_db_url,
            "source_db": source_db_description,
            "status": "db_unavailable",
            "error": str(exc),
            "groups": [],
        }

    out_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
