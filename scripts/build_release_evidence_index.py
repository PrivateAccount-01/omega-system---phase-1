from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RELEASE_PROFILE = "equity_core"


def _read_json(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _load_release_record(profile: str) -> dict[str, object] | None:
    latest_path = REPO_ROOT / "artifacts" / "releases" / f"latest_{profile}.json"
    latest_payload = _read_json(latest_path)
    if latest_payload is None:
        return None
    manifest_path = REPO_ROOT / str(latest_payload["manifest_path"])
    manifest = _read_json(manifest_path)
    if manifest is None:
        return None
    release_id = str(manifest.get("release_id", latest_payload.get("release_id", ""))).strip()
    signature_path = manifest_path.with_suffix(manifest_path.suffix + ".asc")
    return {
        "release_id": release_id,
        "manifest_path": manifest_path.relative_to(REPO_ROOT).as_posix(),
        "signature_path": signature_path.relative_to(REPO_ROOT).as_posix() if signature_path.exists() else None,
        "quality_report_path": str(manifest.get("quality_report_path") or ""),
        "lineage_report_path": str(manifest.get("lineage_report_path") or ""),
        "warehouse_sync_status": str(manifest.get("warehouse_sync_status") or "UNKNOWN"),
        "generated_at": manifest.get("generated_at"),
    }


def _supporting_release_id(
    *,
    artifact_name: str,
    artifact_payload: dict[str, object] | None,
    releases: dict[str, dict[str, object] | None],
) -> str | None:
    if artifact_payload is None:
        return None
    direct = artifact_payload.get("release_id")
    if isinstance(direct, str) and direct:
        return direct
    nested = artifact_payload.get("release")
    if isinstance(nested, dict):
        nested_release_id = nested.get("release_id")
        if isinstance(nested_release_id, str) and nested_release_id:
            return nested_release_id
    profile_defaults = {
        "release_readiness_equity_core": "equity_core",
        "release_readiness_equity_plus_sidefeeds": "equity_plus_sidefeeds",
        "release_readiness_full_derivatives": "full_derivatives",
        "release_build_equity_core": "equity_core",
        "release_build_equity_plus_sidefeeds": "equity_plus_sidefeeds",
        "release_build_full_derivatives": "full_derivatives",
        "adjusted_ohlcv_proof": "equity_core",
        "corporate_action_proof": "equity_core",
        "pit_universe_proof": "equity_core",
        "sidefeed_proof": "equity_plus_sidefeeds",
        "nse_fo_load_report": "full_derivatives",
        "futures_continuation_proof": "full_derivatives",
        "options_query_proof": "full_derivatives",
    }
    profile = profile_defaults.get(artifact_name)
    if profile is None:
        return None
    record = releases.get(profile)
    if not isinstance(record, dict):
        return None
    release_id = record.get("release_id")
    return release_id if isinstance(release_id, str) else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.parse_args()

    evidence_paths = {
        "source_probe": REPO_ROOT / "artifacts/verification/source_probe_report.json",
        "pipeline_execution": REPO_ROOT / "artifacts/verification/pipeline_execution_result.json",
        "release_readiness": REPO_ROOT / "artifacts/verification/release_readiness.json",
        "release_readiness_equity_core": REPO_ROOT / "artifacts/verification/release_readiness_equity_core.json",
        "release_readiness_equity_plus_sidefeeds": REPO_ROOT / "artifacts/verification/release_readiness_equity_plus_sidefeeds.json",
        "release_readiness_full_derivatives": REPO_ROOT / "artifacts/verification/release_readiness_full_derivatives.json",
        "release_build_equity_core": REPO_ROOT / "artifacts/verification/release_build_equity_core.json",
        "release_build_equity_plus_sidefeeds": REPO_ROOT / "artifacts/verification/release_build_equity_plus_sidefeeds.json",
        "release_build_full_derivatives": REPO_ROOT / "artifacts/verification/release_build_full_derivatives.json",
        "adjusted_ohlcv_proof": REPO_ROOT / "artifacts/verification/adjusted_ohlcv_proof.json",
        "corporate_action_proof": REPO_ROOT / "artifacts/verification/corporate_action_proof.json",
        "corporate_action_corpus_coverage": REPO_ROOT / "artifacts/verification/corporate_action_corpus_coverage.json",
        "sidefeed_proof": REPO_ROOT / "artifacts/verification/sidefeed_proof.json",
        "pit_universe_proof": REPO_ROOT / "artifacts/verification/pit_universe_proof.json",
        "historical_trading_calendar_proof": REPO_ROOT / "artifacts/verification/historical_trading_calendar_proof.json",
        "cross_source_tolerance": REPO_ROOT / "artifacts/verification/cross_source_tolerance_report.json",
        "matching_report": REPO_ROOT / "artifacts/verification/corporate_action_matching_report.json",
        "discontinuity_spike_report": REPO_ROOT / "artifacts/verification/discontinuity_spike_report.json",
        "nse_historical_backfill": REPO_ROOT / "artifacts/verification/nse_historical_backfill_report.json",
        "trading_calendar_coverage": REPO_ROOT / "artifacts/verification/trading_calendar_coverage.json",
        "nse_fo_load_report": REPO_ROOT / "artifacts/verification/nse_fo_load_report.json",
        "futures_continuation_proof": REPO_ROOT / "artifacts/verification/futures_continuation_proof.json",
        "options_query_proof": REPO_ROOT / "artifacts/verification/options_query_proof.json",
        "review_backlog_reconciliation": REPO_ROOT / "artifacts/verification/review_backlog_reconciliation.json",
    }
    releases = {
        "equity_core": _load_release_record("equity_core"),
        "equity_plus_sidefeeds": _load_release_record("equity_plus_sidefeeds"),
        "full_derivatives": _load_release_record("full_derivatives"),
    }
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "default_release_profile": DEFAULT_RELEASE_PROFILE,
        "releases": releases,
        "proof_artifacts": {
            name: {
                "path": path.relative_to(REPO_ROOT).as_posix(),
                "exists": path.exists(),
                "generated_at": None if (artifact := _read_json(path)) is None else artifact.get("generated_at"),
                "supporting_release_id": _supporting_release_id(
                    artifact_name=name,
                    artifact_payload=artifact,
                    releases=releases,
                ),
            }
            for name, path in evidence_paths.items()
        },
    }
    out_path = REPO_ROOT / "artifacts/verification/release_evidence_index.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
