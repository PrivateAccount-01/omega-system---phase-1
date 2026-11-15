from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, date, datetime
from pathlib import Path

import httpx

from omegadata.config import settings
from omegadata.db.models import (
    ContinuousFutureDaily,
    FuturesContractMaster,
    FuturesEOD,
    OptionsContractMaster,
    OptionsEOD,
)
from omegadata.db.session import get_session, init_db
from omegadata.pipelines.sequential_pipeline import OmegaDataSequentialPipeline
from omegadata.track_a.acquisition import failure
from omegadata.track_a.source_registry import resolve_era
from omegadata.track_a.source_rights import (
    PolicyRequest,
    SourceOperation,
    SourceTransport,
    authorize_source,
    policy_url_host,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _relative_repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except Exception:  # noqa: BLE001
        return path.as_posix()


def _render_fo_url(as_of: date) -> str:
    era = resolve_era("NSE_FO_BHAVCOPY", as_of)
    return (
        era.url_pattern.replace("{YYYY}", f"{as_of.year:04d}")
        .replace("{MM}", f"{as_of.month:02d}")
        .replace("{DD}", f"{as_of.day:02d}")
        .replace("{YYYYMMDD}", as_of.strftime("%Y%m%d"))
        .replace("{DDMONYYYY}", as_of.strftime("%d%b%Y").upper())
        .replace("{MON}", as_of.strftime("%b").upper())
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Load official NSE F&O bhavcopy into the canonical pipeline DB.")
    parser.add_argument("--db-url", default=None, help="Database URL override")
    parser.add_argument("--trade-date", required=True, help="Trade date in YYYY-MM-DD")
    parser.add_argument(
        "--artifact-path",
        default="artifacts/verification/nse_fo_load_report.json",
        help="Output report path",
    )
    args = parser.parse_args()

    trade_date = date.fromisoformat(args.trade_date)
    url = _render_fo_url(trade_date)
    def preflight(operation: SourceOperation):
        return authorize_source(PolicyRequest(
            source_key="NSE_FO_BHAVCOPY", operation=operation,
            decision_at=datetime.now(UTC), requested_transport=SourceTransport.HTTPX,
            requested_host=policy_url_host(url),
        ))

    decisions = [preflight(operation) for operation in (SourceOperation.FETCH, SourceOperation.STORE_RAW)]
    if args.db_url:
        settings.db_url = str(args.db_url)
    init_db()

    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.nseindia.com/all-reports-derivatives"}
    decisions[0] = preflight(SourceOperation.FETCH)
    # Connection-time egress control and FO structural validation are not certified.
    # Never let this independent legacy loader bypass the offline acquisition gate.
    raise failure("BLOCKED_EXTERNAL_EGRESS")
    response = httpx.get(url, headers=headers, timeout=60.0, follow_redirects=False)
    response.raise_for_status()
    payload = response.content
    decisions[1] = preflight(SourceOperation.STORE_RAW)

    out_dir = REPO_ROOT / "data/raw/nse_fo_bhavcopy" / f"year={trade_date.year:04d}" / f"month={trade_date.month:02d}"
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = out_dir / f"{trade_date.strftime('%Y%m%d')}.zip"
    artifact_path.write_bytes(payload)
    checksum = hashlib.sha256(payload).hexdigest()
    manifest_path = out_dir / f"{trade_date.strftime('%Y%m%d')}.manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(UTC).isoformat(),
                "source_key": "NSE_FO_BHAVCOPY",
                "trade_date": trade_date.isoformat(),
                "used_url": url,
                "artifact_path": _relative_repo_path(artifact_path),
                "checksum": checksum,
                "policy_decisions": [decision.model_dump(mode="json") for decision in decisions],
                "bytes_downloaded": len(payload),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    pipeline = OmegaDataSequentialPipeline()
    with get_session() as session:
        loaded = pipeline._load_nse_fo(session, artifact_path, trade_date)
        futures_contracts = session.query(FuturesContractMaster).count()
        futures_eod = session.query(FuturesEOD).count()
        continuous = session.query(ContinuousFutureDaily).count()
        options_contracts = session.query(OptionsContractMaster).count()
        options_eod = session.query(OptionsEOD).count()

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "trade_date": trade_date.isoformat(),
        "used_url": url,
        "artifact_path": _relative_repo_path(artifact_path),
        "artifact_manifest_path": _relative_repo_path(manifest_path),
        "bytes_downloaded": len(payload),
        "checksum": checksum,
        "rows_loaded": loaded,
        "futures_contracts": futures_contracts,
        "futures_eod_rows": futures_eod,
        "continuous_futures_rows": continuous,
        "options_contracts": options_contracts,
        "options_eod_rows": options_eod,
    }
    out_path = REPO_ROOT / args.artifact_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
