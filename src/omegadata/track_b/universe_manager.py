from __future__ import annotations

import csv
import io
import json
import zipfile
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd
from sqlalchemy import and_, delete, or_, select
from sqlalchemy.orm import Session

from omegadata.db.models import InstrumentMaster, SymbolMap, UniverseMembership
from omegadata.domain import Exchange, InstrumentType
from omegadata.track_b.isin_master import ISINMasterService


@dataclass(frozen=True)
class UniverseEntry:
    isin: str
    index_name: str
    effective_date: date
    source: str
    source_confidence: Decimal


@dataclass(frozen=True)
class UniverseValidationResult:
    index_name: str
    as_of_date: date
    expected_isins: list[str]
    actual_isins: list[str]
    matched: bool
    source: str
    errors: list[str]


class PointInTimeUniverseManager:
    def add_membership(
        self,
        session: Session,
        isin: str,
        index_name: str,
        added_date: date,
        effective_date: date,
        source: str,
        source_confidence: Decimal = Decimal("1.00"),
        removed_date: date | None = None,
        removal_effective: date | None = None,
    ) -> UniverseMembership:
        row = UniverseMembership(
            isin=isin,
            index_name=index_name,
            added_date=added_date,
            effective_date=effective_date,
            removed_date=removed_date,
            removal_effective=removal_effective,
            source=source,
            source_confidence=source_confidence,
        )
        session.add(row)
        return row

    def get_universe(self, session: Session, index_name: str, as_of_date: date) -> list[UniverseEntry]:
        rows = session.scalars(
            select(UniverseMembership)
            .where(UniverseMembership.index_name == index_name)
            .where(UniverseMembership.effective_date <= as_of_date)
            .where(
                or_(
                    UniverseMembership.removal_effective.is_(None),
                    UniverseMembership.removal_effective > as_of_date,
                )
            )
        ).all()

        entries: list[UniverseEntry] = []
        for row in rows:
            master = session.get(InstrumentMaster, row.isin)
            if master is None:
                continue
            if master.delisted_date is not None and as_of_date > master.delisted_date:
                continue
            entries.append(
                UniverseEntry(
                    isin=row.isin,
                    index_name=row.index_name,
                    effective_date=row.effective_date,
                    source=row.source,
                    source_confidence=Decimal(str(row.source_confidence)),
                )
            )
        return entries

    def get_upcoming_additions(
        self,
        session: Session,
        index_name: str,
        as_of_date: date,
        horizon_days: int = 30,
    ) -> list[UniverseEntry]:
        horizon = date.fromordinal(as_of_date.toordinal() + horizon_days)
        rows = session.scalars(
            select(UniverseMembership)
            .where(UniverseMembership.index_name == index_name)
            .where(UniverseMembership.added_date <= as_of_date)
            .where(UniverseMembership.effective_date > as_of_date)
            .where(UniverseMembership.effective_date <= horizon)
        ).all()
        return [
            UniverseEntry(
                isin=row.isin,
                index_name=row.index_name,
                effective_date=row.effective_date,
                source=row.source,
                source_confidence=Decimal(str(row.source_confidence)),
            )
            for row in rows
        ]

    def reconstruct_pre2010(
        self,
        session: Session,
        index_name: str,
        as_of_date: date,
        bhavcopy_universe: pd.DataFrame,
        min_avg_volume: float,
        top_n: int,
    ) -> list[UniverseMembership]:
        required_cols = {"isin", "market_cap", "avg_20d_volume", "trade_date"}
        missing = required_cols - set(bhavcopy_universe.columns)
        if missing:
            raise ValueError(f"Missing reconstruction columns: {sorted(missing)}")

        filtered = bhavcopy_universe.loc[
            (bhavcopy_universe["trade_date"] <= pd.Timestamp(as_of_date))
            & (bhavcopy_universe["avg_20d_volume"] >= min_avg_volume)
        ]
        selected = filtered.sort_values("market_cap", ascending=False).head(top_n)

        rows: list[UniverseMembership] = []
        for isin in selected["isin"].astype(str).tolist():
            row = UniverseMembership(
                isin=isin,
                index_name=index_name,
                added_date=as_of_date,
                effective_date=as_of_date,
                removed_date=None,
                removal_effective=None,
                source="RECONSTRUCTED",
                source_confidence=Decimal("0.70"),
            )
            session.add(row)
            rows.append(row)
        return rows

    def remove_membership(
        self,
        session: Session,
        isin: str,
        index_name: str,
        removed_date: date,
        removal_effective: date,
    ) -> None:
        row = session.scalar(
            select(UniverseMembership)
            .where(
                and_(
                    UniverseMembership.isin == isin,
                    UniverseMembership.index_name == index_name,
                    UniverseMembership.removal_effective.is_(None),
                )
            )
            .order_by(UniverseMembership.effective_date.desc())
        )
        if row is None:
            raise LookupError(f"No active membership row for {isin}/{index_name}")
        row.removed_date = removed_date
        row.removal_effective = removal_effective

    @staticmethod
    def _coerce_seed_pack(seed_pack: dict[str, object] | str | Path) -> dict[str, object]:
        if isinstance(seed_pack, dict):
            return seed_pack
        path = Path(seed_pack)
        return dict(json.loads(path.read_text(encoding="utf-8")))

    @staticmethod
    def _snapshot_symbols(snapshot: dict[str, object]) -> list[str]:
        constituents = snapshot.get("constituents", [])
        if not isinstance(constituents, list):
            return []
        return sorted(
            {
                str(item.get("symbol", "")).strip().upper()
                for item in constituents
                if isinstance(item, dict) and str(item.get("symbol", "")).strip()
            }
        )

    @staticmethod
    def _scan_symbol_isin_map(raw_root: Path) -> dict[str, str]:
        symbol_to_isin: dict[str, str] = {}
        bhavcopy_root = raw_root / "nse_equity_bhavcopy"
        if not bhavcopy_root.exists():
            return symbol_to_isin

        for path in sorted(bhavcopy_root.glob("year=*/month=*/*.zip")):
            with zipfile.ZipFile(path) as zf:
                names = [name for name in zf.namelist() if name.lower().endswith(".csv")]
                if not names:
                    continue
                with zf.open(names[0]) as handle:
                    reader = csv.DictReader(io.TextIOWrapper(handle, encoding="utf-8"))
                    for row in reader:
                        symbol = str(row.get("SYMBOL") or row.get("TckrSymb") or "").strip().upper()
                        isin = str(row.get("ISIN") or row.get("ISIN_NUMBER") or "").strip().upper()
                        if symbol and isin:
                            symbol_to_isin[symbol] = isin
        return symbol_to_isin

    @staticmethod
    def _seed_symbol_map(seed_pack: dict[str, object], raw_root: Path) -> dict[str, str]:
        symbol_to_isin = PointInTimeUniverseManager._scan_symbol_isin_map(raw_root)
        overrides = seed_pack.get("symbol_isin_overrides", {})
        if isinstance(overrides, dict):
            for symbol, isin in overrides.items():
                symbol_to_isin[str(symbol).upper()] = str(isin).upper()
        return symbol_to_isin

    @staticmethod
    def _seed_security_map(seed_pack: dict[str, object]) -> dict[str, dict[str, str]]:
        records = seed_pack.get("security_master", [])
        if not isinstance(records, list):
            return {}
        out: dict[str, dict[str, str]] = {}
        for item in records:
            if not isinstance(item, dict):
                continue
            symbol = str(item.get("symbol", "")).strip().upper()
            company_name = str(item.get("company_name", "")).strip()
            if symbol and company_name:
                out[symbol] = {"company_name": company_name}
        return out

    @staticmethod
    def _ensure_instrument(
        session: Session,
        *,
        isin: str,
        symbol: str,
        company_name: str,
        listed_date: date,
    ) -> None:
        svc = ISINMasterService()
        master = session.get(InstrumentMaster, isin)
        if master is None:
            svc.create_instrument(
                session=session,
                isin=isin,
                company_name=company_name,
                instrument_type=InstrumentType.EQUITY,
                primary_exchange=Exchange.NSE,
                listed_date=listed_date,
                symbol=symbol,
            )
            return

        if master.listed_date is None or listed_date < master.listed_date:
            master.listed_date = listed_date
        if not master.company_name:
            master.company_name = company_name

        mapping = session.scalar(
            select(SymbolMap)
            .where(SymbolMap.isin == isin)
            .where(SymbolMap.exchange == Exchange.NSE)
            .where(SymbolMap.symbol == symbol)
            .where(SymbolMap.valid_to.is_(None))
        )
        if mapping is None:
            session.add(
                SymbolMap(
                    isin=isin,
                    exchange=Exchange.NSE,
                    symbol=symbol,
                    valid_from=listed_date,
                    valid_to=None,
                )
            )

    def backfill_from_seed_pack(
        self,
        session: Session,
        seed_pack: dict[str, object] | str | Path,
        *,
        raw_root: str | Path = "data/raw",
    ) -> int:
        pack = self._coerce_seed_pack(seed_pack)
        snapshots = pack.get("snapshots", [])
        if not isinstance(snapshots, list) or not snapshots:
            raise ValueError("Universe seed pack must contain non-empty snapshots")

        raw_path = Path(raw_root)
        symbol_to_isin = self._seed_symbol_map(pack, raw_path)
        security_master = self._seed_security_map(pack)
        validation = self.validate_seed_pack(
            session,
            pack,
            raw_root=raw_path,
            preview_only=True,
        )
        validation_errors = [error for result in validation for error in result.errors]
        if validation_errors:
            raise ValueError(
                "Universe seed pack validation failed before applying destructive changes: "
                + "; ".join(validation_errors)
            )

        index_names = sorted(
            {
                str(snapshot.get("index_name", "")).strip()
                for snapshot in snapshots
                if isinstance(snapshot, dict) and str(snapshot.get("index_name", "")).strip()
            }
        )
        if not index_names:
            raise ValueError("Universe seed pack does not contain any index_name values")

        session.execute(delete(UniverseMembership).where(UniverseMembership.index_name.in_(index_names)))
        session.flush()

        loaded = 0
        previous_symbols: dict[str, set[str]] = {}
        ordered_snapshots = sorted(
            (snapshot for snapshot in snapshots if isinstance(snapshot, dict)),
            key=lambda snapshot: (
                str(snapshot.get("index_name", "")),
                str(snapshot.get("effective_date", "")),
            ),
        )

        for snapshot in ordered_snapshots:
            index_name = str(snapshot["index_name"]).strip()
            effective_date = date.fromisoformat(str(snapshot["effective_date"]))
            added_date = date.fromisoformat(str(snapshot.get("announcement_date") or snapshot["effective_date"]))
            source = str(snapshot.get("source", "SEED_PACK")).strip() or "SEED_PACK"
            confidence = Decimal(str(snapshot.get("source_confidence", "1.00")))

            constituents = snapshot.get("constituents", [])
            if not isinstance(constituents, list):
                raise ValueError(f"Snapshot for {index_name} on {effective_date.isoformat()} is malformed")

            current_symbols = {
                str(item.get("symbol", "")).strip().upper()
                for item in constituents
                if isinstance(item, dict) and str(item.get("symbol", "")).strip()
            }
            previous = previous_symbols.get(index_name, set())

            for symbol in sorted(previous - current_symbols):
                isin = symbol_to_isin.get(symbol)
                if not isin:
                    raise LookupError(f"No ISIN mapping available for removed symbol {symbol}")
                self.remove_membership(
                    session=session,
                    isin=isin,
                    index_name=index_name,
                    removed_date=added_date,
                    removal_effective=effective_date,
                )
            session.flush()

            current_by_symbol = {
                str(item.get("symbol", "")).strip().upper(): item
                for item in constituents
                if isinstance(item, dict) and str(item.get("symbol", "")).strip()
            }
            for symbol in sorted(current_symbols - previous):
                isin = symbol_to_isin.get(symbol)
                if not isin:
                    raise LookupError(f"No ISIN mapping available for added symbol {symbol}")
                item = current_by_symbol[symbol]
                company_name = str(
                    item.get("company_name")
                    or security_master.get(symbol, {}).get("company_name")
                    or symbol
                ).strip()
                self._ensure_instrument(
                    session,
                    isin=isin,
                    symbol=symbol,
                    company_name=company_name,
                    listed_date=added_date,
                )
                self.add_membership(
                    session=session,
                    isin=isin,
                    index_name=index_name,
                    added_date=added_date,
                    effective_date=effective_date,
                    source=source,
                    source_confidence=confidence,
                )
                loaded += 1
            session.flush()

            previous_symbols[index_name] = current_symbols

        session.flush()
        return loaded

    def validate_seed_pack(
        self,
        session: Session,
        seed_pack: dict[str, object] | str | Path,
        *,
        raw_root: str | Path = "data/raw",
        preview_only: bool = False,
    ) -> list[UniverseValidationResult]:
        pack = self._coerce_seed_pack(seed_pack)
        raw_path = Path(raw_root)
        symbol_to_isin = self._seed_symbol_map(pack, raw_path)
        results: list[UniverseValidationResult] = []

        snapshots = pack.get("snapshots", [])
        if not isinstance(snapshots, list):
            return results

        for snapshot in snapshots:
            if not isinstance(snapshot, dict):
                continue
            index_name = str(snapshot.get("index_name", "")).strip()
            effective_date_raw = str(snapshot.get("effective_date", "")).strip()
            if not index_name or not effective_date_raw:
                continue
            as_of_date = date.fromisoformat(effective_date_raw)
            constituents = snapshot.get("constituents", [])
            if not isinstance(constituents, list):
                results.append(
                    UniverseValidationResult(
                        index_name=index_name,
                        as_of_date=as_of_date,
                        expected_isins=[],
                        actual_isins=[],
                        matched=False,
                        source=str(snapshot.get("source", "SEED_PACK")),
                        errors=[f"{index_name} {as_of_date.isoformat()} has malformed constituents payload"],
                    )
                )
                continue

            errors: list[str] = []
            expected_isins: list[str] = []
            for symbol in self._snapshot_symbols(snapshot):
                mapped_isin = symbol_to_isin.get(symbol)
                if mapped_isin is None:
                    errors.append(
                        f"{index_name} {as_of_date.isoformat()} missing symbol→ISIN mapping for {symbol}"
                    )
                    continue
                expected_isins.append(mapped_isin)
            expected_isins = sorted(set(expected_isins))
            actual_isins = (
                []
                if preview_only
                else sorted(
                    entry.isin for entry in self.get_universe(session, index_name=index_name, as_of_date=as_of_date)
                )
            )
            results.append(
                UniverseValidationResult(
                    index_name=index_name,
                    as_of_date=as_of_date,
                    expected_isins=expected_isins,
                    actual_isins=actual_isins,
                    matched=(not errors and (preview_only or expected_isins == actual_isins)),
                    source=str(snapshot.get("source", "SEED_PACK")),
                    errors=errors,
                )
            )

        return results
