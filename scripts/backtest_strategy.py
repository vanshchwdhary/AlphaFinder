from __future__ import annotations

"""
Very simple research/backtest harness.

Idea: for each signal date, buy the top-N by total_score (label != Avoid),
hold for horizon_days, compute forward returns.

This is *not* a production-grade backtester (no slippage, liquidity, taxes).
Use it to validate whether your scoring is directionally useful.
"""

import argparse
from datetime import date, timedelta

import pandas as pd
from sqlalchemy import create_engine, text

from stock_scout.config import Settings


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top-n", type=int, default=5)
    ap.add_argument("--horizon-days", type=int, default=20)
    ap.add_argument("--drop-days", type=int, default=20)
    args = ap.parse_args()

    settings = Settings()
    engine = create_engine(settings.database_url, future=True)

    signals_q = text(
        """
        SELECT s.equity_id, s.as_of_date, s.total_score, s.label
        FROM signals s
        WHERE s.drop_period_days = :drop_days
        ORDER BY s.as_of_date ASC, s.total_score DESC
        """
    )
    prices_q = text(
        """
        SELECT equity_id, date, close
        FROM price_bars
        """
    )

    with engine.connect() as conn:
        signals = pd.read_sql(signals_q, conn, params={"drop_days": args.drop_days})
        prices = pd.read_sql(prices_q, conn)

    if signals.empty or prices.empty:
        raise SystemExit("Missing signals or prices. Run ingestion + generate-signals first.")

    signals["as_of_date"] = pd.to_datetime(signals["as_of_date"]).dt.date
    prices["date"] = pd.to_datetime(prices["date"]).dt.date

    # forward return per equity/date
    prices = prices.sort_values(["equity_id", "date"])
    prices["fwd_close"] = prices.groupby("equity_id")["close"].shift(-args.horizon_days)
    prices["fwd_ret"] = prices["fwd_close"] / prices["close"] - 1.0

    # choose top-N each date
    chosen = (
        signals[signals["label"] != "Avoid"]
        .sort_values(["as_of_date", "total_score"], ascending=[True, False])
        .groupby("as_of_date")
        .head(args.top_n)
    )

    merged = chosen.merge(prices, left_on=["equity_id", "as_of_date"], right_on=["equity_id", "date"], how="left")
    merged = merged.dropna(subset=["fwd_ret"])
    if merged.empty:
        raise SystemExit("No forward returns available (need more future data past signal dates).")

    summary = merged.groupby("as_of_date")["fwd_ret"].mean().rename("avg_fwd_ret").reset_index()
    print("Backtest summary")
    print(summary.tail(20).to_string(index=False))
    print("\nOverall:")
    print(f"n_trades={len(merged)} avg_fwd_ret={merged['fwd_ret'].mean():.4f} median={merged['fwd_ret'].median():.4f}")


if __name__ == "__main__":
    main()

