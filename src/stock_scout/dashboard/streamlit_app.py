from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st
from sqlalchemy import text

from stock_scout.analysis.signals import generate_signals
from stock_scout.analysis.features import add_features
from stock_scout.analysis.indicators import add_indicators
from stock_scout.config import Settings
from stock_scout.db.engine import get_engine, session_scope
from stock_scout.db.models import Base
from stock_scout.ingest import ingest_fundamentals, ingest_prices
from stock_scout.universe import load_universe_csv

st.set_page_config(page_title="Stock Scout (NSE/BSE)", layout="wide")


@st.cache_resource
def _engine(db_url: str):
    return get_engine(db_url)


@st.cache_data(ttl=60)
def load_signal_table(db_url: str, *, drop_days: int, horizon_days: int) -> pd.DataFrame:
    engine = _engine(db_url)
    q = text(
        """
        SELECT
          s.as_of_date,
          s.label,
          s.total_score,
          s.fundamentals_score,
          s.technical_score,
          s.ai_score,
          s.drop_score,
          s.return_5d,
          s.return_20d,
          s.drawdown_252,
          s.rsi,
          e.exchange,
          e.symbol,
          e.name,
          s.rationale,
          e.id AS equity_id
        FROM signals s
        JOIN equities e ON e.id = s.equity_id
        WHERE s.drop_period_days = :drop_days AND s.horizon_days = :horizon_days
          AND s.as_of_date = (
            SELECT MAX(as_of_date) FROM signals
            WHERE drop_period_days = :drop_days AND horizon_days = :horizon_days
          )
        ORDER BY s.total_score DESC
        """
    )
    with engine.connect() as conn:
        df = pd.read_sql(q, conn, params={"drop_days": drop_days, "horizon_days": horizon_days})
    return df


@st.cache_data(ttl=60)
def load_price_history(db_url: str, equity_id: int, limit: int = 260) -> pd.DataFrame:
    engine = _engine(db_url)
    q = text(
        """
        SELECT date, close, volume
        FROM price_bars
        WHERE equity_id = :equity_id
        ORDER BY date DESC
        LIMIT :limit
        """
    )
    with engine.connect() as conn:
        df = pd.read_sql(q, conn, params={"equity_id": equity_id, "limit": limit})
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df = df.sort_values("date").reset_index(drop=True)
    return df


def bootstrap_data(settings: Settings, *, drop_days: int, horizon_days: int) -> None:
    engine = get_engine(settings.database_url)
    Base.metadata.create_all(bind=engine)
    universe = load_universe_csv(settings.universe_path)
    start = date.today() - timedelta(days=365 * 3)

    with session_scope(settings.database_url) as session:
        ingest_prices(session, settings, universe, start=start, end=None)
        ingest_fundamentals(session, settings, universe)
        generate_signals(session, settings, drop_period_days=drop_days, horizon_days=horizon_days)


def main() -> None:
    settings = Settings()

    st.title("Stock Scout (NSE/BSE)")
    st.caption("Find falling stocks with strong long-term potential (rules + fundamentals + optional ML).")

    with st.sidebar:
        st.header("Filters")
        drop_days = st.number_input("Drop lookback (days)", min_value=5, max_value=120, value=20, step=5)
        horizon_days = st.number_input("Horizon (days)", min_value=20, max_value=252, value=60, step=10)
        min_score = st.slider("Min score", min_value=0, max_value=100, value=55)
        labels = st.multiselect(
            "Labels",
            options=["Potential Buy", "Watchlist", "Avoid"],
            default=["Potential Buy", "Watchlist"],
        )
        if st.button("Refresh data now", type="primary"):
            with st.spinner("Fetching prices + fundamentals and generating signals..."):
                bootstrap_data(settings, drop_days=drop_days, horizon_days=horizon_days)
            st.cache_data.clear()
            st.rerun()

    signals = load_signal_table(settings.database_url, drop_days=drop_days, horizon_days=horizon_days)
    if signals.empty:
        st.warning("No signals found in the database yet.")
        if st.button("Bootstrap database (download data + generate signals)"):
            with st.spinner("Bootstrapping (first run can take a minute)..."):
                bootstrap_data(settings, drop_days=drop_days, horizon_days=horizon_days)
            st.cache_data.clear()
            st.rerun()
        st.stop()

    filt = (signals["total_score"] >= float(min_score)) & (signals["label"].isin(labels))
    view = signals.loc[filt].copy()

    st.subheader("Ranked Opportunities")
    st.dataframe(
        view[
            [
                "exchange",
                "symbol",
                "name",
                "label",
                "total_score",
                "return_20d",
                "drawdown_252",
                "rsi",
                "fundamentals_score",
                "technical_score",
                "ai_score",
                "rationale",
            ]
        ],
        width="stretch",
        hide_index=True,
    )

    st.divider()
    st.subheader("Stock Detail")
    options = view[["symbol", "exchange", "equity_id"]].drop_duplicates().to_dict(orient="records")
    if not options:
        st.info("Adjust filters to see stocks.")
        return

    selected = st.selectbox(
        "Select a stock",
        options,
        format_func=lambda x: f"{x['exchange']}:{x['symbol']}",
    )
    eq_id = int(selected["equity_id"])

    price_df = load_price_history(settings.database_url, eq_id, limit=400)
    if price_df.empty:
        st.warning("No price history found for selection.")
        return

    price_df = add_indicators(
        price_df,
        rsi_period=settings.rsi_period,
        macd_fast=settings.macd_fast,
        macd_slow=settings.macd_slow,
        macd_signal=settings.macd_signal,
    )
    price_df = add_features(price_df)

    st.line_chart(price_df.set_index("date")[["close", "ma50", "ma200"]].dropna(), height=320)
    st.line_chart(price_df.set_index("date")[["rsi"]].dropna(), height=180)


if __name__ == "__main__":
    main()
