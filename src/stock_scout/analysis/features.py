from __future__ import annotations

import pandas as pd


def add_returns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["return_1d"] = out["close"].pct_change(1)
    out["return_5d"] = out["close"].pct_change(5)
    out["return_20d"] = out["close"].pct_change(20)
    out["return_60d"] = out["close"].pct_change(60)
    return out


def add_drawdowns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    rolling_max_252 = out["close"].rolling(252, min_periods=252).max()
    out["drawdown_252"] = (out["close"] / rolling_max_252) - 1.0
    return out


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out = add_returns(out)
    out = add_drawdowns(out)
    return out

