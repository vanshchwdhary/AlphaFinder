from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class FundamentalMetrics:
    pe: float | None
    eps: float | None
    revenue_growth_yoy: float | None
    debt_to_equity: float | None
    market_cap: float | None


@dataclass(frozen=True)
class ScoreResult:
    fundamentals_score: float
    technical_score: float
    drop_score: float
    ai_score: float | None
    total_score: float
    label: str
    red_flags: list[str]
    rationale: str


def score_stock(
    *,
    df: pd.DataFrame,
    fundamentals: FundamentalMetrics | None,
    predicted_return: float | None,
    drop_period_days: int,
    score_buy_threshold: float,
    score_watch_threshold: float,
) -> ScoreResult:
    if df.empty:
        raise ValueError("Empty price dataframe")

    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else last

    red_flags: list[str] = []

    fundamentals_score = _score_fundamentals(fundamentals, red_flags)
    technical_score = _score_technicals(last, prev, red_flags)
    drop_score = _score_drop(last, drop_period_days=drop_period_days)
    if drop_score < 20.0:
        red_flags.append("Not a meaningful pullback")
    ai_score = _score_ai(predicted_return)

    total = 0.35 * fundamentals_score + 0.35 * technical_score + 0.10 * drop_score
    if ai_score is not None:
        total += 0.20 * ai_score
    else:
        # redistribute AI weight to fundamentals+technicals when AI not available
        total += 0.10 * fundamentals_score + 0.10 * technical_score

    label = _label(total, red_flags, score_buy_threshold, score_watch_threshold)
    rationale = _rationale_text(last, fundamentals, predicted_return, total, label, red_flags)

    return ScoreResult(
        fundamentals_score=float(round(fundamentals_score, 2)),
        technical_score=float(round(technical_score, 2)),
        drop_score=float(round(drop_score, 2)),
        ai_score=(float(round(ai_score, 2)) if ai_score is not None else None),
        total_score=float(round(total, 2)),
        label=label,
        red_flags=red_flags,
        rationale=rationale,
    )


def _score_fundamentals(f: FundamentalMetrics | None, red_flags: list[str]) -> float:
    if f is None:
        red_flags.append("Missing fundamentals")
        return 45.0

    # EPS
    eps_score = 50.0
    if f.eps is None:
        red_flags.append("EPS missing")
        eps_score = 45.0
    elif f.eps <= 0:
        red_flags.append("Negative EPS")
        eps_score = 0.0
    else:
        eps_score = 100.0

    # P/E (heuristic; sector-relative is better)
    pe_score = 55.0
    if f.pe is None:
        pe_score = 55.0
    elif f.pe <= 15:
        pe_score = 95.0
    elif f.pe <= 25:
        pe_score = 85.0
    elif f.pe <= 40:
        pe_score = 65.0
    elif f.pe <= 60:
        pe_score = 40.0
    else:
        red_flags.append("Very high P/E")
        pe_score = 15.0

    # Revenue growth YoY (if available)
    growth_score = 50.0
    g = f.revenue_growth_yoy
    if g is None:
        growth_score = 50.0
    elif g >= 0.25:
        growth_score = 100.0
    elif g >= 0.12:
        growth_score = 85.0
    elif g >= 0.05:
        growth_score = 70.0
    elif g >= 0:
        growth_score = 55.0
    else:
        red_flags.append("Negative revenue growth")
        growth_score = 10.0

    # Debt to equity (if available)
    dte_score = 55.0
    dte = f.debt_to_equity
    if dte is None:
        dte_score = 55.0
    elif dte <= 0.3:
        dte_score = 100.0
    elif dte <= 0.7:
        dte_score = 85.0
    elif dte <= 1.2:
        dte_score = 65.0
    elif dte <= 2.0:
        red_flags.append("High leverage")
        dte_score = 35.0
    else:
        red_flags.append("Very high leverage")
        dte_score = 10.0

    # Weighted mix
    return 0.35 * eps_score + 0.25 * pe_score + 0.25 * growth_score + 0.15 * dte_score


def _score_technicals(last: pd.Series, prev: pd.Series, red_flags: list[str]) -> float:
    rsi = _to_float(last.get("rsi"))
    ma50 = _to_float(last.get("ma50"))
    ma200 = _to_float(last.get("ma200"))
    close = _to_float(last.get("close"))
    macd_hist = _to_float(last.get("macd_hist"))
    macd_hist_prev = _to_float(prev.get("macd_hist"))
    ret_1d = _to_float(last.get("return_1d"))
    vol_z = _to_float(last.get("volume_z"))

    # RSI score: prefer 25-45 for "oversold but not broken"
    rsi_score = 45.0
    if rsi is None:
        rsi_score = 45.0
    elif rsi <= 20:
        rsi_score = 75.0
    elif rsi <= 30:
        rsi_score = 100.0
    elif rsi <= 40:
        rsi_score = 85.0
    elif rsi <= 55:
        rsi_score = 60.0
    else:
        rsi_score = 35.0

    # Trend score: MA50 > MA200 indicates longer-term uptrend
    trend_score = 50.0
    if ma50 is None or ma200 is None:
        trend_score = 45.0
    elif ma50 > ma200:
        trend_score = 100.0
    else:
        red_flags.append("Downtrend (MA50 < MA200)")
        trend_score = 10.0

    # Pullback score: price below MA50 but trend still up is a "dip" setup
    pullback_score = 45.0
    if close is None or ma50 is None or ma200 is None:
        pullback_score = 45.0
    elif ma50 > ma200 and close < ma50 and close > ma200 * 0.90:
        pullback_score = 90.0
    elif close < ma200:
        red_flags.append("Price below MA200")
        pullback_score = 15.0
    else:
        pullback_score = 55.0

    # Momentum inflection: MACD histogram improving
    macd_score = 50.0
    if macd_hist is None or macd_hist_prev is None:
        macd_score = 50.0
    elif macd_hist > macd_hist_prev:
        macd_score = 75.0
    else:
        macd_score = 40.0

    # Volume penalty: big volume spike on down day can mean distribution
    volume_penalty = 0.0
    if ret_1d is not None and ret_1d < 0 and vol_z is not None and vol_z >= 2.0:
        volume_penalty = 15.0
        red_flags.append("Down day on volume spike")

    technical = 0.30 * rsi_score + 0.30 * trend_score + 0.25 * pullback_score + 0.15 * macd_score
    return max(0.0, technical - volume_penalty)


def _score_drop(last: pd.Series, *, drop_period_days: int) -> float:
    return_col = {5: "return_5d", 20: "return_20d", 60: "return_60d"}.get(
        int(drop_period_days), "return_20d"
    )
    r = _to_float(last.get(return_col))
    dd = _to_float(last.get("drawdown_252"))

    # Prefer meaningful pullbacks, but cap the benefit.
    drop = 0.0
    if r is not None:
        drop = max(drop, min((-r) / 0.30, 1.0))  # 30% down => 1.0
    if dd is not None:
        drop = max(drop, min((-dd) / 0.40, 1.0))  # 40% off 52w high => 1.0
    return 100.0 * drop


def _score_ai(predicted_return: float | None) -> float | None:
    if predicted_return is None:
        return None
    # map predicted 20d return to 0..100 (very heuristic)
    # -10% => 0, 0% => 50, +10% => 100
    return max(0.0, min((predicted_return + 0.10) / 0.20, 1.0)) * 100.0


def _label(total: float, red_flags: list[str], buy: float, watch: float) -> str:
    if any(x in {"Negative EPS", "Very high leverage"} for x in red_flags):
        return "Avoid"
    if (
        total >= buy
        and "Downtrend (MA50 < MA200)" not in red_flags
        and "Not a meaningful pullback" not in red_flags
    ):
        return "Potential Buy"
    if total >= watch:
        return "Watchlist"
    return "Avoid"


def _rationale_text(
    last: pd.Series,
    fundamentals: FundamentalMetrics | None,
    predicted_return: float | None,
    total: float,
    label: str,
    red_flags: list[str],
) -> str:
    parts: list[str] = []

    r20 = _to_float(last.get("return_20d"))
    rsi = _to_float(last.get("rsi"))
    ma50 = _to_float(last.get("ma50"))
    ma200 = _to_float(last.get("ma200"))

    if r20 is not None:
        parts.append(f"20d return {r20*100:.1f}%")
    if rsi is not None:
        parts.append(f"RSI {rsi:.1f}")
    if ma50 is not None and ma200 is not None:
        parts.append("MA50>MA200" if ma50 > ma200 else "MA50<MA200")

    if fundamentals:
        if fundamentals.pe is not None:
            parts.append(f"P/E {fundamentals.pe:.1f}")
        if fundamentals.eps is not None:
            parts.append(f"EPS {fundamentals.eps:.2f}")
        if fundamentals.revenue_growth_yoy is not None:
            parts.append(f"RevYoY {fundamentals.revenue_growth_yoy*100:.1f}%")
        if fundamentals.debt_to_equity is not None:
            parts.append(f"D/E {fundamentals.debt_to_equity:.2f}")

    if predicted_return is not None:
        parts.append(f"AI {predicted_return*100:.1f}%/{'20d'}")

    if red_flags:
        parts.append("Flags: " + ", ".join(sorted(set(red_flags))))

    parts.append(f"Score {total:.1f} => {label}")
    return " | ".join(parts)


def _to_float(x: Any) -> float | None:
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
