# Advanced features (ideas)

## AI prediction models
- **Return prediction (baseline included)**: regress forward 20d return from technical features.
- **Classification**: predict probability of outperforming a benchmark (NIFTY) over horizon.
- **Per-sector models**: reduce noise; different regimes behave differently.
- **Ensembling**: blend models (GBDT + linear + momentum).
- **Monitoring**: drift detection + scheduled retraining.

## Financial reasoning (explainability)
- Rule-based tags (already stored in `signals.rationale`).
- Add “evidence” objects:
  - trend: MA50 vs MA200
  - pullback depth: drawdown from 52-week high
  - fundamentals: EPS, growth, leverage
- (Optional) LLM summaries of earnings calls/news:
  - store citations/links
  - enforce “no recommendation” language
  - require structured output (risk factors, catalysts, uncertainties)

## Advanced strategy research
- **Backtests**: walk-forward, avoid look-ahead bias.
- **Constraints**: slippage, liquidity (volume), max position size, sector caps.
- **Risk overlays**: volatility targeting, max drawdown control, stop-loss rules.
- **Factor filters**: quality (ROE/ROCE), value, growth, momentum.
- **Regime filters**: market breadth, VIX-like proxies, interest-rate sensitivity.
- **Benchmarking**: compare vs NIFTY 50/500 and a naive “buy the dip” baseline.

## Sentiment analysis (news & social)
- Source: RSS/news APIs; filter for the equity by name/symbol/ISIN.
- Model: transformer sentiment (finBERT-like) or keyword/rule hybrid.
- Store: per-article sentiment and a rolling 7d/30d aggregate feature.

## Portfolio tracking
- Tables: portfolios, holdings, transactions.
- Metrics: P&L, realized/unrealized, exposure, drawdown, attribution.
- Integrate: “signal → watchlist → buy → track”.

## Alerts (Telegram/Discord)
- Daily “Top 10 Potential Buy” summary.
- Optional: thresholds (score >= X, 20d drawdown >= Y, RSI <= Z).
- Alert de-duplication and cool-down windows.

