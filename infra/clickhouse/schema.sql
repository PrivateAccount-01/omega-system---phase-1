CREATE DATABASE IF NOT EXISTS omegadata;

CREATE TABLE IF NOT EXISTS omegadata.price_record
(
    isin String,
    exchange String,
    trade_date Date,
    open_price Float64,
    high_price Float64,
    low_price Float64,
    close_price Float64,
    volume Float64,
    adjusted_close_price Nullable(Float64),
    adjusted_volume Nullable(Float64),
    confidence_score Float32,
    source String,
    ingested_at DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(trade_date)
ORDER BY (isin, exchange, trade_date);

CREATE TABLE IF NOT EXISTS omegadata.validation_audit_log
(
    validation_date DateTime,
    source_1 String,
    source_2 String,
    isin Nullable(String),
    data_date Nullable(Date),
    field_compared String,
    source_1_value String,
    source_2_value String,
    difference_absolute Float64,
    difference_pct Float64,
    tolerance_applied Float64,
    result String,
    resolution_status String,
    resolution_notes Nullable(String)
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(validation_date)
ORDER BY (source_1, source_2, isin, data_date, field_compared);
