# “Falling but strong” scoring (rule-based)

## Step 1 — Detect “falling”
Use short/medium lookbacks (5d/20d) and longer context (52-week drawdown):
- `return_5d`, `return_20d`, `drawdown_252`

## Step 2 — Judge if it’s a pullback vs structural weakness

### Technical signals (examples)
- Uptrend: `MA50 > MA200` is a strong filter for long-term strength.
- Dip: `close < MA50` while still above/near `MA200` suggests a pullback.
- Oversold: RSI ~ 25–40 can indicate exhaustion.
- Momentum inflection: improving MACD histogram.
- Risk flag: down day + big volume spike (possible distribution).

### Fundamental checks (examples)
- EPS positive (avoid structurally loss-making unless your strategy is built for it).
- Reasonable P/E (sector-relative is best; the starter uses heuristic thresholds).
- Revenue growth YoY positive.
- Debt/Equity not excessive.

## Step 3 — Rank & label
Compute component scores:
- `fundamentals_score` (EPS, P/E, growth, leverage)
- `technical_score` (trend, pullback, RSI, MACD, volume flags)
- `drop_score` (how meaningful the pullback is)
- `ai_score` (optional ML)

Label:
- `Potential Buy`: high total score + no major red flags + not in downtrend
- `Watchlist`: mixed signals
- `Avoid`: negative EPS / extreme leverage / structural downtrend

All scores/labels are adjustable in `src/stock_scout/analysis/scoring.py`.

