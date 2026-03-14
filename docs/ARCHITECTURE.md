# System architecture

## Components
- **CLI / Jobs** (`stock-scout`, `scripts/*.py`)
  - Ingest prices + fundamentals
  - Train/predict (optional ML)
  - Generate signals + ranks
  - Send alerts (optional)
- **Providers** (`src/stock_scout/providers/`)
  - `yfinance` (daily; easiest)
  - optional: `alphavantage`, `nsepython`, `kiteconnect`
- **Database** (`src/stock_scout/db/`)
  - SQLite for local dev
  - Postgres/TimescaleDB for scale + concurrency
- **Analysis** (`src/stock_scout/analysis/`)
  - Indicators + feature engineering
  - Scoring + labeling + rationale generation
- **AI** (`src/stock_scout/ai/`)
  - Feature dataset builder
  - Baseline ML model (predict forward returns)
- **Dashboard** (`src/stock_scout/dashboard/streamlit_app.py`)
  - Ranked picks, filters, and basic charts

## Data flow (daily)
1) Universe → providers → `price_bars`, `fundamentals`
2) (Optional) ML predicts → `predictions`
3) Features + scoring → `signals`
4) Dashboard/alerts read → `signals` (and related tables)

