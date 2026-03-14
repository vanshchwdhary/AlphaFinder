from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import pandas as pd
import requests

from stock_scout.providers.base import Fundamentals, FundamentalsProvider, PriceProvider, ProviderError


@dataclass(frozen=True)
class AlphaVantageProvider(PriceProvider, FundamentalsProvider):
    """
    Alpha Vantage coverage for Indian equities varies by symbol format and plan.
    Keep this provider as an optional/experimental source.
    """

    api_key: str

    def fetch_daily_prices(
        self,
        *,
        symbol: str,
        exchange: str,
        start: date,
        end: date | None,
    ) -> pd.DataFrame:
        # NOTE: symbol format differs by Alpha Vantage dataset; you may need to adapt.
        av_symbol = symbol.strip().upper()
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "TIME_SERIES_DAILY_ADJUSTED",
            "symbol": av_symbol,
            "outputsize": "full",
            "apikey": self.api_key,
        }
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        payload = r.json()
        ts = payload.get("Time Series (Daily)")
        if not ts:
            raise ProviderError(f"Alpha Vantage returned no daily series for symbol={av_symbol}: {payload.get('Note') or payload.get('Error Message')}")

        rows: list[dict[str, Any]] = []
        for ds, v in ts.items():
            d = date.fromisoformat(ds)
            if d < start:
                continue
            if end and d > end:
                continue
            rows.append(
                {
                    "date": d,
                    "open": float(v.get("1. open")) if v.get("1. open") else None,
                    "high": float(v.get("2. high")) if v.get("2. high") else None,
                    "low": float(v.get("3. low")) if v.get("3. low") else None,
                    "close": float(v.get("4. close")) if v.get("4. close") else None,
                    "adj_close": float(v.get("5. adjusted close")) if v.get("5. adjusted close") else None,
                    "volume": int(float(v.get("6. volume"))) if v.get("6. volume") else None,
                }
            )
        df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
        return df

    def fetch_fundamentals(self, *, symbol: str, exchange: str) -> Fundamentals:
        av_symbol = symbol.strip().upper()
        url = "https://www.alphavantage.co/query"
        params = {"function": "OVERVIEW", "symbol": av_symbol, "apikey": self.api_key}
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        payload = r.json()
        if not payload or "Symbol" not in payload:
            raise ProviderError(f"Alpha Vantage returned no overview for symbol={av_symbol}")

        return Fundamentals(
            as_of_date=date.today(),
            pe=_to_float(payload.get("PERatio")),
            eps=_to_float(payload.get("EPS")),
            revenue_growth_yoy=None,
            debt_to_equity=None,
            market_cap=_to_float(payload.get("MarketCapitalization")),
            payload=payload,
        )


def _to_float(x: Any) -> float | None:
    if x is None:
        return None
    try:
        return float(x)
    except Exception:
        return None

