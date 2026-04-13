from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="OMEGA_", extra="ignore")

    env: str = "dev"
    db_url: str = "postgresql+psycopg://omega:omega@localhost:5432/omegadata"
    parquet_root: str = "./data/parquet"
    raw_root: str = "./data/raw"
    report_root: str = "./data/reports"
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 8123
    clickhouse_user: str = "default"
    clickhouse_password: str = ""
    kafka_bootstrap: str = "localhost:9092"
    redis_url: str = "redis://localhost:6379/0"
    alert_webhook_url: str = ""
    alert_min_severity: str = "WARN"
    api_key: str = Field(default="change-me", min_length=8)
    market_proxy_isin: str = ""
    quarterly_validation_pack: str = "./artifacts/verification/quarterly_validation_input.json"
    review_policy_path: str = "./config/review_policies.json"
    cross_source_tolerance_policy_path: str = "./config/cross_source_tolerance_policy.json"
    corporate_action_matching_policy_path: str = "./config/corporate_action_matching_policy.json"
    release_readiness_policy_path: str = "./config/release_readiness_policy.json"
    trading_holiday_path: str = "./config/trading_holidays_india.json"
    trading_calendar_warning_window_days: int = 60
    source_probe_profile_mode: str = "deterministic"
    source_probe_timeout_seconds: float = 8.0
    reprocess_root: str = "./artifacts/reprocess_queue"
    probe_history_days: int = 3


settings = Settings()
