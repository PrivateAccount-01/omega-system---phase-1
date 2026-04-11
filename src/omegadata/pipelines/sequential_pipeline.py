from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Mapping
import zipfile

from sqlalchemy import select

from omegadata.db.models import (
    CorporateActionStaging,
    DiscontinuityEvent,
    InstrumentMaster,
    PriceRecord,
    SymbolMap,
)
from omegadata.db.session import get_session
from omegadata.domain import CorporateActionType, Exchange, InstrumentType
from omegadata.track_a.orchestration import IngestionOrchestrator
from omegadata.track_a.collection_schedule import (
    due_corporate_action_sources,
    require_confirmation_window,
)
from omegadata.track_b.adjustment_engine import PriceAdjustmentEngine
from omegadata.track_b.confidence import ConfidenceInputs, ConfidenceScorer
from omegadata.track_b.corporate_actions import CorporateActionService
from omegadata.track_b.cross_source_validation import CrossSourceValidator
from omegadata.track_b.discontinuity import DiscontinuityDetector


@dataclass(frozen=True)
class PipelineSummary:
    ingest_paths: list[str]
    confirmed_actions: int
    adjusted_rows: int
    discontinuities: int
    validations: int


class OmegaDataSequentialPipeline:
    _RATIO_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*:\s*(\d+(?:\.\d+)?)")
    _DIVIDEND_PATTERN = re.compile(
        r"\bdividend\b[^0-9]*(?:rs|re)\.?\s*([0-9]+(?:\.[0-9]+)?)",
        re.IGNORECASE,
    )
    _FACE_VALUE_PATTERN = re.compile(
        r"\bfrom\s+r(?:s|e)\.?\s*([0-9]+(?:\.[0-9]+)?)"
        r".*?\bto\s+r(?:s|e)\.?\s*([0-9]+(?:\.[0-9]+)?)",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        self.ingestor = IngestionOrchestrator()
        self.ca_service = CorporateActionService()
        self.adjustment_engine = PriceAdjustmentEngine()
        self.discontinuity_detector = DiscontinuityDetector()
        self.confidence_scorer = ConfidenceScorer()
        self.validator = CrossSourceValidator()

    @staticmethod
    def _to_decimal(value: str | int | float | None) -> Decimal | None:
        if value in (None, ""):
            return None
        text = str(value).replace(",", "").strip()
        if not text:
            return None
        try:
            return Decimal(text)
        except Exception:
            return None

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
    def _first_present(row: dict[str, str], keys: tuple[str, ...]) -> str:
        for key in keys:
            value = row.get(key, "")
            if value:
                return value
        return ""

    def _populate_subject_derived_fields(
        self,
        *,
        payload: dict[str, object],
        action_type: CorporateActionType,
        purpose: str,
    ) -> None:
        if not purpose.strip():
            return

        ratio_match = self._RATIO_PATTERN.search(purpose)
        if ratio_match:
            left = self._to_decimal(ratio_match.group(1))
            right = self._to_decimal(ratio_match.group(2))
            if left is not None and right is not None:
                if action_type == CorporateActionType.BONUS:
                    payload.setdefault("bonus_ratio_numerator", str(left))
                    payload.setdefault("bonus_ratio_denominator", str(right))
                if action_type in {CorporateActionType.RIGHTS, CorporateActionType.RIGHTS_RENOUNCE}:
                    payload.setdefault("rights_ratio_numerator", str(left))
                    payload.setdefault("rights_ratio_denominator", str(right))

        if action_type in {CorporateActionType.DIVIDEND_CASH, CorporateActionType.DIVIDEND_SPECIAL}:
            dividend_match = self._DIVIDEND_PATTERN.search(purpose)
            if dividend_match is not None:
                amount = self._to_decimal(dividend_match.group(1))
                if amount is not None:
                    payload.setdefault("dividend_per_share", str(amount))

        if action_type in {CorporateActionType.SPLIT, CorporateActionType.SPLIT_REVERSE}:
            fv_match = self._FACE_VALUE_PATTERN.search(purpose)
            if fv_match is not None:
                old_face_value = self._to_decimal(fv_match.group(1))
                new_face_value = self._to_decimal(fv_match.group(2))
                if old_face_value is not None and new_face_value is not None:
                    payload.setdefault("old_face_value", str(old_face_value))
                    payload.setdefault("new_face_value", str(new_face_value))

    def _ensure_instrument(self, session, isin: str, symbol: str, trade_date: date) -> None:
        inst = session.get(InstrumentMaster, isin)
        if inst is None:
            session.add(
                InstrumentMaster(
                    isin=isin,
                    instrument_type=InstrumentType.EQUITY,
                    primary_exchange=Exchange.NSE,
                    company_name=symbol,
                    listed_date=trade_date,
                    active=True,
                )
            )

        existing_symbol = session.scalar(
            select(SymbolMap)
            .where(SymbolMap.isin == isin)
            .where(SymbolMap.exchange == Exchange.NSE)
            .where(SymbolMap.symbol == symbol)
            .where(SymbolMap.valid_to.is_(None))
        )
        if existing_symbol is None:
            session.add(
                SymbolMap(
                    isin=isin,
                    exchange=Exchange.NSE,
                    symbol=symbol,
                    valid_from=trade_date,
                    valid_to=None,
                )
            )

    def _load_bhavcopy_prices(self, session, path: Path, trade_date: date) -> int:
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

            self._ensure_instrument(session, isin=isin, symbol=symbol, trade_date=trade_date)
            existing = session.scalar(
                select(PriceRecord)
                .where(PriceRecord.isin == isin)
                .where(PriceRecord.exchange == Exchange.NSE)
                .where(PriceRecord.trade_date == trade_date)
            )
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
                session.add(existing)
            else:
                existing.open_price = open_p
                existing.high_price = high_p
                existing.low_price = low_p
                existing.close_price = close_p
                existing.volume = volume
                existing.raw_source = "nse_bhavcopy"
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

    def _load_bse_prices_from_stockreach(self, session, as_of: date) -> int:
        nse_isins = {
            row[0]
            for row in session.execute(
                select(PriceRecord.isin)
                .where(PriceRecord.exchange == Exchange.NSE)
                .where(PriceRecord.trade_date == as_of)
            ).all()
        }
        if not nse_isins:
            return 0

        bse_rows = session.scalars(
            select(CorporateActionStaging).where(CorporateActionStaging.source == Exchange.BSE)
        ).all()
        isin_to_scrip: dict[str, str] = {}
        for row in bse_rows:
            if row.isin not in nse_isins:
                continue
            payload = row.payload or {}
            scrip_code = str(
                payload.get("scrip_code")
                or payload.get("scrip_cd")
                or payload.get("SCRIP_CODE")
                or ""
            ).strip()
            if scrip_code and scrip_code.isdigit():
                isin_to_scrip[row.isin] = scrip_code

        loaded = 0
        for isin, scrip_code in isin_to_scrip.items():
            try:
                graph = self.ingestor.download_manager.fetch_bse_stockreach_graph(
                    scrip_code=scrip_code,
                    from_date=as_of,
                    to_date=as_of,
                )
            except Exception:
                continue

            raw_points = graph.get("Data")
            if not raw_points:
                continue

            try:
                if isinstance(raw_points, str):
                    points = json.loads(raw_points)
                elif isinstance(raw_points, list):
                    points = raw_points
                else:
                    continue
            except Exception:
                continue

            for point in points:
                if not isinstance(point, dict):
                    continue
                trade_date = self._parse_bse_graph_trade_date(point.get("dttm"))
                if trade_date != as_of:
                    continue

                close_price = self._to_decimal(point.get("vale1"))
                volume = self._to_decimal(point.get("vole"))
                if close_price is None:
                    continue
                if volume is None:
                    volume = Decimal("0")

                existing = session.scalar(
                    select(PriceRecord)
                    .where(PriceRecord.isin == isin)
                    .where(PriceRecord.exchange == Exchange.BSE)
                    .where(PriceRecord.trade_date == trade_date)
                )
                if existing is None:
                    existing = PriceRecord(
                        isin=isin,
                        exchange=Exchange.BSE,
                        trade_date=trade_date,
                        open_price=close_price,
                        high_price=close_price,
                        low_price=close_price,
                        close_price=close_price,
                        volume=volume,
                        raw_source="bse_stockreach_graph",
                    )
                    session.add(existing)
                else:
                    existing.open_price = close_price
                    existing.high_price = close_price
                    existing.low_price = close_price
                    existing.close_price = close_price
                    existing.volume = volume
                    existing.raw_source = "bse_stockreach_graph"
                loaded += 1

        return loaded

    @staticmethod
    def _map_action_type(text: str) -> CorporateActionType:
        value = text.upper()
        if "BONUS" in value:
            return CorporateActionType.BONUS
        if "BUY BACK" in value or "BUYBACK" in value:
            return CorporateActionType.BUYBACK_OPEN_MARKET
        if "SPLIT" in value and "REVERSE" in value:
            return CorporateActionType.SPLIT_REVERSE
        if "SPLIT" in value:
            return CorporateActionType.SPLIT
        if "RIGHT" in value:
            return CorporateActionType.RIGHTS
        if "DEMERGER" in value:
            return CorporateActionType.DEMERGER_PARENT
        if "MERGER" in value or "AMALGAMATION" in value:
            return CorporateActionType.MERGER_TARGET
        if "DIVIDEND" in value and "SPECIAL" in value:
            return CorporateActionType.DIVIDEND_SPECIAL
        if "DIVIDEND" in value:
            return CorporateActionType.DIVIDEND_CASH
        return CorporateActionType.UNCLASSIFIED

    def _load_corporate_actions(self, session, source: Exchange, path: Path) -> int:
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
            normalized = self._normalize_row({k: v for k, v in item.items()})
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
            action_type = self._map_action_type(purpose)
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

            self._populate_subject_derived_fields(
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
            "NSE_CORPORATE_ACTIONS",
            "BSE_CORPORATE_ACTIONS",
            "NSE_FII_DII",
            "INDIA_VIX",
        ]
        required_sources = {"NSE_EQUITY_BHAVCOPY"}
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
            self._load_bse_prices_from_stockreach(session, as_of=as_of)
        return paths

    def run_scheduled_corporate_action_collection(self, run_at: datetime) -> dict[str, str]:
        aware_run_at = run_at if run_at.tzinfo is not None else run_at.replace(tzinfo=timezone.utc)
        due_sources = due_corporate_action_sources(aware_run_at)
        if not due_sources:
            raise ValueError(f"No corporate action source is due at {aware_run_at.isoformat()}")

        paths: dict[str, str] = {}
        as_of = aware_run_at.astimezone(timezone.utc).date()
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

    def run_track_b(self, as_of: date, market_isin: str | None = None) -> tuple[int, int, int, int]:
        with get_session() as session:
            confirmations = self.ca_service.run_daily_confirmation(session, as_of=as_of)

            adjusted_rows = 0
            isins = [row[0] for row in session.execute(select(PriceRecord.isin).distinct()).all()]
            if market_isin is None and isins:
                market_isin = isins[0]

            for isin in isins:
                adjusted_rows += self.adjustment_engine.recompute_adjusted_series(
                    session,
                    isin=isin,
                    exchange=Exchange.NSE,
                )

            discontinuities = []
            if market_isin is not None:
                discontinuities = self.discontinuity_detector.detect(
                    session,
                    market_isin=market_isin,
                    exchange=Exchange.NSE,
                )

            validation_count = 0
            for isin in isins:
                validation_count += len(self.validator.validate_nse_bse_prices(session, isin))
                validation_count += len(self.validator.validate_corporate_actions(session, isin))

            bse_pairs = {
                (row[0], row[1])
                for row in session.execute(
                    select(PriceRecord.isin, PriceRecord.trade_date).where(PriceRecord.exchange == Exchange.BSE)
                ).all()
            }
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
                inputs = ConfidenceInputs(
                    is_secondary_source=(row.raw_source.lower() != "nse_bhavcopy"),
                    cross_validation_available=((row.isin, row.trade_date) in bse_pairs),
                    cross_validation_discrepancy_pct=None,
                    has_medium_ca=has_medium,
                    has_low_ca=has_low,
                    rights_subscription_fallback_zero=rights_fallback,
                    is_gap_fill=bool(row.is_imputed),
                    is_reconstructed_universe=False,
                    discontinuity_category=discontinuity_map.get((row.isin, row.trade_date)),
                )
                row.confidence_score = self.confidence_scorer.compute_score(inputs)

            return len(confirmations), adjusted_rows, len(discontinuities), validation_count

    def run_scheduled_track_b_confirmation(
        self,
        run_at: datetime,
        market_isin: str | None = None,
    ) -> tuple[int, int, int, int]:
        require_confirmation_window(run_at)
        aware_run_at = run_at if run_at.tzinfo is not None else run_at.replace(tzinfo=timezone.utc)
        return self.run_track_b(as_of=aware_run_at.astimezone(timezone.utc).date(), market_isin=market_isin)

    def run_full_day(self, as_of: date, market_isin: str | None = None) -> PipelineSummary:
        paths = self.run_track_a(as_of)
        confirmed, adjusted, discontinuities, validations = self.run_track_b(
            as_of=as_of,
            market_isin=market_isin,
        )
        return PipelineSummary(
            ingest_paths=list(paths.values()),
            confirmed_actions=confirmed,
            adjusted_rows=adjusted,
            discontinuities=discontinuities,
            validations=validations,
        )
