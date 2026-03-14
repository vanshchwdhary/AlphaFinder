from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import yfinance as yf
from tenacity import retry, stop_after_attempt, wait_exponential

from stock_scout.providers.base import Fundamentals, FundamentalsProvider, PriceProvider, ProviderError


def _yf_symbol(symbol: str, exchange: str) -> str:
    s = symbol.strip().upper()
    ex = exchange.strip().upper()
    if ex == "NSE":
        return f"{s}.NS"
    if ex == "BSE":
        return f"{s}.BO"
    return s


class YFinanceProvider(PriceProvider, FundamentalsProvider):
    @retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(3))
    def fetch_daily_prices(
        self,
        *,
        symbol: str,
        exchange: str,
        start: date,
        end: date | None,
    ) -> pd.DataFrame:
        ticker = _yf_symbol(symbol, exchange)
        df = yf.download(
            tickers=ticker,
            start=start.isoformat(),
            end=(end.isoformat() if end else None),
            interval="1d",
            auto_adjust=False,
            progress=False,
            threads=False,
        )
        if df is None or df.empty:
            raise ProviderError(f"yfinance returned empty data for {ticker}")

        # yfinance may return MultiIndex columns even for a single ticker.
        if isinstance(df.columns, pd.MultiIndex):
            tickers = df.columns.get_level_values(1).unique()
            if len(tickers) == 1:
                df = df.xs(tickers[0], axis=1, level=1, drop_level=True)
            else:
                raise ProviderError(f"Unexpected MultiIndex columns for single ticker={ticker}: {df.columns}")

        df = df.reset_index()
        # yfinance uses "Date" for daily, "Datetime" for intraday. Support both.
        dt_col = "Date" if "Date" in df.columns else ("Datetime" if "Datetime" in df.columns else df.columns[0])
        df = df.rename(
            columns={
                dt_col: "date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Adj Close": "adj_close",
                "Volume": "volume",
            }
        )

        if "adj_close" not in df.columns and "close" in df.columns:
            df["adj_close"] = df["close"]

        df["date"] = pd.to_datetime(df["date"]).dt.date
        keep = ["date", "open", "high", "low", "close", "adj_close", "volume"]
        df = df[keep].dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
        return df

    @retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(3))
    def fetch_fundamentals(self, *, symbol: str, exchange: str) -> Fundamentals:
        ticker = _yf_symbol(symbol, exchange)
        info: dict[str, Any] = yf.Ticker(ticker).info or {}

        pe = info.get("trailingPE") or info.get("forwardPE")
        eps = info.get("trailingEps")
        revenue_growth = info.get("revenueGrowth")
        debt_to_equity = info.get("debtToEquity")
        market_cap = info.get("marketCap")

        return Fundamentals(
            as_of_date=date.today(),
            pe=_as_float(pe),
            eps=_as_float(eps),
            revenue_growth_yoy=_as_float(revenue_growth),
            debt_to_equity=_as_float(debt_to_equity),
            market_cap=_as_float(market_cap),
            payload=info,
        )


def _as_float(x: Any) -> float | None:
    if x is None:
        return None
    try:
        if pd.isna(x):
            return None
    except Exception:
        pass
    try:
        return float(x)
    except Exception:
        return None
