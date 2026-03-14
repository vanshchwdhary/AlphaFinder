# Stock Scout (NSE/BSE)

Personal project to **find Indian stocks that are currently falling** and rank them by **long-term potential** using:
- Price action + technical indicators (RSI/MAs/MACD/volume)
- Fundamentals (P/E, EPS, growth, debt)
- Optional ML return prediction + rule-based financial reasoning

> Not investment advice. This is an analytics project; always validate with your own research.

## Quickstart (local SQLite)

1) Create env + install deps:
```bash
python3 --version  # requires Python 3.10+ (3.11+ recommended)
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dashboard,ai]"
cp .env.example .env
```

2) Initialize DB, ingest data, generate signals:
```bash
stock-scout init-db
stock-scout ingest-prices --start 2019-01-01
stock-scout ingest-fundamentals
stock-scout generate-signals
```

3) Run dashboard:
```bash
streamlit run src/stock_scout/dashboard/streamlit_app.py
```

## Architecture (high level)

- `providers/`: pluggable data sources (`yfinance`, optional `alphavantage`, `nsepython`, `kite`)
- `db/`: SQLAlchemy models + repository upserts
- `analysis/`: indicators, features, scoring, labeling, rule-based reasoning
- `ai/`: baseline ML model to predict forward returns
- `dashboard/`: Streamlit UI

## Deployment (Docker + Postgres)

- Use `docker/docker-compose.yml` for Postgres.
- Run a daily job (cron/GitHub Actions) that executes:
  - `stock-scout ingest-prices`
  - `stock-scout ingest-fundamentals`
  - `stock-scout generate-signals`
  - `stock-scout predict` (optional)
