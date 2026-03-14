from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from stock_scout.analysis.features import add_features
from stock_scout.analysis.indicators import add_indicators
from stock_scout.config import Settings
from stock_scout.db.models import Equity, PriceBar


FEATURE_COLUMNS = [
    "return_1d",
    "return_5d",
    "return_20d",
    "return_60d",
    "drawdown_252",
    "rsi",
    "macd",
    "macd_signal",
    "macd_hist",
    "ma20",
    "ma50",
    "ma200",
    "volume_z",
    "close_to_ma50",
    "close_to_ma200",
    "ma50_to_ma200",
]


@dataclass(frozen=True)
class Dataset:
    X: pd.DataFrame
    y: pd.Series
    meta: pd.DataFrame  # columns: equity_id, date


def build_dataset(
    session: Session,
    settings: Settings,
    *,
    horizon_days: int,
    min_history: int = 260,
) -> Dataset:
    equities = session.execute(select(Equity)).scalars().all()
    frames: list[pd.DataFrame] = []

    for eq in equities:
        df = _load_prices(session, eq.id, limit=1500)
        if df is None or len(df) < min_history:
            continue

        df = add_indicators(
            df,
            rsi_period=settings.rsi_period,
            macd_fast=settings.macd_fast,
            macd_slow=settings.macd_slow,
            macd_signal=settings.macd_signal,
        )
        df = add_features(df)
        df = _add_ratios(df)

        df["target_return"] = df["close"].shift(-horizon_days) / df["close"] - 1.0
        df = df.dropna(subset=FEATURE_COLUMNS + ["target_return"])
        if df.empty:
            continue

        df["equity_id"] = eq.id
        frames.append(df[["equity_id", "date", "target_return"] + FEATURE_COLUMNS])

    if not frames:
        raise ValueError("No training data. Ingest prices first.")

    all_df = pd.concat(frames, ignore_index=True)
    X = all_df[FEATURE_COLUMNS]
    y = all_df["target_return"]
    meta = all_df[["equity_id", "date"]]
    return Dataset(X=X, y=y, meta=meta)


def build_latest_features(
    session: Session,
    settings: Settings,
    *,
    horizon_days: int,
    min_history: int = 260,
) -> pd.DataFrame:
    equities = session.execute(select(Equity)).scalars().all()
    rows: list[dict] = []

    for eq in equities:
        df = _load_prices(session, eq.id, limit=400)
        if df is None or len(df) < min_history:
            continue
        df = add_indicators(
            df,
            rsi_period=settings.rsi_period,
            macd_fast=settings.macd_fast,
            macd_slow=settings.macd_slow,
            macd_signal=settings.macd_signal,
        )
        df = add_features(df)
        df = _add_ratios(df)

        last = df.iloc[-1]
        if last[FEATURE_COLUMNS].isna().any():
            continue
        rows.append({"equity_id": eq.id, "as_of_date": last["date"], **{c: float(last[c]) for c in FEATURE_COLUMNS}})

    if not rows:
        raise ValueError("No feature rows available; check history length and indicators.")
    return pd.DataFrame(rows)


def _add_ratios(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["close_to_ma50"] = out["close"] / out["ma50"] - 1.0
    out["close_to_ma200"] = out["close"] / out["ma200"] - 1.0
    out["ma50_to_ma200"] = out["ma50"] / out["ma200"] - 1.0
    return out


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
            "close": [b.close for b in bars],
            "volume": [b.volume for b in bars],
        }
    )
    df = df.dropna(subset=["date", "close"]).reset_index(drop=True)
    return df

