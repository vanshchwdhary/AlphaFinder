from __future__ import annotations

import pandas as pd


def add_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ma20"] = out["close"].rolling(20, min_periods=20).mean()
    out["ma50"] = out["close"].rolling(50, min_periods=50).mean()
    out["ma200"] = out["close"].rolling(200, min_periods=200).mean()
    return out


def add_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Wilder's RSI implementation.
    """
    out = df.copy()
    delta = out["close"].diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)

    # Wilder smoothing uses EMA with alpha=1/period
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0.0, pd.NA)
    out["rsi"] = 100.0 - (100.0 / (1.0 + rs))
    return out


def add_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    out = df.copy()
    ema_fast = out["close"].ewm(span=fast, adjust=False, min_periods=fast).mean()
    ema_slow = out["close"].ewm(span=slow, adjust=False, min_periods=slow).mean()
    macd = ema_fast - ema_slow
    macd_signal = macd.ewm(span=signal, adjust=False, min_periods=signal).mean()
    out["macd"] = macd
    out["macd_signal"] = macd_signal
    out["macd_hist"] = macd - macd_signal
    return out


def add_volume_zscore(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    out = df.copy()
    vol = out["volume"].astype("float")
    mu = vol.rolling(window, min_periods=window).mean()
    sigma = vol.rolling(window, min_periods=window).std(ddof=0)
    out["volume_z"] = (vol - mu) / sigma.replace(0.0, pd.NA)
    return out


def add_indicators(
    df: pd.DataFrame,
    *,
    rsi_period: int = 14,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
) -> pd.DataFrame:
    out = df.copy()
    out = add_moving_averages(out)
    out = add_rsi(out, period=rsi_period)
    out = add_macd(out, fast=macd_fast, slow=macd_slow, signal=macd_signal)
    out = add_volume_zscore(out, window=20)
    return out

