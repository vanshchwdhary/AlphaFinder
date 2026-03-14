from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from stock_scout.config import Settings, UniverseEntry
from stock_scout.db.models import PriceBar
from stock_scout.db.repositories import ensure_equity, upsert_fundamentals, upsert_price_bars
from stock_scout.providers.factory import create_fundamentals_provider, create_price_provider

logger = logging.getLogger(__name__)


def _default_start() -> date:
    # reasonable default: ~5 years of daily bars
    return (date.today() - timedelta(days=365 * 5))


def ingest_prices(
    session: Session,
    settings: Settings,
    universe: list[UniverseEntry],
    *,
    start: date | None,
    end: date | None,
) -> None:
    provider = create_price_provider(settings)
    for entry in universe:
        equity = ensure_equity(session, entry.symbol, entry.exchange, entry.name)

        effective_start = start or _infer_incremental_start(session, equity.id) or _default_start()
        logger.info(
            "Ingest prices: %s:%s start=%s end=%s",
            entry.exchange,
            entry.symbol,
            effective_start.isoformat(),
            end.isoformat() if end else None,
        )
        try:
            df = provider.fetch_daily_prices(
                symbol=entry.symbol,
                exchange=entry.exchange,
                start=effective_start,
                end=end,
            )
        except Exception:
            logger.exception("Price ingestion failed for %s:%s", entry.exchange, entry.symbol)
            continue

        if df is None or df.empty:
            logger.info("No price rows for %s:%s (already up to date?)", entry.exchange, entry.symbol)
            continue

        upsert_price_bars(session, equity_id=equity.id, df=df, source=settings.price_provider)


def ingest_fundamentals(
    session: Session,
    settings: Settings,
    universe: list[UniverseEntry],
) -> None:
    provider = create_fundamentals_provider(settings)
    today = date.today()
    for entry in universe:
        equity = ensure_equity(session, entry.symbol, entry.exchange, entry.name)
        logger.info("Ingest fundamentals: %s:%s as_of=%s", entry.exchange, entry.symbol, today.isoformat())
        try:
            f = provider.fetch_fundamentals(symbol=entry.symbol, exchange=entry.exchange)
        except Exception:
            logger.exception("Fundamentals ingestion failed for %s:%s", entry.exchange, entry.symbol)
            continue
        upsert_fundamentals(
            session,
            equity_id=equity.id,
            as_of_date=f.as_of_date,
            metrics={
                "pe": f.pe,
                "eps": f.eps,
                "revenue_growth_yoy": f.revenue_growth_yoy,
                "debt_to_equity": f.debt_to_equity,
                "market_cap": f.market_cap,
                "payload": f.payload,
            },
            source=settings.fundamentals_provider,
        )


def _infer_incremental_start(session: Session, equity_id: int) -> date | None:
    last: date | None = session.execute(
        select(func.max(PriceBar.date)).where(PriceBar.equity_id == equity_id)
    ).scalar_one_or_none()
    if not last:
        return None
    # Re-fetch last ingested bar to avoid "empty result" failures when the provider
    # hasn't published the newest day yet. Upserts keep this idempotent.
    return last


def parse_date(d: str | None) -> date | None:
    if not d:
        return None
    return datetime.strptime(d, "%Y-%m-%d").date()
