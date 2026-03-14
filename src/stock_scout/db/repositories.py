from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
from sqlalchemy import Select, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from stock_scout.db.models import Equity, FundamentalsSnapshot, ModelArtifact, Prediction, PriceBar, Signal


def ensure_equity(session: Session, symbol: str, exchange: str, name: str | None = None) -> Equity:
    symbol = symbol.strip().upper()
    exchange = exchange.strip().upper()
    existing = session.execute(
        select(Equity).where(Equity.symbol == symbol, Equity.exchange == exchange)
    ).scalar_one_or_none()
    if existing:
        if name and existing.name != name:
            existing.name = name
        return existing
    equity = Equity(symbol=symbol, exchange=exchange, name=name)
    session.add(equity)
    session.flush()  # assign id
    return equity


def _upsert_many(
    session: Session,
    model,
    rows: list[dict[str, Any]],
    index_elements: list,
    update_columns: list[str],
) -> None:
    if not rows:
        return
    dialect = session.get_bind().dialect.name
    if dialect == "sqlite":
        stmt = sqlite_insert(model).values(rows)
        set_ = {c: getattr(stmt.excluded, c) for c in update_columns}
        stmt = stmt.on_conflict_do_update(index_elements=index_elements, set_=set_)
        session.execute(stmt)
        return
    if dialect in {"postgresql", "postgres"}:
        stmt = pg_insert(model).values(rows)
        set_ = {c: getattr(stmt.excluded, c) for c in update_columns}
        stmt = stmt.on_conflict_do_update(index_elements=index_elements, set_=set_)
        session.execute(stmt)
        return

    # fallback: merge row-by-row (slower)
    for row in rows:
        session.merge(model(**row))


def upsert_price_bars(
    session: Session,
    *,
    equity_id: int,
    df: pd.DataFrame,
    source: str,
) -> None:
    # expected cols: date, open, high, low, close, adj_close, volume
    records: list[dict[str, Any]] = []
    for r in df.itertuples(index=False):
        d = r.date
        if isinstance(d, pd.Timestamp):
            d = d.date()
        records.append(
            {
                "equity_id": equity_id,
                "date": d,
                "open": _to_float(r.open),
                "high": _to_float(r.high),
                "low": _to_float(r.low),
                "close": _to_float(r.close),
                "adj_close": _to_float(getattr(r, "adj_close", None)),
                "volume": _to_int(getattr(r, "volume", None)),
                "source": source,
            }
        )

    _upsert_many(
        session,
        PriceBar,
        records,
        index_elements=[PriceBar.equity_id, PriceBar.date, PriceBar.source],
        update_columns=["open", "high", "low", "close", "adj_close", "volume"],
    )


def upsert_fundamentals(
    session: Session,
    *,
    equity_id: int,
    as_of_date: date,
    metrics: dict[str, Any],
    source: str,
) -> None:
    row = {
        "equity_id": equity_id,
        "as_of_date": as_of_date,
        "pe": _to_float(metrics.get("pe")),
        "eps": _to_float(metrics.get("eps")),
        "revenue_growth_yoy": _to_float(metrics.get("revenue_growth_yoy")),
        "debt_to_equity": _to_float(metrics.get("debt_to_equity")),
        "market_cap": _to_float(metrics.get("market_cap")),
        "payload": metrics.get("payload"),
        "source": source,
    }

    _upsert_many(
        session,
        FundamentalsSnapshot,
        [row],
        index_elements=[FundamentalsSnapshot.equity_id, FundamentalsSnapshot.as_of_date, FundamentalsSnapshot.source],
        update_columns=[
            "pe",
            "eps",
            "revenue_growth_yoy",
            "debt_to_equity",
            "market_cap",
            "payload",
        ],
    )


def upsert_signal(session: Session, *, row: dict[str, Any]) -> None:
    update_columns = [
        k
        for k in row.keys()
        if k
        not in {"equity_id", "as_of_date", "drop_period_days", "horizon_days"}
    ]
    _upsert_many(
        session,
        Signal,
        [row],
        index_elements=[Signal.equity_id, Signal.as_of_date, Signal.drop_period_days, Signal.horizon_days],
        update_columns=update_columns,
    )


def upsert_prediction(session: Session, *, row: dict[str, Any]) -> None:
    update_columns = [
        k
        for k in row.keys()
        if k not in {"equity_id", "as_of_date", "horizon_days", "model_name", "model_version"}
    ]
    _upsert_many(
        session,
        Prediction,
        [row],
        index_elements=[
            Prediction.equity_id,
            Prediction.as_of_date,
            Prediction.horizon_days,
            Prediction.model_name,
            Prediction.model_version,
        ],
        update_columns=update_columns,
    )


def upsert_model_artifact(session: Session, *, row: dict[str, Any]) -> None:
    _upsert_many(
        session,
        ModelArtifact,
        [row],
        index_elements=[ModelArtifact.model_name, ModelArtifact.model_version],
        update_columns=[
            k for k in row.keys() if k not in {"model_name", "model_version"}
        ],
    )


def latest_prices_query(equity_id: int, limit: int = 260) -> Select:
    return (
        select(PriceBar)
        .where(PriceBar.equity_id == equity_id)
        .order_by(PriceBar.date.desc())
        .limit(limit)
    )


def get_latest_fundamentals(session: Session, equity_id: int) -> FundamentalsSnapshot | None:
    return session.execute(
        select(FundamentalsSnapshot)
        .where(FundamentalsSnapshot.equity_id == equity_id)
        .order_by(FundamentalsSnapshot.as_of_date.desc())
        .limit(1)
    ).scalar_one_or_none()


def get_latest_prediction(
    session: Session, equity_id: int, *, horizon_days: int, model_name: str | None = None
) -> Prediction | None:
    q = select(Prediction).where(
        Prediction.equity_id == equity_id,
        Prediction.horizon_days == horizon_days,
    )
    if model_name:
        q = q.where(Prediction.model_name == model_name)
    q = q.order_by(Prediction.as_of_date.desc()).limit(1)
    return session.execute(q).scalar_one_or_none()


def list_equities(session: Session) -> list[Equity]:
    return list(session.execute(select(Equity).order_by(Equity.exchange, Equity.symbol)).scalars())


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


def _to_int(x: Any) -> int | None:
    if x is None:
        return None
    try:
        if pd.isna(x):
            return None
    except Exception:
        pass
    try:
        return int(x)
    except Exception:
        try:
            return int(float(x))
        except Exception:
            return None
