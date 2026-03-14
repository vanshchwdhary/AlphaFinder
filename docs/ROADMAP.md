# Roadmap

## Phase 0 — Setup
1) Define your universe (NIFTY 50/200/500 or custom list) in `data/universe_*.csv`.
2) Choose storage: start with SQLite; move to Postgres for scale.
3) Pick data sources:
   - Daily analysis: `yfinance` is simplest (delayed/unofficial).
   - Real-time: broker APIs like Zerodha Kite Connect (official, requires account).

## Phase 1 — Data ingestion (daily OHLCV + fundamentals)
1) `stock-scout init-db`
2) `stock-scout ingest-prices --start 2019-01-01` (initial backfill)
3) Schedule daily incremental ingestion: `scripts/run_daily_pipeline.py`
4) Ingest fundamentals snapshots daily/weekly (depends on provider quality)

## Phase 2 — Signals + ranking (rule-based)
1) Compute indicators: RSI, moving averages, MACD, volume z-score
2) Detect pullbacks: negative 5d/20d returns + drawdown from 52w high
3) Fundamentals scoring: EPS, P/E, revenue growth, leverage
4) Create ranked labels:
   - `Potential Buy` (pullback + uptrend + good fundamentals)
   - `Watchlist` (mixed signals)
   - `Avoid` (structural downtrend or weak fundamentals)

## Phase 3 — Financial reasoning (explainability)
1) Generate a rationale string per signal (stored in DB)
2) Add rule-based “why” tags (e.g., `Downtrend`, `High leverage`)
3) (Optional) Add LLM summaries of earnings/news with strict guardrails

## Phase 4 — AI prediction models
1) Baseline supervised model: predict forward 20d return from technical features
2) Walk-forward validation + model registry (versioning)
3) Add predictions into ranking (not replacing fundamentals/technicals)
4) Add drift monitoring + retraining schedule

## Phase 5 — Research & backtesting
1) Backtest simple “top-N by score” portfolio vs. NIFTY benchmark
2) Add transaction costs, slippage, liquidity constraints
3) Compare variants (value vs growth filters, volatility targeting, etc.)

## Phase 6 — Productization
1) Dashboard + alerts (Telegram/Discord)
2) Docker + Postgres + scheduled jobs
3) Add portfolio tracking and performance analytics

