from __future__ import annotations

import csv
import io
import json
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from omegadata.config import settings
from omegadata.db.models import (
    ContinuousFutureDaily,
    CorporateActionStaging,
    DiscontinuityEvent,
    FuturesContractMaster,
    FuturesEOD,
    InstrumentMaster,
    MarketIndexDaily,
    OptionsContractMaster,
    OptionsEOD,
    ParticipantFlowDaily,
    PriceRecord,
    SymbolMap,
)
from omegadata.db.session import get_session
from omegadata.domain import CorporateActionType, Exchange, InstrumentType
from omegadata.track_a.collection_schedule import (
    due_corporate_action_sources,
    require_confirmation_window,
)
from omegadata.track_a.orchestration import IngestionOrchestrator
from omegadata.track_b.adjustment_engine import PriceAdjustmentEngine
from omegadata.track_b.confidence import ConfidenceInputs, ConfidenceScorer
from omegadata.track_b.corporate_action_parser import CorporateActionParser
from omegadata.track_b.corporate_actions import CorporateActionService
from omegadata.track_b.cross_source_validation import CrossSourceValidator
from omegadata.track_b.discontinuity import DiscontinuityDetector


@dataclass(frozen=True)
class PipelineSummary:
    ingest_paths: list[str]
    confirmed_actions: int
    adjusted_rows: int
    discontinuities: int
    total_discontinuity_events: int
    validations: int


class OmegaDataSequentialPipeline:
    def __init__(self) -> None:
        self.ingestor = IngestionOrchestrator()
        self.ca_service = CorporateActionService()
        self.ca_parser = CorporateActionParser()
        self.adjustment_engine = PriceAdjustmentEngine()
        self.discontinuity_detector = DiscontinuityDetector()
        self.confidence_scorer = ConfidenceScorer()
        self.validator = CrossSourceValidator()

    @staticmethod
    def _to_decimal(value: str | int | float | None) -> Decimal | None:
        return CorporateActionParser.to_decimal(value)

    @staticmethod
    def _parse_date(value: str | None) -> date | None:
        if not value:
            return None
        text = str(value).strip()
        if not text:
            return None
        patterns = (
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%d-%b-%Y",
            "%d %b %Y",
            "%Y/%m/%d",
            "%d %B %Y",
        )
        for fmt in patterns:
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(text).date()
        except ValueError:
            return None

    @staticmethod
    def _normalize_row(raw: Mapping[str, object]) -> dict[str, str]:
        out: dict[str, str] = {}
        for key, value in raw.items():
            k = str(key).strip().upper().replace(" ", "_")
            out[k] = "" if value is None else str(value).strip()
        return out

    @staticmethod
    def _ensure_identity_adjusted_fields(price_record: PriceRecord) -> None:
        """Populate adjusted fields with identity values until a real CA recompute overrides them."""
        if all(
            value is not None
            for value in (
                price_record.adjusted_open_price,
                price_record.adjusted_high_price,
                price_record.adjusted_low_price,
                price_record.adjusted_close_price,
                price_record.adjusted_volume,
            )
        ):
            return
        price_record.adjusted_open_price = price_record.open_price
        price_record.adjusted_high_price = price_record.high_price
        price_record.adjusted_low_price = price_record.low_price
        price_record.adjusted_close_price = price_record.close_price
        price_record.adjusted_volume = price_record.volume
        price_record.cumulative_price_factor = Decimal("1")
        price_record.cumulative_volume_factor = Decimal("1")
        price_record.adjustment_chain = price_record.adjustment_chain or []

    def _load_fii_dii(self, session: Session, path: Path) -> int:
        if not path.exists():
            return 0
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            return 0
        loaded = 0
        for item in payload:
            if not isinstance(item, Mapping):
                continue
            trade_date = self._parse_date(str(item.get("date", "")))
            category = str(item.get("category", "")).strip()
            buy_value = self._to_decimal(str(item.get("buyValue", "")))
            sell_value = self._to_decimal(str(item.get("sellValue", "")))
            net_value = self._to_decimal(str(item.get("netValue", "")))
            if trade_date is None or not category or None in (buy_value, sell_value, net_value):
                continue
            assert buy_value is not None
            assert sell_value is not None
            assert net_value is not None
            existing = session.scalar(
                select(ParticipantFlowDaily)
                .where(ParticipantFlowDaily.trade_date == trade_date)
                .where(ParticipantFlowDaily.participant_category == category)
            )
            if existing is None:
                existing = ParticipantFlowDaily(
                    trade_date=trade_date,
                    participant_category=category,
                    buy_value=buy_value,
                    sell_value=sell_value,
                    net_value=net_value,
                    raw_source="nse_fii_dii",
                    source_artifact_path=path.as_posix(),
                )
                session.add(existing)
            else:
                existing.buy_value = buy_value
                existing.sell_value = sell_value
                existing.net_value = net_value
                existing.source_artifact_path = path.as_posix()
            loaded += 1
        return loaded

    def _index_kind(self, row: Mapping[str, object]) -> str:
        key = str(row.get("key", "")).upper()
        symbol = str(row.get("indexSymbol", "")).upper()
        name = str(row.get("index", "")).upper()
        if "VIX" in symbol or "VIX" in name:
            return "VIX"
        if "SECTOR" in key:
            return "SECTOR"
        return "BENCHMARK"

    def _load_market_indices(self, session: Session, path: Path, as_of: date) -> int:
        if not path.exists():
            return 0
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            return 0
        rows = payload.get("data", [])
        if not isinstance(rows, list):
            return 0
        loaded = 0
        for item in rows:
            if not isinstance(item, Mapping):
                continue
            index_name = str(item.get("index", "")).strip()
            index_symbol = str(item.get("indexSymbol", index_name)).strip()
            close_price = self._to_decimal(str(item.get("last", "")))
            if not index_name or not index_symbol or close_price is None:
                continue
            open_price = self._to_decimal(str(item.get("open", "")))
            high_price = self._to_decimal(str(item.get("high", "")))
            low_price = self._to_decimal(str(item.get("low", "")))
            previous_close = self._to_decimal(str(item.get("previousClose", "")))
            change_pct = self._to_decimal(str(item.get("percentChange", "")))
            existing = session.scalar(
                select(MarketIndexDaily)
                .where(MarketIndexDaily.trade_date == as_of)
                .where(MarketIndexDaily.index_symbol == index_symbol)
            )
            if existing is None:
                existing = MarketIndexDaily(
                    trade_date=as_of,
                    index_name=index_name,
                    index_symbol=index_symbol,
                    index_kind=self._index_kind(item),
                    open_price=open_price,
                    high_price=high_price,
                    low_price=low_price,
                    close_price=close_price,
                    previous_close=previous_close,
                    change_pct=change_pct,
                    raw_source="india_vix_all_indices",
                    source_artifact_path=path.as_posix(),
                )
                session.add(existing)
            else:
                existing.index_name = index_name
                existing.index_kind = self._index_kind(item)
                existing.open_price = open_price
                existing.high_price = high_price
                existing.low_price = low_price
                existing.close_price = close_price
                existing.previous_close = previous_close
                existing.change_pct = change_pct
                existing.source_artifact_path = path.as_posix()
            loaded += 1
        return loaded

    @staticmethod
    def _canonical_contract_symbol(
        underlying_symbol: str,
        expiry_date: date,
        instrument_kind: str,
        strike_price: Decimal | None,
        option_type: str | None,
    ) -> str:
        strike_part = "" if strike_price is None else f"_{strike_price.normalize()}"
        option_part = "" if not option_type else f"_{option_type}"
        return f"{underlying_symbol}_{expiry_date.isoformat()}_{instrument_kind}{strike_part}{option_part}"

    def _lookup_underlying_isin(self, session: Session, symbol: str) -> str | None:
        normalized = symbol.strip().upper()
        if not normalized:
            return None
        row = session.scalar(
            select(SymbolMap)
            .where(SymbolMap.exchange == Exchange.NSE)
            .where(SymbolMap.symbol == normalized)
            .where(SymbolMap.valid_to.is_(None))
        )
        return None if row is None else row.isin

    def _rebuild_continuous_futures(self, session: Session, trade_date: date) -> int:
        rows = session.execute(
            select(FuturesContractMaster, FuturesEOD)
            .join(FuturesEOD, FuturesEOD.contract_id == FuturesContractMaster.id)
            .where(FuturesEOD.trade_date == trade_date)
            .order_by(FuturesContractMaster.underlying_symbol.asc(), FuturesContractMaster.expiry_date.asc())
        ).all()
        existing = session.scalars(
            select(ContinuousFutureDaily).where(ContinuousFutureDaily.trade_date == trade_date)
        ).all()
        for row in existing:
            session.delete(row)
        loaded = 0
        seen_underlyings: set[str] = set()
        for contract, eod in rows:
            if contract.underlying_symbol in seen_underlyings:
                continue
            seen_underlyings.add(contract.underlying_symbol)
            session.add(
                ContinuousFutureDaily(
                    trade_date=trade_date,
                    underlying_symbol=contract.underlying_symbol,
                    underlying_isin=contract.underlying_isin,
                    roll_rule="front_month",
                    contract_symbol=contract.contract_symbol,
                    expiry_date=contract.expiry_date,
                    open_price=eod.open_price,
                    high_price=eod.high_price,
                    low_price=eod.low_price,
                    close_price=eod.close_price,
                    settle_price=eod.settle_price,
                    volume=eod.volume,
                    open_interest=eod.open_interest,
                )
            )
            loaded += 1
        return loaded

    def _load_nse_fo(self, session: Session, path: Path, trade_date: date) -> int:
        if not path.exists():
            return 0
        payload = path.read_bytes()
        if path.suffix.lower() == ".zip":
            with zipfile.ZipFile(io.BytesIO(payload)) as zf:
                names = [name for name in zf.namelist() if name.lower().endswith(".csv")]
                if not names:
                    return 0
                payload = zf.read(sorted(names)[0])
        text = payload.decode("utf-8", errors="ignore")
        reader = csv.DictReader(io.StringIO(text))
        loaded = 0
        instrument_map = {
            "STF": "FUTSTK",
            "IDF": "FUTIDX",
            "STO": "OPTSTK",
            "IDO": "OPTIDX",
        }
        for raw in reader:
            row = self._normalize_row(raw)
            raw_instrument = self._first_present(row, ("FH_INSTRUMENT", "INSTRUMENT", "FININSTRMTP"))
            instrument = instrument_map.get(raw_instrument, raw_instrument)
            underlying_symbol = self._first_present(row, ("FH_SYMBOL", "SYMBOL", "TCKRSYMB"))
            expiry_date = self._parse_date(self._first_present(row, ("FH_EXPIRY_DT", "EXPIRY_DT", "XPRYDT")))
            if not instrument or not underlying_symbol or expiry_date is None:
                continue
            strike_price = self._to_decimal(self._first_present(row, ("FH_STRIKE_PR", "STRIKE_PR", "STRKPRIC")))
            option_type = self._first_present(row, ("FH_OPTION_TYP", "OPTION_TYP", "OPTNTP")) or None
            open_price = self._to_decimal(self._first_present(row, ("FH_OPENING_PRICE", "OPEN", "OPNPRIC")))
            high_price = self._to_decimal(self._first_present(row, ("FH_TRADE_HIGH_PRICE", "HIGH", "HGHPRIC")))
            low_price = self._to_decimal(self._first_present(row, ("FH_TRADE_LOW_PRICE", "LOW", "LWPRIC")))
            close_price = self._to_decimal(self._first_present(row, ("FH_CLOSING_PRICE", "CLOSE", "CLSPRIC")))
            settle_price = self._to_decimal(self._first_present(row, ("FH_SETTLE_PRICE", "SETTLE_PR", "STTLMPRIC")))
            volume = self._to_decimal(self._first_present(row, ("FH_TOT_TRADED_QTY", "CONTRACTS", "TTLTRADGVOL")))
            open_interest = self._to_decimal(self._first_present(row, ("FH_OPEN_INT", "OPEN_INT", "OPNINTRST")))
            lot_size_text = self._first_present(row, ("FH_MARKET_LOT", "LOT_SIZE", "NEWBRDLOTQTY"))
            lot_size = int(Decimal(lot_size_text)) if lot_size_text else None
            underlying_isin = self._first_present(row, ("ISIN",)) or self._lookup_underlying_isin(session, underlying_symbol)
            contract_symbol = self._canonical_contract_symbol(
                underlying_symbol=underlying_symbol,
                expiry_date=expiry_date,
                instrument_kind=instrument,
                strike_price=strike_price,
                option_type=option_type,
            )
            if instrument.startswith("FUT"):
                contract = session.scalar(
                    select(FuturesContractMaster)
                    .where(FuturesContractMaster.exchange == Exchange.NSE)
                    .where(FuturesContractMaster.contract_symbol == contract_symbol)
                )
                if contract is None:
                    contract = FuturesContractMaster(
                        exchange=Exchange.NSE,
                        contract_symbol=contract_symbol,
                        underlying_symbol=underlying_symbol,
                        underlying_isin=underlying_isin,
                        instrument_kind=instrument,
                        expiry_date=expiry_date,
                        lot_size=lot_size,
                    )
                    session.add(contract)
                    session.flush()
                eod = session.scalar(
                    select(FuturesEOD)
                    .where(FuturesEOD.contract_id == contract.id)
                    .where(FuturesEOD.trade_date == trade_date)
                )
                if eod is None:
                    eod = FuturesEOD(
                        contract_id=contract.id,
                        trade_date=trade_date,
                        raw_source="nse_fo_bhavcopy",
                        source_artifact_path=path.as_posix(),
                    )
                    session.add(eod)
                eod.open_price = open_price
                eod.high_price = high_price
                eod.low_price = low_price
                eod.close_price = close_price
                eod.settle_price = settle_price
                eod.volume = volume
                eod.open_interest = open_interest
                loaded += 1
            elif instrument.startswith("OPT"):
                if strike_price is None or option_type is None:
                    continue
                option_contract = session.scalar(
                    select(OptionsContractMaster)
                    .where(OptionsContractMaster.exchange == Exchange.NSE)
                    .where(OptionsContractMaster.contract_symbol == contract_symbol)
                )
                if option_contract is None:
                    option_contract = OptionsContractMaster(
                        exchange=Exchange.NSE,
                        contract_symbol=contract_symbol,
                        underlying_symbol=underlying_symbol,
                        underlying_isin=underlying_isin,
                        expiry_date=expiry_date,
                        strike_price=strike_price,
                        option_type=option_type,
                        lot_size=lot_size,
                    )
                    session.add(option_contract)
                    session.flush()
                option_eod = session.scalar(
                    select(OptionsEOD)
                    .where(OptionsEOD.contract_id == option_contract.id)
                    .where(OptionsEOD.trade_date == trade_date)
                )
                if option_eod is None:
                    option_eod = OptionsEOD(
                        contract_id=option_contract.id,
                        trade_date=trade_date,
                        raw_source="nse_fo_bhavcopy",
                        source_artifact_path=path.as_posix(),
                    )
                    session.add(option_eod)
                option_eod.open_price = open_price
                option_eod.high_price = high_price
                option_eod.low_price = low_price
                option_eod.close_price = close_price
                option_eod.settle_price = settle_price
                option_eod.volume = volume
                option_eod.open_interest = open_interest
                loaded += 1
        self._rebuild_continuous_futures(session, trade_date)
        return loaded

    @staticmethod
    def _first_present(row: dict[str, str], keys: tuple[str, ...]) -> str:
        for key in keys:
            value = row.get(key, "")
            if value:
                return value
        return ""

    def _ensure_instrument(
        self,
        session: Session,
        isin: str,
        symbol: str,
        trade_date: date,
        *,
        exchange: Exchange = Exchange.NSE,
        existing_instruments: set[str] | None = None,
        existing_symbol_maps: set[tuple[str, Exchange, str]] | None = None,
    ) -> None:
        instrument_known = (
            isin in existing_instruments
            if existing_instruments is not None
            else session.get(InstrumentMaster, isin) is not None
            or any(isinstance(obj, InstrumentMaster) and obj.isin == isin for obj in session.new)
        )
        if not instrument_known:
            session.add(
                InstrumentMaster(
                    isin=isin,
                    instrument_type=InstrumentType.EQUITY,
                    primary_exchange=exchange,
                    company_name=symbol,
                    listed_date=trade_date,
                    active=True,
                )
            )
            if existing_instruments is not None:
                existing_instruments.add(isin)

        symbol_key = (isin, exchange, symbol)
        symbol_known = (
            symbol_key in existing_symbol_maps
            if existing_symbol_maps is not None
            else session.scalar(
                select(SymbolMap)
                .where(SymbolMap.isin == isin)
                .where(SymbolMap.exchange == exchange)
                .where(SymbolMap.symbol == symbol)
                .where(SymbolMap.valid_to.is_(None))
            )
            is not None
            or any(
                isinstance(obj, SymbolMap)
                and obj.isin == isin
                and obj.exchange == exchange
                and obj.symbol == symbol
                and obj.valid_to is None
                for obj in session.new
            )
        )
        if not symbol_known:
            session.add(
                SymbolMap(
                    isin=isin,
                    exchange=exchange,
                    symbol=symbol,
                    valid_from=trade_date,
                    valid_to=None,
                )
            )
            if existing_symbol_maps is not None:
                existing_symbol_maps.add(symbol_key)

    def _load_bhavcopy_prices(self, session: Session, path: Path, trade_date: date) -> int:
        if not path.exists():
            return 0

        payload = path.read_bytes()
        if path.suffix.lower() == ".zip":
            with zipfile.ZipFile(io.BytesIO(payload)) as zf:
                names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
                if not names:
                    return 0
                payload = zf.read(names[0])

        text = payload.decode("utf-8", errors="ignore")
        reader = csv.DictReader(io.StringIO(text))
        loaded = 0
        existing_instruments = {
            row[0] for row in session.execute(select(InstrumentMaster.isin)).all()
        }
        existing_instruments.update(
            obj.isin for obj in session.new if isinstance(obj, InstrumentMaster)
        )
        existing_symbol_maps = {
            (row[0], row[1], row[2])
            for row in session.execute(
                select(SymbolMap.isin, SymbolMap.exchange, SymbolMap.symbol).where(SymbolMap.valid_to.is_(None))
            ).all()
        }
        existing_symbol_maps.update(
            (obj.isin, obj.exchange, obj.symbol)
            for obj in session.new
            if isinstance(obj, SymbolMap) and obj.valid_to is None
        )
        existing_prices = {
            row.isin: row
            for row in session.scalars(
                select(PriceRecord)
                .where(PriceRecord.exchange == Exchange.NSE)
                .where(PriceRecord.trade_date == trade_date)
            ).all()
        }

        for raw in reader:
            row = self._normalize_row(raw)
            series = self._first_present(row, ("SERIES", "SERIES_TYPE", "SCTYSRS"))
            if series and series != "EQ":
                continue

            isin = self._first_present(row, ("ISIN", "ISIN_NUMBER"))
            symbol = self._first_present(row, ("SYMBOL", "SYMB", "TICKER", "TCKRSYMB"))
            open_p = self._to_decimal(self._first_present(row, ("OPEN", "OPEN_PRICE", "OPNPRIC")))
            high_p = self._to_decimal(self._first_present(row, ("HIGH", "HIGH_PRICE", "HGHPRIC")))
            low_p = self._to_decimal(self._first_present(row, ("LOW", "LOW_PRICE", "LWPRIC")))
            close_p = self._to_decimal(
                self._first_present(row, ("CLOSE", "CLOSE_PRICE", "CLOSE_", "CLSPRIC"))
            )
            volume = self._to_decimal(
                self._first_present(
                    row,
                    (
                        "TOTTRDQTY",
                        "TOTAL_TRADED_QUANTITY",
                        "TTL_TRD_QNTY",
                        "TOT_TRADED_QTY",
                        "TTLTRADGVOL",
                    ),
                )
            )

            if not isin or not symbol or None in (open_p, high_p, low_p, close_p, volume):
                continue
            assert open_p is not None
            assert high_p is not None
            assert low_p is not None
            assert close_p is not None
            assert volume is not None

            self._ensure_instrument(
                session,
                isin=isin,
                symbol=symbol,
                trade_date=trade_date,
                existing_instruments=existing_instruments,
                existing_symbol_maps=existing_symbol_maps,
            )
            existing = existing_prices.get(isin)
            if existing is None:
                existing = PriceRecord(
                    isin=isin,
                    exchange=Exchange.NSE,
                    trade_date=trade_date,
                    open_price=open_p,
                    high_price=high_p,
                    low_price=low_p,
                    close_price=close_p,
                    volume=volume,
                    raw_source="nse_bhavcopy",
                )
                self._ensure_identity_adjusted_fields(existing)
                session.add(existing)
                existing_prices[isin] = existing
            else:
                existing.open_price = open_p
                existing.high_price = high_p
                existing.low_price = low_p
                existing.close_price = close_p
                existing.volume = volume
                existing.raw_source = "nse_bhavcopy"
                self._ensure_identity_adjusted_fields(existing)
            loaded += 1

        return loaded

    def _load_bse_bhavcopy_prices(self, session: Session, path: Path, trade_date: date) -> int:
        if not path.exists():
            return 0

        payload = path.read_bytes()
        if path.suffix.lower() == ".zip":
            with zipfile.ZipFile(io.BytesIO(payload)) as zf:
                names = [name for name in zf.namelist() if name.lower().endswith(".csv")]
                if not names:
                    return 0
                payload = zf.read(names[0])

        text = payload.decode("utf-8", errors="ignore")
        reader = csv.DictReader(io.StringIO(text))
        loaded = 0
        existing_instruments = {
            row[0] for row in session.execute(select(InstrumentMaster.isin)).all()
        }
        existing_instruments.update(
            obj.isin for obj in session.new if isinstance(obj, InstrumentMaster)
        )
        existing_symbol_maps = {
            (row[0], row[1], row[2])
            for row in session.execute(
                select(SymbolMap.isin, SymbolMap.exchange, SymbolMap.symbol).where(SymbolMap.valid_to.is_(None))
            ).all()
        }
        existing_symbol_maps.update(
            (obj.isin, obj.exchange, obj.symbol)
            for obj in session.new
            if isinstance(obj, SymbolMap) and obj.valid_to is None
        )
        existing_prices = {
            row.isin: row
            for row in session.scalars(
                select(PriceRecord)
                .where(PriceRecord.exchange == Exchange.BSE)
                .where(PriceRecord.trade_date == trade_date)
            ).all()
        }

        for raw in reader:
            row = self._normalize_row(raw)
            isin = self._first_present(row, ("ISIN_CODE", "ISIN", "ISIN_NO"))
            symbol = self._first_present(row, ("TCKRSYMB", "SC_NAME", "SYMBOL", "SC_CODE", "FININSTRMNM"))
            open_p = self._to_decimal(self._first_present(row, ("OPEN", "OPEN_PRICE", "OPNPRIC")))
            high_p = self._to_decimal(self._first_present(row, ("HIGH", "HIGH_PRICE", "HGHPRIC")))
            low_p = self._to_decimal(self._first_present(row, ("LOW", "LOW_PRICE", "LWPRIC")))
            close_p = self._to_decimal(self._first_present(row, ("CLOSE", "CLOSE_PRICE", "CLSPRIC")))
            volume = self._to_decimal(
                self._first_present(
                    row,
                    ("NO_OF_SHRS", "TOTTRDQTY", "VOLUME", "TTLTRADGVOL", "TTLTRADG_VOL"),
                )
            )

            if not isin or not symbol or None in (open_p, high_p, low_p, close_p, volume):
                continue
            assert open_p is not None
            assert high_p is not None
            assert low_p is not None
            assert close_p is not None
            assert volume is not None

            self._ensure_instrument(
                session,
                isin=isin,
                symbol=symbol,
                trade_date=trade_date,
                exchange=Exchange.BSE,
                existing_instruments=existing_instruments,
                existing_symbol_maps=existing_symbol_maps,
            )
            existing = existing_prices.get(isin)
            if existing is None:
                existing = PriceRecord(
                    isin=isin,
                    exchange=Exchange.BSE,
                    trade_date=trade_date,
                    open_price=open_p,
                    high_price=high_p,
                    low_price=low_p,
                    close_price=close_p,
                    volume=volume,
                    raw_source="bse_bhavcopy",
                )
                self._ensure_identity_adjusted_fields(existing)
                session.add(existing)
                existing_prices[isin] = existing
            else:
                existing.open_price = open_p
                existing.high_price = high_p
                existing.low_price = low_p
                existing.close_price = close_p
                existing.volume = volume
                existing.raw_source = "bse_bhavcopy"
                self._ensure_identity_adjusted_fields(existing)
            loaded += 1

        return loaded

    @staticmethod
    def _parse_bse_graph_trade_date(value: object) -> date | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        for fmt in ("%a %b %d %Y %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        return None

    def _load_bse_prices_from_stockreach(self, session: Session, as_of: date) -> int:
        raise RuntimeError(
            "Synthetic BSE StockReach graph loading is disabled; official BSE bhavcopy is required."
        )

    def _load_corporate_actions(self, session: Session, source: Exchange, path: Path) -> int:
        if not path.exists():
            return 0
        content = path.read_text(encoding="utf-8", errors="ignore")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            return 0

        records: list[dict[str, object]] = []
        if isinstance(parsed, list):
            records = [r for r in parsed if isinstance(r, dict)]
        elif isinstance(parsed, dict):
            for key in ("data", "results", "Table", "tableData"):
                value = parsed.get(key)
                if isinstance(value, list):
                    records = [r for r in value if isinstance(r, dict)]
                    break

        loaded = 0
        for item in records:
            normalized = self._normalize_row(dict(item))
            isin = self._first_present(normalized, ("ISIN", "ISIN_CODE", "SECURITY_ISIN"))
            symbol = self._first_present(
                normalized,
                (
                    "SYMBOL",
                    "TCKRSYMB",
                    "SC_NAME",
                    "SHORT_NAME",
                    "SHORTNAME",
                ),
            )
            scrip_code = self._first_present(normalized, ("SCRIP_CODE", "SCRIP_CD"))

            purpose = self._first_present(
                normalized,
                ("PURPOSE", "SUBJECT", "DESCRIPTION", "CORP_ACTION", "ACTION_TYPE", "NEWSSUB"),
            )
            action_type = self.ca_parser.map_action_type(purpose)
            if action_type == CorporateActionType.UNCLASSIFIED and not purpose.strip():
                continue

            ex_date = self._parse_date(
                self._first_present(
                    normalized,
                    ("EX_DATE", "EX_DT", "EXDATE", "XDATE", "MEETING_DATE"),
                )
            )
            announcement_date = self._parse_date(
                self._first_present(
                    normalized,
                    ("ANNOUNCEMENT_DATE", "ANN_DATE", "DATE", "ANNDT", "ANN_DT", "NEWS_DT"),
                )
            )
            record_date = self._parse_date(
                self._first_present(normalized, ("RECORD_DATE", "RECORD_DT"))
            )

            if not isin and symbol:
                resolved = session.scalar(
                    select(SymbolMap.isin)
                    .where(SymbolMap.exchange == Exchange.NSE)
                    .where(SymbolMap.symbol == symbol)
                    .where(SymbolMap.valid_to.is_(None))
                )
                if resolved:
                    isin = resolved

            if not isin:
                continue

            if source == Exchange.BSE and action_type == CorporateActionType.UNCLASSIFIED:
                # The BSE payload frequently includes board-meeting calendar rows with no actionable CA type.
                # Keeping them out of staging is safer than promoting them into false corporate actions.
                continue

            existing = session.scalar(
                select(CorporateActionStaging)
                .where(CorporateActionStaging.source == source)
                .where(CorporateActionStaging.isin == isin)
                .where(CorporateActionStaging.ex_date == ex_date)
                .where(CorporateActionStaging.action_type == action_type)
            )
            if existing is not None:
                continue

            payload: dict[str, object] = {
                "isin": isin,
                "ex_date": ex_date.isoformat() if ex_date else None,
                "record_date": record_date.isoformat() if record_date else None,
                "purpose": purpose,
                "symbol": symbol,
            }
            if scrip_code:
                payload["scrip_code"] = scrip_code
            issue_price = self._to_decimal(
                self._first_present(normalized, ("ISSUE_PRICE", "PRICE", "SUBSCRIPTION_PRICE"))
            )
            if issue_price is not None:
                payload["issue_price"] = str(issue_price)

            ratio = self._first_present(normalized, ("RATIO", "SHARE_RATIO", "RATIO_TEXT"))
            if ":" in ratio:
                left, right = ratio.split(":", 1)
                lval = self._to_decimal(left)
                rval = self._to_decimal(right)
                if lval is not None and rval is not None:
                    if action_type == CorporateActionType.BONUS:
                        payload["bonus_ratio_numerator"] = str(lval)
                        payload["bonus_ratio_denominator"] = str(rval)
                    if action_type in {CorporateActionType.RIGHTS, CorporateActionType.RIGHTS_RENOUNCE}:
                        payload["rights_ratio_numerator"] = str(lval)
                        payload["rights_ratio_denominator"] = str(rval)

            self.ca_parser.enrich_payload_from_subject(
                payload=payload,
                action_type=action_type,
                purpose=purpose,
            )

            self.ca_service.add_staging_record(
                session=session,
                source=source,
                isin=isin,
                action_type=action_type,
                announcement_date=announcement_date,
                ex_date=ex_date,
                record_date=record_date,
                payload=payload,
            )
            loaded += 1

        return loaded

    def run_track_a(self, as_of: date) -> dict[str, str]:
        sources = [
            "NSE_EQUITY_BHAVCOPY",
            "BSE_EQUITY_BHAVCOPY",
            "NSE_FO_BHAVCOPY",
            "NSE_CORPORATE_ACTIONS",
            "BSE_CORPORATE_ACTIONS",
            "NSE_FII_DII",
            "INDIA_VIX",
        ]
        required_sources = {"NSE_EQUITY_BHAVCOPY", "BSE_EQUITY_BHAVCOPY"}
        paths: dict[str, str] = {}
        for source in sources:
            try:
                paths[source] = self.ingestor.ingest_raw_source(source, as_of)
            except Exception:
                if source in required_sources:
                    raise
                paths[source] = ""

        with get_session() as session:
            self._load_bhavcopy_prices(session, Path(paths["NSE_EQUITY_BHAVCOPY"]), as_of)
            if paths.get("BSE_EQUITY_BHAVCOPY"):
                self._load_bse_bhavcopy_prices(session, Path(paths["BSE_EQUITY_BHAVCOPY"]), as_of)
            if paths.get("NSE_FO_BHAVCOPY"):
                self._load_nse_fo(session, Path(paths["NSE_FO_BHAVCOPY"]), as_of)
            if paths.get("NSE_CORPORATE_ACTIONS"):
                self._load_corporate_actions(
                    session,
                    Exchange.NSE,
                    Path(paths["NSE_CORPORATE_ACTIONS"]),
                )
            if paths.get("BSE_CORPORATE_ACTIONS"):
                self._load_corporate_actions(
                    session,
                    Exchange.BSE,
                    Path(paths["BSE_CORPORATE_ACTIONS"]),
                )
            if paths.get("NSE_FII_DII"):
                self._load_fii_dii(session, Path(paths["NSE_FII_DII"]))
            if paths.get("INDIA_VIX"):
                self._load_market_indices(session, Path(paths["INDIA_VIX"]), as_of)
        return paths

    def run_scheduled_corporate_action_collection(self, run_at: datetime) -> dict[str, str]:
        aware_run_at = run_at if run_at.tzinfo is not None else run_at.replace(tzinfo=UTC)
        due_sources = due_corporate_action_sources(aware_run_at)
        if not due_sources:
            raise ValueError(f"No corporate action source is due at {aware_run_at.isoformat()}")

        paths: dict[str, str] = {}
        as_of = aware_run_at.astimezone(UTC).date()
        for source_key in due_sources:
            paths[source_key] = self.ingestor.ingest_raw_source(source_key, as_of)

        with get_session() as session:
            if paths.get("NSE_CORPORATE_ACTIONS"):
                self._load_corporate_actions(
                    session,
                    Exchange.NSE,
                    Path(paths["NSE_CORPORATE_ACTIONS"]),
                )
            if paths.get("BSE_CORPORATE_ACTIONS"):
                self._load_corporate_actions(
                    session,
                    Exchange.BSE,
                    Path(paths["BSE_CORPORATE_ACTIONS"]),
                )
        return paths

    def _resolve_market_isin(self, session: Session, market_isin: str | None) -> str | None:
        if market_isin:
            return market_isin
        if settings.market_proxy_isin:
            return settings.market_proxy_isin
        has_prices = session.scalar(select(PriceRecord.id).limit(1)) is not None
        if not has_prices:
            return None
        raise ValueError("market_isin is required; pass it explicitly or set OMEGA_MARKET_PROXY_ISIN")

    def run_track_b(self, as_of: date, market_isin: str | None = None) -> tuple[int, int, int, int, int]:
        with get_session() as session:
            confirmations = self.ca_service.run_daily_confirmation(session, as_of=as_of)

            adjusted_rows = 0
            isins = [row[0] for row in session.execute(select(PriceRecord.isin).distinct()).all()]
            resolved_market_isin = self._resolve_market_isin(session, market_isin)
            if resolved_market_isin is not None and resolved_market_isin not in set(isins):
                raise LookupError(f"Configured market proxy {resolved_market_isin} is not present in price records")

            for isin in isins:
                adjusted_rows += self.adjustment_engine.recompute_adjusted_series(
                    session,
                    isin=isin,
                    exchange=Exchange.NSE,
                )

            discontinuities = []
            if resolved_market_isin is not None:
                discontinuities = self.discontinuity_detector.detect(
                    session,
                    market_isin=resolved_market_isin,
                    exchange=Exchange.NSE,
                )

            validation_count = 0
            price_validation_map: dict[tuple[str, date], dict[str, object]] = {}
            for isin in isins:
                price_outcomes = self.validator.validate_nse_bse_prices(session, isin)
                validation_count += len(price_outcomes)
                for outcome in price_outcomes:
                    key = (isin, outcome.data_date)
                    state = price_validation_map.setdefault(
                        key,
                        {"max_diff": Decimal("0"), "failed": False},
                    )
                    state["max_diff"] = max(Decimal(str(state["max_diff"])), outcome.difference_pct)
                    if outcome.result.value == "FAIL":
                        state["failed"] = True
                validation_count += len(self.validator.validate_corporate_actions(session, isin))

            nse_pairs = {
                (row[0], row[1])
                for row in session.execute(
                    select(PriceRecord.isin, PriceRecord.trade_date).where(PriceRecord.exchange == Exchange.NSE)
                ).all()
            }
            bse_pairs = {
                (row[0], row[1])
                for row in session.execute(
                    select(PriceRecord.isin, PriceRecord.trade_date).where(PriceRecord.exchange == Exchange.BSE)
                ).all()
            }
            matched_pairs = nse_pairs & bse_pairs
            discontinuity_map = {
                (event.isin, event.event_date): event.category
                for event in session.scalars(select(DiscontinuityEvent)).all()
            }

            for row in session.scalars(select(PriceRecord)).all():
                chain = row.adjustment_chain or []
                has_medium = any(item.get("ca_confidence") == "MEDIUM" for item in chain)
                has_low = any(item.get("ca_confidence") == "LOW" for item in chain)
                rights_fallback = any(
                    bool(item.get("subscription_price_fallback_zero", False)) for item in chain
                )
                validation_state = price_validation_map.get((row.isin, row.trade_date))
                inputs = ConfidenceInputs(
                    is_secondary_source=(row.raw_source.lower() != "nse_bhavcopy"),
                    cross_validation_available=((row.isin, row.trade_date) in matched_pairs),
                    cross_validation_discrepancy_pct=(
                        None
                        if validation_state is None
                        else Decimal(str(validation_state["max_diff"]))
                    ),
                    cross_validation_failed=bool(validation_state and validation_state["failed"]),
                    has_medium_ca=has_medium,
                    has_low_ca=has_low,
                    rights_subscription_fallback_zero=rights_fallback,
                    is_gap_fill=bool(row.is_imputed),
                    is_reconstructed_universe=False,
                    discontinuity_category=discontinuity_map.get((row.isin, row.trade_date)),
                )
                row.confidence_score = self.confidence_scorer.compute_score(inputs)

            new_discontinuities = sum(1 for event in discontinuities if event.is_new)
            total_discontinuity_events = int(
                session.query(DiscontinuityEvent).count()
            )

            return len(confirmations), adjusted_rows, new_discontinuities, total_discontinuity_events, validation_count

    def run_scheduled_track_b_confirmation(
        self,
        run_at: datetime,
        market_isin: str | None = None,
    ) -> tuple[int, int, int, int, int]:
        require_confirmation_window(run_at)
        aware_run_at = run_at if run_at.tzinfo is not None else run_at.replace(tzinfo=UTC)
        return self.run_track_b(as_of=aware_run_at.astimezone(UTC).date(), market_isin=market_isin)

    def run_full_day(self, as_of: date, market_isin: str | None = None) -> PipelineSummary:
        paths = self.run_track_a(as_of)
        confirmed, adjusted, discontinuities, total_discontinuity_events, validations = self.run_track_b(
            as_of=as_of,
            market_isin=market_isin,
        )
        return PipelineSummary(
            ingest_paths=list(paths.values()),
            confirmed_actions=confirmed,
            adjusted_rows=adjusted,
            discontinuities=discontinuities,
            total_discontinuity_events=total_discontinuity_events,
            validations=validations,
        )
