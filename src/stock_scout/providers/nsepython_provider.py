from __future__ import annotations

from datetime import date

import pandas as pd

from stock_scout.providers.base import Fundamentals, FundamentalsProvider, PriceProvider, ProviderError


class NSEPythonProvider(PriceProvider, FundamentalsProvider):
    """
    Uses the `nsepython` package (web-scraping based). This may break if NSE changes
    its endpoints or blocks automated clients. Prefer official APIs for production.
    """

    def __init__(self) -> None:
        try:
            import nsepython  # noqa: F401
        except Exception as e:  # pragma: no cover
            raise ProviderError(
                "nsepython is not installed. Install it separately if you want to use this provider."
            ) from e

    def fetch_daily_prices(
        self,
        *,
        symbol: str,
        exchange: str,
        start: date,
        end: date | None,
    ) -> pd.DataFrame:
        raise ProviderError("NSEPythonProvider.fetch_daily_prices not implemented (provider is optional).")

    def fetch_fundamentals(self, *, symbol: str, exchange: str) -> Fundamentals:
        raise ProviderError("NSEPythonProvider.fetch_fundamentals not implemented (provider is optional).")

