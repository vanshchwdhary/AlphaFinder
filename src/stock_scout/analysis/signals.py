from __future__ import annotations

import logging
from datetime import date

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from stock_scout.analysis.features import add_features
from stock_scout.analysis.indicators import add_indicators
from stock_scout.analysis.scoring import FundamentalMetrics, score_stock
from stock_scout.config import Settings
from stock_scout.db.models import PriceBar
from stock_scout.db.repositories import (
    get_latest_fundamentals,
    get_latest_prediction,
    list_equities,
    upsert_signal,
)

logger = logging.getLogger(__name__)


def generate_signals(
    session: Session,
    settings: Settings,
    *,
    drop_period_days: int = 20,
    horizon_days: int = 60,
    min_history: int = 220,
) -> None:
    equities = list_equities(session)
    for eq in equities:
        try:
            df = _load_prices(session, eq.id, limit=400)
            if df is None or len(df) < min_history:
                logger.warning("Skipping %s:%s (insufficient history)", eq.exchange, eq.symbol)
                continue

            df = add_indicators(
                df,
                rsi_period=settings.rsi_period,
                macd_fast=settings.macd_fast,
                macd_slow=settings.macd_slow,
                macd_signal=settings.macd_signal,
            )
            df = add_features(df)

            fundamentals_row = get_latest_fundamentals(session, eq.id)
            fundamentals = None
            if fundamentals_row:
                fundamentals = FundamentalMetrics(
                    pe=fundamentals_row.pe,
                    eps=fundamentals_row.eps,
                    revenue_growth_yoy=fundamentals_row.revenue_growth_yoy,
                    debt_to_equity=fundamentals_row.debt_to_equity,
                    market_cap=fundamentals_row.market_cap,
                )

            pred = get_latest_prediction(
                session,
                eq.id,
                horizon_days=settings.ai_horizon_days,
                model_name=settings.ai_model_name,
            )
            predicted_return = pred.predicted_return if pred else None

            scored = score_stock(
                df=df,
                fundamentals=fundamentals,
                predicted_return=predicted_return,
                drop_period_days=drop_period_days,
                score_buy_threshold=settings.score_buy_threshold,
                score_watch_threshold=settings.score_watch_threshold,
            )

            last = df.iloc[-1]
            as_of: date = last["date"]

            row = {
                "equity_id": eq.id,
                "as_of_date": as_of,
                "drop_period_days": drop_period_days,
                "horizon_days": horizon_days,
                "return_1d": _f(last.get("return_1d")),
                "return_5d": _f(last.get("return_5d")),
                "return_20d": _f(last.get("return_20d")),
                "return_60d": _f(last.get("return_60d")),
                "drawdown_252": _f(last.get("drawdown_252")),
                "rsi": _f(last.get("rsi")),
                "macd": _f(last.get("macd")),
                "macd_signal": _f(last.get("macd_signal")),
                "macd_hist": _f(last.get("macd_hist")),
                "ma20": _f(last.get("ma20")),
                "ma50": _f(last.get("ma50")),
                "ma200": _f(last.get("ma200")),
                "volume_z": _f(last.get("volume_z")),
                "fundamentals_score": scored.fundamentals_score,
                "technical_score": scored.technical_score,
                "ai_score": scored.ai_score,
                "drop_score": scored.drop_score,
                "total_score": scored.total_score,
                "label": scored.label,
                "rationale": scored.rationale,
            }

            upsert_signal(session, row=row)
            logger.info(
                "Signal %s:%s => %s (%.1f)", eq.exchange, eq.symbol, scored.label, scored.total_score
            )
        except Exception:
            logger.exception("Signal generation failed for %s:%s", eq.exchange, eq.symbol)
            continue


def _load_prices(session: Session, equity_id: int, limit: int) -> pd.DataFrame | None:
    bars = session.execute(
        select(PriceBar)
        .where(PriceBar.equity_id == equity_id)
        .order_by(PriceBar.date.desc())
        .limit(limit)
    ).scalars().all()
    if not bars:
        return None
    bars = list(reversed(bars))
    df = pd.DataFrame(
        {
            "date": [b.date for b in bars],
            "open": [b.open for b in bars],
            "high": [b.high for b in bars],
            "low": [b.low for b in bars],
            "close": [b.close for b in bars],
            "adj_close": [b.adj_close for b in bars],
            "volume": [b.volume for b in bars],
        }
    )
    df = df.dropna(subset=["date", "close"]).reset_index(drop=True)
    return df


def _f(x) -> float | None:
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
