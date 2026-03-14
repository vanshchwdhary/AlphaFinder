from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="STOCK_SCOUT_", env_file=".env", extra="ignore")

    # storage
    database_url: str = "sqlite:///./stock_scout.db"

    # providers
    price_provider: str = "yfinance"
    fundamentals_provider: str = "yfinance"
    alphavantage_api_key: Optional[str] = None
    kite_api_key: Optional[str] = None
    kite_access_token: Optional[str] = None

    # universe
    universe_path: str = "./data/universe_sample.csv"

    # analysis defaults
    rsi_period: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9

    drop_days_short: int = 5
    drop_days_medium: int = 20
    drop_days_long: int = 60

    # label thresholds
    score_buy_threshold: float = 70.0
    score_watch_threshold: float = 55.0

    # AI (optional; requires installing extras: `pip install -e ".[ai]"`)
    ai_horizon_days: int = 20
    ai_model_name: str = "hgb"
    ai_model_version: str = "v1"
    artifacts_dir: str = "./artifacts"

    # alerts (optional)
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    discord_webhook_url: Optional[str] = None


@dataclass(frozen=True)
class UniverseEntry:
    symbol: str
    exchange: str
    name: Optional[str] = None
