from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from omegadata.config import settings
from omegadata.db.models import (
    ContinuousFutureDaily,
    FuturesContractMaster,
    FuturesEOD,
    MarketIndexDaily,
    OptionsContractMaster,
    OptionsEOD,
    ParticipantFlowDaily,
    PriceRecord,
    ReleaseRecord,
    UniverseMembership,
)
from omegadata.domain import ReleaseProfile
from omegadata.track_a.warehouse import ClickHouseWarehouseSync
from omegadata.track_b.release_readiness import ReleaseReadinessService


@dataclass(frozen=True)
class ReleaseBuildResult:
    release_id: str
    profile: ReleaseProfile
    release_dir: Path
    manifest_path: Path
    signature_path: Path | None
    quality_report_path: Path
    lineage_report_path: Path
    warehouse_sync_status: str


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _relative_repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(_repo_root().resolve()).as_posix()
    except Exception:  # noqa: BLE001
        return path.as_posix()


def _load_profile_matrix() -> dict[str, Any]:
    path = (_repo_root() / settings.release_profile_matrix_path).resolve()
    if not path.exists():
        return {"profiles": {}}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {"profiles": {}}


class ReleaseManager:
    def __init__(self) -> None:
        self.release_root = (_repo_root() / settings.release_root).resolve()
        self.release_root.mkdir(parents=True, exist_ok=True)
        self.readiness = ReleaseReadinessService()
        self.warehouse = ClickHouseWarehouseSync()

    @staticmethod
    def _sha256(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _dataset_path(self, release_dir: Path, dataset_name: str) -> Path:
        path = release_dir / dataset_name / "part-00000.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _write_dataset(self, release_dir: Path, dataset_name: str, frame: pd.DataFrame) -> dict[str, Any]:
        path = self._dataset_path(release_dir, dataset_name)
        frame.to_parquet(path, index=False)
        return {
            "dataset_name": dataset_name,
            "row_count": int(len(frame)),
            "storage_path": _relative_repo_path(path),
            "checksum": self._sha256(path),
        }

    def _build_release_id(self, profile: ReleaseProfile, as_of: date) -> str:
        return f"{as_of:%Y%m%d}_{profile.value}"

    @staticmethod
    def _gpg_command() -> str:
        candidates = [
            r"C:\Windows\System32\wsl.exe",
            shutil.which("gpg"),
            shutil.which("gpg.exe"),
            r"C:\Program Files\Git\usr\bin\gpg.exe",
            r"C:\Program Files\GnuPG\bin\gpg.exe",
            r"C:\Program Files (x86)\GnuPG\bin\gpg.exe",
        ]
        for candidate in candidates:
            if candidate and Path(candidate).exists():
                return candidate
        raise FileNotFoundError("No GPG binary found on PATH or known Windows locations")

    @staticmethod
    def _to_wsl_path(path: Path) -> str:
        raw = str(path)
        drive, _, tail = raw.partition(":")
        if not tail:
            return raw.replace("\\", "/")
        normalized_tail = tail.replace("\\", "/")
        return f"/mnt/{drive.lower()}{normalized_tail}"

    def _gpg_home(self) -> Path:
        gpg_home = (_repo_root() / settings.release_gpg_home).resolve()
        gpg_home.mkdir(parents=True, exist_ok=True)
        return gpg_home

    def _gpg_args(self, *args: str, path_args: list[Path] | None = None) -> list[str]:
        gpg_cmd = self._gpg_command()
        if gpg_cmd.lower().endswith("wsl.exe"):
            command = [gpg_cmd, "gpg", "--homedir", self._to_wsl_path(self._gpg_home()), *args]
            for path in path_args or []:
                command.append(self._to_wsl_path(path))
            return command
        command = [gpg_cmd, *args]
        for path in path_args or []:
            command.append(str(path))
        return command

    def _gpg_env(self) -> dict[str, str]:
        env = dict(os.environ)
        if not self._gpg_command().lower().endswith("wsl.exe"):
            env["GNUPGHOME"] = str(self._gpg_home())
        return env

    def _ensure_gpg_key(self) -> str:
        key_id = settings.release_gpg_key_id.strip()
        if key_id:
            return key_id
        listing = subprocess.run(
            self._gpg_args("--batch", "--list-secret-keys", "--with-colons"),
            capture_output=True,
            text=True,
            check=False,
            env=self._gpg_env(),
        )
        for line in listing.stdout.splitlines():
            if line.startswith("sec:"):
                parts = line.split(":")
                if len(parts) > 4 and parts[4]:
                    return parts[4]
        subprocess.run(
            self._gpg_args(
                "--batch",
                "--yes",
                "--pinentry-mode",
                "loopback",
                "--passphrase",
                "",
                "--quick-generate-key",
                "OmegaData Release <releases@omegadata.local>",
                "default",
                "default",
                "never",
            ),
            capture_output=True,
            text=True,
            check=True,
            env=self._gpg_env(),
        )
        listing = subprocess.run(
            self._gpg_args("--batch", "--list-secret-keys", "--with-colons"),
            capture_output=True,
            text=True,
            check=True,
            env=self._gpg_env(),
        )
        for line in listing.stdout.splitlines():
            if line.startswith("sec:"):
                parts = line.split(":")
                if len(parts) > 4 and parts[4]:
                    return parts[4]
        raise RuntimeError("Unable to provision OmegaData release signing key")

    def _sign_manifest(self, manifest_path: Path) -> Path:
        signature_path = manifest_path.with_suffix(manifest_path.suffix + ".asc")
        key_id = self._ensure_gpg_key()
        output_path = (
            self._to_wsl_path(signature_path)
            if self._gpg_command().lower().endswith("wsl.exe")
            else str(signature_path)
        )
        subprocess.run(
            self._gpg_args(
                "--batch",
                "--yes",
                "--armor",
                "--local-user",
                key_id,
                "--output",
                output_path,
                "--detach-sign",
                path_args=[manifest_path],
            ),
            check=True,
            env=self._gpg_env(),
            capture_output=True,
            text=True,
        )
        return signature_path

    def verify_signature(self, manifest_path: Path, signature_path: Path) -> tuple[bool, str]:
        try:
            subprocess.run(
                self._gpg_args(
                    "--batch",
                    "--verify",
                    path_args=[signature_path, manifest_path],
                ),
                check=True,
                env=self._gpg_env(),
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            details = exc.stderr.strip() or exc.stdout.strip() or str(exc)
            return (False, details)
        except Exception as exc:  # noqa: BLE001
            return (False, str(exc))
        return (True, "signature verified")

    @staticmethod
    def _frame_from_rows(rows: list[dict[str, Any]]) -> pd.DataFrame:
        return pd.DataFrame(rows) if rows else pd.DataFrame()

    def _export_adjusted_equity(self, session: Session, as_of: date, release_dir: Path) -> dict[str, Any]:
        rows = session.execute(
            select(PriceRecord).where(PriceRecord.trade_date <= as_of).order_by(PriceRecord.trade_date.asc())
        ).scalars().all()
        payload = [
            {
                "isin": row.isin,
                "exchange": row.exchange.value,
                "trade_date": row.trade_date.isoformat(),
                "open_price": None if row.open_price is None else str(row.open_price),
                "high_price": None if row.high_price is None else str(row.high_price),
                "low_price": None if row.low_price is None else str(row.low_price),
                "close_price": None if row.close_price is None else str(row.close_price),
                "volume": None if row.volume is None else str(row.volume),
                "adjusted_open_price": None if row.adjusted_open_price is None else str(row.adjusted_open_price),
                "adjusted_high_price": None if row.adjusted_high_price is None else str(row.adjusted_high_price),
                "adjusted_low_price": None if row.adjusted_low_price is None else str(row.adjusted_low_price),
                "adjusted_close_price": None if row.adjusted_close_price is None else str(row.adjusted_close_price),
                "adjusted_volume": None if row.adjusted_volume is None else str(row.adjusted_volume),
                "adjustment_chain": row.adjustment_chain or [],
                "confidence_score": str(row.confidence_score),
            }
            for row in rows
        ]
        return self._write_dataset(release_dir, "adjusted_equity_bars", self._frame_from_rows(payload))

    def _export_universe(self, session: Session, as_of: date, release_dir: Path) -> dict[str, Any]:
        rows = session.execute(
            select(UniverseMembership)
            .where(UniverseMembership.effective_date <= as_of)
            .order_by(UniverseMembership.index_name.asc(), UniverseMembership.isin.asc())
        ).scalars().all()
        payload = [
            {
                "isin": row.isin,
                "index_name": row.index_name,
                "added_date": row.added_date.isoformat(),
                "effective_date": row.effective_date.isoformat(),
                "removed_date": None if row.removed_date is None else row.removed_date.isoformat(),
                "removal_effective": None if row.removal_effective is None else row.removal_effective.isoformat(),
                "source": row.source,
                "source_confidence": str(row.source_confidence),
            }
            for row in rows
        ]
        return self._write_dataset(release_dir, "pit_universe_snapshot", self._frame_from_rows(payload))

    def _export_participant_flows(self, session: Session, as_of: date, release_dir: Path) -> dict[str, Any]:
        rows = session.execute(
            select(ParticipantFlowDaily).where(ParticipantFlowDaily.trade_date <= as_of).order_by(ParticipantFlowDaily.trade_date.asc())
        ).scalars().all()
        payload = [
            {
                "trade_date": row.trade_date.isoformat(),
                "participant_category": row.participant_category,
                "buy_value": str(row.buy_value),
                "sell_value": str(row.sell_value),
                "net_value": str(row.net_value),
                "raw_source": row.raw_source,
                "source_artifact_path": row.source_artifact_path,
            }
            for row in rows
        ]
        return self._write_dataset(release_dir, "fii_dii_daily", self._frame_from_rows(payload))

    def _export_indices(self, session: Session, as_of: date, release_dir: Path, *, kind: str, dataset_name: str) -> dict[str, Any]:
        rows = session.execute(
            select(MarketIndexDaily)
            .where(MarketIndexDaily.trade_date <= as_of)
            .where(MarketIndexDaily.index_kind == kind)
            .order_by(MarketIndexDaily.trade_date.asc(), MarketIndexDaily.index_symbol.asc())
        ).scalars().all()
        payload = [
            {
                "trade_date": row.trade_date.isoformat(),
                "index_name": row.index_name,
                "index_symbol": row.index_symbol,
                "index_kind": row.index_kind,
                "open_price": None if row.open_price is None else str(row.open_price),
                "high_price": None if row.high_price is None else str(row.high_price),
                "low_price": None if row.low_price is None else str(row.low_price),
                "close_price": str(row.close_price),
                "previous_close": None if row.previous_close is None else str(row.previous_close),
                "change_pct": None if row.change_pct is None else str(row.change_pct),
                "raw_source": row.raw_source,
                "source_artifact_path": row.source_artifact_path,
            }
            for row in rows
        ]
        return self._write_dataset(release_dir, dataset_name, self._frame_from_rows(payload))

    def _export_futures_contracts(self, session: Session, release_dir: Path) -> dict[str, Any]:
        rows = session.execute(select(FuturesContractMaster).order_by(FuturesContractMaster.underlying_symbol.asc())).scalars().all()
        payload = [
            {
                "id": row.id,
                "exchange": row.exchange.value,
                "contract_symbol": row.contract_symbol,
                "underlying_symbol": row.underlying_symbol,
                "underlying_isin": row.underlying_isin,
                "instrument_kind": row.instrument_kind,
                "expiry_date": row.expiry_date.isoformat(),
                "lot_size": row.lot_size,
            }
            for row in rows
        ]
        return self._write_dataset(release_dir, "futures_contract_master", self._frame_from_rows(payload))

    def _export_futures_eod(self, session: Session, as_of: date, release_dir: Path) -> dict[str, Any]:
        rows = session.execute(
            select(FuturesContractMaster, FuturesEOD)
            .join(FuturesEOD, FuturesEOD.contract_id == FuturesContractMaster.id)
            .where(FuturesEOD.trade_date <= as_of)
            .order_by(FuturesEOD.trade_date.asc())
        ).all()
        payload = [
            {
                "trade_date": eod.trade_date.isoformat(),
                "contract_symbol": contract.contract_symbol,
                "underlying_symbol": contract.underlying_symbol,
                "underlying_isin": contract.underlying_isin,
                "expiry_date": contract.expiry_date.isoformat(),
                "open_price": None if eod.open_price is None else str(eod.open_price),
                "high_price": None if eod.high_price is None else str(eod.high_price),
                "low_price": None if eod.low_price is None else str(eod.low_price),
                "close_price": None if eod.close_price is None else str(eod.close_price),
                "settle_price": None if eod.settle_price is None else str(eod.settle_price),
                "volume": None if eod.volume is None else str(eod.volume),
                "open_interest": None if eod.open_interest is None else str(eod.open_interest),
                "raw_source": eod.raw_source,
                "source_artifact_path": eod.source_artifact_path,
            }
            for contract, eod in rows
        ]
        return self._write_dataset(release_dir, "futures_eod", self._frame_from_rows(payload))

    def _export_continuous_futures(self, session: Session, as_of: date, release_dir: Path) -> dict[str, Any]:
        rows = session.execute(
            select(ContinuousFutureDaily)
            .where(ContinuousFutureDaily.trade_date <= as_of)
            .order_by(ContinuousFutureDaily.trade_date.asc(), ContinuousFutureDaily.underlying_symbol.asc())
        ).scalars().all()
        payload = [
            {
                "trade_date": row.trade_date.isoformat(),
                "underlying_symbol": row.underlying_symbol,
                "underlying_isin": row.underlying_isin,
                "roll_rule": row.roll_rule,
                "contract_symbol": row.contract_symbol,
                "expiry_date": row.expiry_date.isoformat(),
                "open_price": None if row.open_price is None else str(row.open_price),
                "high_price": None if row.high_price is None else str(row.high_price),
                "low_price": None if row.low_price is None else str(row.low_price),
                "close_price": None if row.close_price is None else str(row.close_price),
                "settle_price": None if row.settle_price is None else str(row.settle_price),
                "volume": None if row.volume is None else str(row.volume),
                "open_interest": None if row.open_interest is None else str(row.open_interest),
            }
            for row in rows
        ]
        return self._write_dataset(release_dir, "continuous_futures", self._frame_from_rows(payload))

    def _export_options_contracts(self, session: Session, release_dir: Path) -> dict[str, Any]:
        rows = session.execute(select(OptionsContractMaster).order_by(OptionsContractMaster.underlying_symbol.asc())).scalars().all()
        payload = [
            {
                "id": row.id,
                "exchange": row.exchange.value,
                "contract_symbol": row.contract_symbol,
                "underlying_symbol": row.underlying_symbol,
                "underlying_isin": row.underlying_isin,
                "expiry_date": row.expiry_date.isoformat(),
                "strike_price": str(row.strike_price),
                "option_type": row.option_type,
                "lot_size": row.lot_size,
            }
            for row in rows
        ]
        return self._write_dataset(release_dir, "options_contract_master", self._frame_from_rows(payload))

    def _export_options_eod(self, session: Session, as_of: date, release_dir: Path) -> dict[str, Any]:
        rows = session.execute(
            select(OptionsContractMaster, OptionsEOD)
            .join(OptionsEOD, OptionsEOD.contract_id == OptionsContractMaster.id)
            .where(OptionsEOD.trade_date <= as_of)
            .order_by(OptionsEOD.trade_date.asc())
        ).all()
        payload = [
            {
                "trade_date": eod.trade_date.isoformat(),
                "contract_symbol": contract.contract_symbol,
                "underlying_symbol": contract.underlying_symbol,
                "underlying_isin": contract.underlying_isin,
                "expiry_date": contract.expiry_date.isoformat(),
                "strike_price": str(contract.strike_price),
                "option_type": contract.option_type,
                "open_price": None if eod.open_price is None else str(eod.open_price),
                "high_price": None if eod.high_price is None else str(eod.high_price),
                "low_price": None if eod.low_price is None else str(eod.low_price),
                "close_price": None if eod.close_price is None else str(eod.close_price),
                "settle_price": None if eod.settle_price is None else str(eod.settle_price),
                "volume": None if eod.volume is None else str(eod.volume),
                "open_interest": None if eod.open_interest is None else str(eod.open_interest),
                "raw_source": eod.raw_source,
                "source_artifact_path": eod.source_artifact_path,
            }
            for contract, eod in rows
        ]
        return self._write_dataset(release_dir, "options_eod", self._frame_from_rows(payload))

    def _build_quality_report(self, session: Session, *, as_of: date, profile: ReleaseProfile, out_path: Path) -> None:
        readiness = self.readiness.evaluate(session)
        payload = {
            "generated_at": datetime.now(UTC).isoformat(),
            "as_of_date": as_of.isoformat(),
            "release_profile": profile.value,
            "release_readiness_snapshot": readiness,
        }
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _build_lineage_report(self, session: Session, *, as_of: date, profile: ReleaseProfile, out_path: Path) -> None:
        source_artifacts: set[str] = set()
        source_artifacts.update(
            row[0]
            for row in session.execute(
                select(ParticipantFlowDaily.source_artifact_path).where(ParticipantFlowDaily.trade_date <= as_of)
            ).all()
            if row[0]
        )
        source_artifacts.update(
            row[0]
            for row in session.execute(
                select(MarketIndexDaily.source_artifact_path).where(MarketIndexDaily.trade_date <= as_of)
            ).all()
            if row[0]
        )
        payload = {
            "generated_at": datetime.now(UTC).isoformat(),
            "as_of_date": as_of.isoformat(),
            "release_profile": profile.value,
            "source_artifacts": sorted(source_artifacts),
        }
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def build_release(self, session: Session, *, as_of: date, profile: ReleaseProfile) -> ReleaseBuildResult:
        release_id = self._build_release_id(profile, as_of)
        release_dir = self.release_root / release_id
        release_dir.mkdir(parents=True, exist_ok=True)
        dataset_entries: list[dict[str, Any]] = []
        dataset_entries.append(self._export_adjusted_equity(session, as_of, release_dir))
        dataset_entries.append(self._export_universe(session, as_of, release_dir))
        if profile in {ReleaseProfile.EQUITY_PLUS_SIDEFEEDS, ReleaseProfile.FULL_DERIVATIVES}:
            dataset_entries.append(self._export_participant_flows(session, as_of, release_dir))
            dataset_entries.append(self._export_indices(session, as_of, release_dir, kind="VIX", dataset_name="india_vix"))
            dataset_entries.append(self._export_indices(session, as_of, release_dir, kind="BENCHMARK", dataset_name="benchmark_series"))
            dataset_entries.append(self._export_indices(session, as_of, release_dir, kind="SECTOR", dataset_name="sector_series"))
        if profile == ReleaseProfile.FULL_DERIVATIVES:
            dataset_entries.append(self._export_futures_contracts(session, release_dir))
            dataset_entries.append(self._export_futures_eod(session, as_of, release_dir))
            dataset_entries.append(self._export_continuous_futures(session, as_of, release_dir))
            dataset_entries.append(self._export_options_contracts(session, release_dir))
            dataset_entries.append(self._export_options_eod(session, as_of, release_dir))

        matrix = _load_profile_matrix()
        quality_report_path = release_dir / "quality_report.json"
        lineage_report_path = release_dir / "lineage_report.json"
        self._build_quality_report(session, as_of=as_of, profile=profile, out_path=quality_report_path)
        self._build_lineage_report(session, as_of=as_of, profile=profile, out_path=lineage_report_path)

        warehouse_result = self.warehouse.sync_release_manifest(
            release_id=release_id,
            release_profile=profile.value,
            as_of_date=as_of.isoformat(),
            dataset_entries=dataset_entries,
        )
        manifest = {
            "release_id": release_id,
            "release_profile": profile.value,
            "as_of_date": as_of.isoformat(),
            "generated_at": datetime.now(UTC).isoformat(),
            "manifest_path": _relative_repo_path(release_dir / "manifest.json"),
            "quality_report_path": _relative_repo_path(quality_report_path),
            "lineage_report_path": _relative_repo_path(lineage_report_path),
            "warehouse_sync_status": warehouse_result.status,
            "warehouse_sync_details": warehouse_result.details,
            "consumer_matrix": matrix.get("profiles", {}).get(profile.value, {}),
            "dataset_entries": dataset_entries,
        }
        manifest_path = release_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        signature_path = self._sign_manifest(manifest_path)

        existing = session.scalar(select(ReleaseRecord).where(ReleaseRecord.release_id == release_id))
        if existing is None:
            existing = ReleaseRecord(
                release_id=release_id,
                release_profile=profile,
                as_of_date=as_of,
                manifest_path=_relative_repo_path(manifest_path),
                signature_path=_relative_repo_path(signature_path),
                quality_report_path=_relative_repo_path(quality_report_path),
                lineage_report_path=_relative_repo_path(lineage_report_path),
                warehouse_sync_status=warehouse_result.status,
                ready_state="GENERATED",
                dataset_entries=dataset_entries,
                consumer_matrix=manifest["consumer_matrix"],
            )
            session.add(existing)
        else:
            existing.manifest_path = _relative_repo_path(manifest_path)
            existing.signature_path = _relative_repo_path(signature_path)
            existing.quality_report_path = _relative_repo_path(quality_report_path)
            existing.lineage_report_path = _relative_repo_path(lineage_report_path)
            existing.warehouse_sync_status = warehouse_result.status
            existing.dataset_entries = dataset_entries
            existing.consumer_matrix = manifest["consumer_matrix"]
        latest = self.release_root / f"latest_{profile.value}.json"
        latest.write_text(json.dumps({"release_id": release_id, "manifest_path": _relative_repo_path(manifest_path)}, indent=2), encoding="utf-8")
        return ReleaseBuildResult(
            release_id=release_id,
            profile=profile,
            release_dir=release_dir,
            manifest_path=manifest_path,
            signature_path=signature_path,
            quality_report_path=quality_report_path,
            lineage_report_path=lineage_report_path,
            warehouse_sync_status=warehouse_result.status,
        )

    def get_release_record(self, session: Session, release_id: str) -> ReleaseRecord | None:
        return session.scalar(select(ReleaseRecord).where(ReleaseRecord.release_id == release_id))

    def get_latest_release_record(self, session: Session, profile: ReleaseProfile) -> ReleaseRecord | None:
        return session.scalar(
            select(ReleaseRecord)
            .where(ReleaseRecord.release_profile == profile)
            .order_by(ReleaseRecord.generated_at.desc())
        )
