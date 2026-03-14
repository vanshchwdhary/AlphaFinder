from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Any

import pandas as pd


class ProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class Fundamentals:
    as_of_date: date
    pe: float | None
    eps: float | None
    revenue_growth_yoy: float | None
    debt_to_equity: float | None
    market_cap: float | None
    payload: dict[str, Any] | None = None


class PriceProvider(ABC):
    @abstractmethod
    def fetch_daily_prices(
        self,
        *,
        symbol: str,
        exchange: str,
        start: date,
        end: date | None,
    ) -> pd.DataFrame:
        """
        Returns DataFrame with columns:
        date, open, high, low, close, adj_close, volume
        """


class FundamentalsProvider(ABC):
    @abstractmethod
    def fetch_fundamentals(self, *, symbol: str, exchange: str) -> Fundamentals:
        ...

