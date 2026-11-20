from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from omegadata.db.base import Base
from omegadata.domain import (
    ConfidenceLevel,
    CorporateActionType,
    DiscontinuityCategory,
    Exchange,
    InstrumentType,
    ReleaseProfile,
    ValidationResult,
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


class InstrumentMaster(Base):
    __tablename__ = "instrument_master"

    isin: Mapped[str] = mapped_column(String(12), primary_key=True)
    instrument_type: Mapped[InstrumentType] = mapped_column(Enum(InstrumentType), nullable=False)
    primary_exchange: Mapped[Exchange] = mapped_column(Enum(Exchange), nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sector_name: Mapped[str | None] = mapped_column(String(64))
    listed_date: Mapped[date | None] = mapped_column(Date)
    delisted_date: Mapped[date | None] = mapped_column(Date)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_utc_now,
        onupdate=_utc_now,
        nullable=False,
    )


class SymbolMap(Base):
    __tablename__ = "symbol_map"
    __table_args__ = (
        UniqueConstraint("exchange", "symbol", "valid_from", name="uq_symbol_exchange_validfrom"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    isin: Mapped[str] = mapped_column(ForeignKey("instrument_master.isin"), nullable=False)
    exchange: Mapped[Exchange] = mapped_column(Enum(Exchange), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date)


class SymbolChangeLog(Base):
    __tablename__ = "symbol_change_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    isin: Mapped[str] = mapped_column(ForeignKey("instrument_master.isin"), nullable=False)
    exchange: Mapped[Exchange] = mapped_column(Enum(Exchange), nullable=False)
    old_symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    new_symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    circular_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    discrepancy_found: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, nullable=False)


class DelistingRecord(Base):
    __tablename__ = "delisting_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    isin: Mapped[str] = mapped_column(ForeignKey("instrument_master.isin"), nullable=False)
    reason: Mapped[str] = mapped_column(String(64), nullable=False)
    delisting_type: Mapped[str] = mapped_column(String(64), nullable=False)
    last_trading_date: Mapped[date] = mapped_column(Date, nullable=False)
    last_recorded_price: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, nullable=False)


class IPORegistry(Base):
    __tablename__ = "ipo_registry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    isin: Mapped[str] = mapped_column(ForeignKey("instrument_master.isin"), nullable=False)
    listing_date: Mapped[date] = mapped_column(Date, nullable=False)
    ipo_price: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    issue_size: Mapped[Decimal] = mapped_column(Numeric(30, 2), nullable=False)


class CrossListingMap(Base):
    __tablename__ = "cross_listing_map"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    isin: Mapped[str] = mapped_column(ForeignKey("instrument_master.isin"), nullable=False)
    foreign_exchange: Mapped[str] = mapped_column(String(64), nullable=False)
    foreign_identifier: Mapped[str] = mapped_column(String(64), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date)


class CorporateActionStaging(Base):
    __tablename__ = "corporate_action_staging"
    __table_args__ = (
        Index("ix_ca_staging_source_isin_exdate", "source", "isin", "ex_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[Exchange] = mapped_column(Enum(Exchange), nullable=False)
    isin: Mapped[str] = mapped_column(String(12), nullable=False)
    action_type: Mapped[CorporateActionType] = mapped_column(Enum(CorporateActionType), nullable=False)
    announcement_date: Mapped[date | None] = mapped_column(Date)
    ex_date: Mapped[date | None] = mapped_column(Date)
    record_date: Mapped[date | None] = mapped_column(Date)
    payload: Mapped[dict[str, str | int | float | None]] = mapped_column(JSON, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, nullable=False)
    matched: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class ConfirmedCorporateAction(Base):
    __tablename__ = "confirmed_corporate_action"
    __table_args__ = (
        Index("ix_confirmed_ca_isin_exdate", "isin", "ex_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    isin: Mapped[str] = mapped_column(String(12), nullable=False)
    action_type: Mapped[CorporateActionType] = mapped_column(Enum(CorporateActionType), nullable=False)
    confidence: Mapped[ConfidenceLevel] = mapped_column(Enum(ConfidenceLevel), nullable=False)
    announcement_date: Mapped[date | None] = mapped_column(Date)
    ex_date: Mapped[date | None] = mapped_column(Date)
    record_date: Mapped[date | None] = mapped_column(Date)
    parameters: Mapped[dict[str, str | int | float | None]] = mapped_column(JSON, default=dict)
    source_preference: Mapped[Exchange] = mapped_column(Enum(Exchange), nullable=False)
    superseded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supersedes_id: Mapped[int | None] = mapped_column(ForeignKey("confirmed_corporate_action.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, nullable=False)


class ManualReviewQueue(Base):
    __tablename__ = "manual_review_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    isin: Mapped[str | None] = mapped_column(String(12))
    event_date: Mapped[date | None] = mapped_column(Date)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, str | int | float | None]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class ReprocessJob(Base):
    __tablename__ = "reprocess_job"
    __table_args__ = (
        Index("ix_reprocess_job_status_created", "status", "created_at"),
        UniqueConstraint("review_id", name="uq_reprocess_job_review"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("manual_review_queue.id"), nullable=False)
    isin: Mapped[str | None] = mapped_column(String(12))
    event_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="QUEUED")
    requested_payload: Mapped[dict[str, str | int | float | bool | list[object] | dict[str, object] | None]] = mapped_column(JSON, default=dict)
    completion_payload: Mapped[dict[str, str | int | float | bool | list[object] | dict[str, object] | None] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)


class PriceRecord(Base):
    __tablename__ = "price_record"
    __table_args__ = (
        UniqueConstraint("isin", "exchange", "trade_date", name="uq_price_isin_exchange_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    isin: Mapped[str] = mapped_column(String(12), nullable=False)
    exchange: Mapped[Exchange] = mapped_column(Enum(Exchange), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    open_price: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    high_price: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    low_price: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    close_price: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    volume: Mapped[Decimal] = mapped_column(Numeric(24, 4), nullable=False)
    raw_source: Mapped[str] = mapped_column(String(64), nullable=False)
    adjusted_open_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    adjusted_high_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    adjusted_low_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    adjusted_close_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    adjusted_volume: Mapped[Decimal | None] = mapped_column(Numeric(24, 4))
    adjustment_chain: Mapped[list[dict[str, str | float | int | bool]]] = mapped_column(JSON, default=list)
    cumulative_price_factor: Mapped[Decimal | None] = mapped_column(Numeric(30, 12))
    cumulative_volume_factor: Mapped[Decimal | None] = mapped_column(Numeric(30, 12))
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("1.00"), nullable=False)
    is_imputed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class ExclusionDate(Base):
    __tablename__ = "exclusion_date"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[str] = mapped_column(String(64), nullable=False)


class DiscontinuityEvent(Base):
    __tablename__ = "discontinuity_event"
    __table_args__ = (
        Index("ix_disc_isin_date", "isin", "event_date"),
        UniqueConstraint("isin", "event_date", "category", name="uq_disc_isin_date_category"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    isin: Mapped[str] = mapped_column(String(12), nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    overnight_return: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    market_return: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    beta_used: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    idiosyncratic_return: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    category: Mapped[DiscontinuityCategory] = mapped_column(
        Enum(DiscontinuityCategory), nullable=False
    )
    auto_adjust_queued: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    review_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, nullable=False)


class UniverseMembership(Base):
    __tablename__ = "universe_membership"
    __table_args__ = (
        Index("ix_universe_index_effective", "index_name", "effective_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    isin: Mapped[str] = mapped_column(String(12), nullable=False)
    index_name: Mapped[str] = mapped_column(String(32), nullable=False)
    added_date: Mapped[date] = mapped_column(Date, nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    removed_date: Mapped[date | None] = mapped_column(Date)
    removal_effective: Mapped[date | None] = mapped_column(Date)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    source_confidence: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("1.00"))


class ValidationAuditLog(Base):
    __tablename__ = "validation_audit_log"
    __table_args__ = (
        Index("ix_validation_isin_datadate", "isin", "data_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    validation_date: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, nullable=False)
    source_1: Mapped[str] = mapped_column(String(64), nullable=False)
    source_2: Mapped[str] = mapped_column(String(64), nullable=False)
    isin: Mapped[str | None] = mapped_column(String(12))
    data_date: Mapped[date | None] = mapped_column(Date)
    field_compared: Mapped[str] = mapped_column(String(64), nullable=False)
    source_1_value: Mapped[str] = mapped_column(String(255), nullable=False)
    source_2_value: Mapped[str] = mapped_column(String(255), nullable=False)
    difference_absolute: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    difference_pct: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    tolerance_applied: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    result: Mapped[ValidationResult] = mapped_column(Enum(ValidationResult), nullable=False)
    resolution_status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN")
    resolution_notes: Mapped[str | None] = mapped_column(Text)


class ParticipantFlowDaily(Base):
    __tablename__ = "participant_flow_daily"
    __table_args__ = (
        UniqueConstraint("trade_date", "participant_category", name="uq_participant_flow_date_category"),
        Index("ix_participant_flow_date", "trade_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    participant_category: Mapped[str] = mapped_column(String(32), nullable=False)
    buy_value: Mapped[Decimal] = mapped_column(Numeric(24, 4), nullable=False)
    sell_value: Mapped[Decimal] = mapped_column(Numeric(24, 4), nullable=False)
    net_value: Mapped[Decimal] = mapped_column(Numeric(24, 4), nullable=False)
    raw_source: Mapped[str] = mapped_column(String(64), nullable=False)
    source_artifact_path: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, nullable=False)


class MarketIndexDaily(Base):
    __tablename__ = "market_index_daily"
    __table_args__ = (
        UniqueConstraint("trade_date", "index_symbol", name="uq_market_index_date_symbol"),
        Index("ix_market_index_kind_date", "index_kind", "trade_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    index_name: Mapped[str] = mapped_column(String(128), nullable=False)
    index_symbol: Mapped[str] = mapped_column(String(128), nullable=False)
    index_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    open_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    high_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    low_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    close_price: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    previous_close: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    change_pct: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    raw_source: Mapped[str] = mapped_column(String(64), nullable=False)
    source_artifact_path: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, nullable=False)


class FuturesContractMaster(Base):
    __tablename__ = "futures_contract_master"
    __table_args__ = (
        UniqueConstraint("exchange", "contract_symbol", name="uq_futures_contract_symbol"),
        Index("ix_futures_contract_underlying_expiry", "underlying_symbol", "expiry_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exchange: Mapped[Exchange] = mapped_column(Enum(Exchange), nullable=False)
    contract_symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    underlying_symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    underlying_isin: Mapped[str | None] = mapped_column(String(12))
    instrument_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    lot_size: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, nullable=False)


class FuturesEOD(Base):
    __tablename__ = "futures_eod"
    __table_args__ = (
        UniqueConstraint("contract_id", "trade_date", name="uq_futures_eod_contract_date"),
        Index("ix_futures_eod_trade_date", "trade_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("futures_contract_master.id"), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    open_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    high_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    low_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    close_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    settle_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    volume: Mapped[Decimal | None] = mapped_column(Numeric(24, 4))
    open_interest: Mapped[Decimal | None] = mapped_column(Numeric(24, 4))
    raw_source: Mapped[str] = mapped_column(String(64), nullable=False)
    source_artifact_path: Mapped[str] = mapped_column(String(512), nullable=False)


class ContinuousFutureDaily(Base):
    __tablename__ = "continuous_future_daily"
    __table_args__ = (
        UniqueConstraint("trade_date", "underlying_symbol", "roll_rule", name="uq_cont_future_date_underlying_rule"),
        Index("ix_cont_future_underlying_date", "underlying_symbol", "trade_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    underlying_symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    underlying_isin: Mapped[str | None] = mapped_column(String(12))
    roll_rule: Mapped[str] = mapped_column(String(32), nullable=False)
    contract_symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    open_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    high_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    low_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    close_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    settle_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    volume: Mapped[Decimal | None] = mapped_column(Numeric(24, 4))
    open_interest: Mapped[Decimal | None] = mapped_column(Numeric(24, 4))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, nullable=False)


class OptionsContractMaster(Base):
    __tablename__ = "options_contract_master"
    __table_args__ = (
        UniqueConstraint("exchange", "contract_symbol", name="uq_options_contract_symbol"),
        Index("ix_options_contract_lookup", "underlying_symbol", "expiry_date", "option_type", "strike_price"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exchange: Mapped[Exchange] = mapped_column(Enum(Exchange), nullable=False)
    contract_symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    underlying_symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    underlying_isin: Mapped[str | None] = mapped_column(String(12))
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    strike_price: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    option_type: Mapped[str] = mapped_column(String(8), nullable=False)
    lot_size: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, nullable=False)


class OptionsEOD(Base):
    __tablename__ = "options_eod"
    __table_args__ = (
        UniqueConstraint("contract_id", "trade_date", name="uq_options_eod_contract_date"),
        Index("ix_options_eod_trade_date", "trade_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("options_contract_master.id"), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    open_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    high_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    low_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    close_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    settle_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    volume: Mapped[Decimal | None] = mapped_column(Numeric(24, 4))
    open_interest: Mapped[Decimal | None] = mapped_column(Numeric(24, 4))
    raw_source: Mapped[str] = mapped_column(String(64), nullable=False)
    source_artifact_path: Mapped[str] = mapped_column(String(512), nullable=False)


class ReleaseRecord(Base):
    __tablename__ = "release_record"
    __table_args__ = (
        UniqueConstraint("release_id", name="uq_release_record_release_id"),
        Index("ix_release_profile_date", "release_profile", "as_of_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    release_id: Mapped[str] = mapped_column(String(64), nullable=False)
    release_profile: Mapped[ReleaseProfile] = mapped_column(Enum(ReleaseProfile), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, nullable=False)
    manifest_path: Mapped[str] = mapped_column(String(512), nullable=False)
    signature_path: Mapped[str | None] = mapped_column(String(512))
    quality_report_path: Mapped[str] = mapped_column(String(512), nullable=False)
    lineage_report_path: Mapped[str] = mapped_column(String(512), nullable=False)
    warehouse_sync_status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    ready_state: Mapped[str] = mapped_column(String(32), nullable=False, default="GENERATED")
    dataset_entries: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list)
    consumer_matrix: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
