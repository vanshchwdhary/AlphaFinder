from __future__ import annotations

from stock_scout.config import Settings
from stock_scout.providers.alphavantage_provider import AlphaVantageProvider
from stock_scout.providers.base import FundamentalsProvider, PriceProvider, ProviderError
from stock_scout.providers.kite_provider import KiteProvider
from stock_scout.providers.nsepython_provider import NSEPythonProvider
from stock_scout.providers.yfinance_provider import YFinanceProvider


def create_price_provider(settings: Settings) -> PriceProvider:
    name = (settings.price_provider or "").strip().lower()
    if name in {"yfinance", "yf", "yahoo"}:
        return YFinanceProvider()
    if name in {"alphavantage", "alpha_vantage", "av"}:
        if not settings.alphavantage_api_key:
            raise ProviderError("Alpha Vantage requires STOCK_SCOUT_ALPHAVANTAGE_API_KEY")
        return AlphaVantageProvider(api_key=settings.alphavantage_api_key)
    if name in {"kite", "kiteconnect"}:
        if not settings.kite_api_key or not settings.kite_access_token:
            raise ProviderError("Kite requires STOCK_SCOUT_KITE_API_KEY and STOCK_SCOUT_KITE_ACCESS_TOKEN")
        return KiteProvider(api_key=settings.kite_api_key, access_token=settings.kite_access_token)
    if name in {"nsepython", "nse"}:
        return NSEPythonProvider()
    raise ProviderError(f"Unknown price provider: {settings.price_provider}")


def create_fundamentals_provider(settings: Settings) -> FundamentalsProvider:
    name = (settings.fundamentals_provider or "").strip().lower()
    if name in {"yfinance", "yf", "yahoo"}:
        return YFinanceProvider()
    if name in {"alphavantage", "alpha_vantage", "av"}:
        if not settings.alphavantage_api_key:
            raise ProviderError("Alpha Vantage requires STOCK_SCOUT_ALPHAVANTAGE_API_KEY")
        return AlphaVantageProvider(api_key=settings.alphavantage_api_key)
    if name in {"kite", "kiteconnect"}:
        if not settings.kite_api_key or not settings.kite_access_token:
            raise ProviderError("Kite requires STOCK_SCOUT_KITE_API_KEY and STOCK_SCOUT_KITE_ACCESS_TOKEN")
        return KiteProvider(api_key=settings.kite_api_key, access_token=settings.kite_access_token)
    if name in {"nsepython", "nse"}:
        return NSEPythonProvider()
    raise ProviderError(f"Unknown fundamentals provider: {settings.fundamentals_provider}")

