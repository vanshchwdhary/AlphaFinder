# Database design

This project uses SQLAlchemy ORM models in `src/stock_scout/db/models.py`.

## Core tables

### `equities`
- One row per stock (symbol + exchange).

### `price_bars`
- Daily OHLCV history.
- Unique per `(equity_id, date, source)`.

### `fundamentals`
- Snapshot of key metrics (P/E, EPS, growth, debt, market cap).
- Stores raw provider payload JSON for audit/debug.

### `signals`
- The output of your “falling but strong” algorithm for a given date.
- Stores features, component scores, final label, and a human-readable rationale.

### `predictions` (optional)
- Latest ML-predicted forward returns (and probabilities, if used).

### `model_artifacts` (optional)
- Tracks model versions and artifact paths/metrics.

## Scaling notes
- For large universes (NIFTY 500/All EQ), prefer Postgres and consider TimescaleDB.
- Partitioning by `equity_id` and indexing `(equity_id, date)` matters for speed.

