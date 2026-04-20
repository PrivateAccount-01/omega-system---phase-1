from __future__ import annotations

import argparse
import csv
import io
import json
import statistics
import zipfile
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_ROOT = REPO_ROOT / "data/raw/nse_equity_bhavcopy"
SEED_ROOT = REPO_ROOT / "data/seed_raw/omega_phase2_repo/nse_equity_bhavcopy"
CALENDAR_PATH = REPO_ROOT / "config/trading_holidays_india.json"
OUTPUT_PATH = REPO_ROOT / "artifacts/verification/pipeline_replay_30day_proof.json"
_ARCHIVE_INDEX: dict[date, tuple[str, Path]] | None = None


def _load_calendar() -> dict[str, object]:
    return json.loads(CALENDAR_PATH.read_text(encoding="utf-8"))


def _holiday_set(payload: dict[str, object], exchange: str) -> set[str]:
    return set(payload.get("holidays", {}).get(exchange, []))


def _special_sessions(payload: dict[str, object], exchange: str) -> set[str]:
    sessions = payload.get("special_sessions", {}).get(exchange, [])
    return {str(item.get("date")) for item in sessions if isinstance(item, dict)}


def _is_trading_day(payload: dict[str, object], exchange: str, value: date) -> bool:
    iso = value.isoformat()
    if iso in _special_sessions(payload, exchange):
        return True
    if value.weekday() >= 5:
        return False
    return iso not in _holiday_set(payload, exchange)


def _iter_trading_days(start_date: date, end_date: date) -> list[date]:
    payload = _load_calendar()
    out: list[date] = []
    current = start_date
    while current <= end_date:
        if _is_trading_day(payload, "NSE", current):
            out.append(current)
        current += timedelta(days=1)
    return out


def _archive_candidates(root: Path, as_of: date) -> list[Path]:
    month_dir = root / f"year={as_of.year:04d}" / f"month={as_of.month:02d}"
    return sorted(month_dir.glob(f"{as_of:%Y%m%d}__*.zip"))


def _build_archive_index() -> dict[date, tuple[str, Path]]:
    indexed: dict[date, tuple[str, Path]] = {}
    for layer, root in (("canonical_cached", CANONICAL_ROOT), ("seed_cached", SEED_ROOT)):
        for path in sorted(root.glob("year=*/month=*/*.zip")):
            stem = path.stem.split("__")[0]
            if len(stem) != 8 or not stem.isdigit():
                continue
            as_of = date(int(stem[:4]), int(stem[4:6]), int(stem[6:8]))
            indexed.setdefault(as_of, (layer, path))
    return indexed


def _pick_archive(as_of: date) -> tuple[str | None, Path | None]:
    global _ARCHIVE_INDEX  # noqa: PLW0603
    if _ARCHIVE_INDEX is None:
        _ARCHIVE_INDEX = _build_archive_index()
    found = _ARCHIVE_INDEX.get(as_of)
    if found is None:
        return None, None
    return found


def _row_move(open_text: str, close_text: str) -> Decimal | None:
    try:
        open_price = Decimal(open_text)
        close_price = Decimal(close_text)
    except (InvalidOperation, TypeError):
        return None
    if open_price == 0:
        return None
    return abs(close_price - open_price) / open_price


def _daily_volatility_proxy(path: Path) -> tuple[bool, str | None, float | None]:
    try:
        with zipfile.ZipFile(path) as archive:
            members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
            if not members:
                return False, None, None
            member = sorted(members)[0]
            payload = archive.read(member)
        reader = csv.DictReader(io.StringIO(payload.decode("utf-8", errors="ignore")))
    except Exception:  # noqa: BLE001
        return False, None, None

    samples: list[float] = []
    for row in reader:
        normalized = {str(key).strip(): str(value).strip() for key, value in row.items()}
        open_text = normalized.get("OPEN") or normalized.get("OpnPric") or normalized.get("OPEN_PRICE")
        close_text = normalized.get("CLOSE") or normalized.get("ClsPric") or normalized.get("CLOSE_PRICE")
        if not open_text or not close_text:
            continue
        move = _row_move(open_text, close_text)
        if move is None:
            continue
        samples.append(float(move))
        if len(samples) >= 250:
            break
    if not samples:
        return True, member, None
    return True, member, statistics.median(samples)


def _find_window(trading_days: list[date], minimum_days: int, span_days: int) -> tuple[list[date], list[date]]:
    best_available: list[date] = []
    best_window: list[date] = []
    for index in range(len(trading_days)):
        window = trading_days[index : index + span_days]
        if len(window) < minimum_days:
            break
        available = [value for value in window if _pick_archive(value)[1] is not None]
        if len(available) > len(best_available):
            best_available = available
            best_window = window
    if len(best_available) < minimum_days:
        return [], []
    return best_available, best_window


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a 30+ trading day historical archive replay proof from canonical + seed NSE bhavcopy cache.")
    parser.add_argument("--start-date", default="2024-01-01")
    parser.add_argument("--end-date", default="2025-12-31")
    parser.add_argument("--minimum-days", type=int, default=30)
    parser.add_argument("--window-span-days", type=int, default=45)
    parser.add_argument("--output-path", default=str(OUTPUT_PATH))
    args = parser.parse_args()

    trading_days = _iter_trading_days(date.fromisoformat(args.start_date), date.fromisoformat(args.end_date))
    available_days, full_window = _find_window(trading_days, args.minimum_days, args.window_span_days)
    if not available_days:
        raise SystemExit("No 30+ trading day archive-backed replay window found")

    rows: list[dict[str, object]] = []
    volatility_samples: list[float] = []
    for as_of in available_days:
        layer, archive = _pick_archive(as_of)
        assert archive is not None
        valid, member, median_move = _daily_volatility_proxy(archive)
        if median_move is not None:
            volatility_samples.append(median_move)
        rows.append(
            {
                "date": as_of.isoformat(),
                "archive_layer": layer,
                "artifact_path": archive.relative_to(REPO_ROOT).as_posix(),
                "csv_member": member,
                "archive_valid": valid,
                "median_abs_open_close_move": median_move,
            }
        )

    valid_moves = [row["median_abs_open_close_move"] for row in rows if isinstance(row["median_abs_open_close_move"], float)]
    quiet_cutoff = None if not valid_moves else statistics.quantiles(valid_moves, n=4)[0]
    volatile_cutoff = None if not valid_moves else statistics.quantiles(valid_moves, n=4)[-1]
    quiet_days = 0
    volatile_days = 0
    for row in rows:
        move = row["median_abs_open_close_move"]
        if isinstance(move, float) and quiet_cutoff is not None and move <= quiet_cutoff:
            row["regime"] = "quiet"
            quiet_days += 1
        elif isinstance(move, float) and volatile_cutoff is not None and move >= volatile_cutoff:
            row["regime"] = "volatile"
            volatile_days += 1
        else:
            row["regime"] = "neutral"

    artifact = {
        "generated_at": datetime.now(UTC).isoformat(),
        "replay_mode": "historical_archive_replay",
        "range": {"start_date": full_window[0].isoformat(), "end_date": full_window[-1].isoformat()},
        "trading_day_count": len(available_days),
        "minimum_required_days": args.minimum_days,
        "window_span_days": len(full_window),
        "missing_days_within_window": len(full_window) - len(available_days),
        "all_archives_valid": all(bool(row["archive_valid"]) for row in rows),
        "canonical_cache_days": sum(1 for row in rows if row["archive_layer"] == "canonical_cached"),
        "seed_cache_days": sum(1 for row in rows if row["archive_layer"] == "seed_cached"),
        "quiet_day_count": quiet_days,
        "volatile_day_count": volatile_days,
        "note": (
            "This proof demonstrates that a 30+ trading day historical replay window is now available from immutable raw archive coverage "
            "using the canonical cache plus the separated omega_phase2_repo seed cache. It proves replayable archive breadth; "
            "it does not treat seed payloads as source-of-truth or bypass official-source validation."
        ),
        "results": rows,
    }
    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
