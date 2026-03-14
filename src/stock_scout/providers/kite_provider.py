from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from stock_scout.providers.base import Fundamentals, FundamentalsProvider, PriceProvider, ProviderError


@dataclass(frozen=True)
class KiteProvider(PriceProvider, FundamentalsProvider):
    """
    Zerodha Kite Connect can provide near real-time data, but requires an account,
    API key, and access token. Keep this provider optional.
    """

    api_key: str
    access_token: str

    def __post_init__(self) -> None:
        try:
            from kiteconnect import KiteConnect  # noqa: F401
        except Exception as e:  # pragma: no cover
            raise ProviderError(
                "kiteconnect is not installed. Install it separately if you want to use this provider."
            ) from e

    def fetch_daily_prices(
        self,
        *,
        symbol: str,
        exchange: str,
        start: date,
        end: date | None,
    ) -> pd.DataFrame:
        raise ProviderError("KiteProvider.fetch_daily_prices not implemented (provider is optional).")

    def fetch_fundamentals(self, *, symbol: str, exchange: str) -> Fundamentals:
        raise ProviderError("KiteProvider.fetch_fundamentals not implemented (provider is optional).")

