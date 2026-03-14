from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Equity(Base):
    __tablename__ = "equities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    exchange: Mapped[str] = mapped_column(String(8), nullable=False)  # NSE / BSE
    name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    isin: Mapped[str | None] = mapped_column(String(16), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(128), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(128), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="INR")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    prices: Mapped[list["PriceBar"]] = relationship(back_populates="equity")
    fundamentals: Mapped[list["FundamentalsSnapshot"]] = relationship(back_populates="equity")
    signals: Mapped[list["Signal"]] = relationship(back_populates="equity")

    __table_args__ = (UniqueConstraint("symbol", "exchange", name="uq_equities_symbol_exchange"),)


class PriceBar(Base):
    __tablename__ = "price_bars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    equity_id: Mapped[int] = mapped_column(ForeignKey("equities.id", ondelete="CASCADE"), index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    open: Mapped[float | None] = mapped_column(Float, nullable=True)
    high: Mapped[float | None] = mapped_column(Float, nullable=True)
    low: Mapped[float | None] = mapped_column(Float, nullable=True)
    close: Mapped[float | None] = mapped_column(Float, nullable=True)
    adj_close: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    source: Mapped[str] = mapped_column(String(32), nullable=False, default="yfinance")
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    equity: Mapped["Equity"] = relationship(back_populates="prices")

    __table_args__ = (UniqueConstraint("equity_id", "date", "source", name="uq_price_bars"),)


class FundamentalsSnapshot(Base):
    __tablename__ = "fundamentals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    equity_id: Mapped[int] = mapped_column(ForeignKey("equities.id", ondelete="CASCADE"), index=True)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    pe: Mapped[float | None] = mapped_column(Float, nullable=True)
    eps: Mapped[float | None] = mapped_column(Float, nullable=True)
    revenue_growth_yoy: Mapped[float | None] = mapped_column(Float, nullable=True)
    debt_to_equity: Mapped[float | None] = mapped_column(Float, nullable=True)
    market_cap: Mapped[float | None] = mapped_column(Float, nullable=True)

    source: Mapped[str] = mapped_column(String(32), nullable=False, default="yfinance")
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    equity: Mapped["Equity"] = relationship(back_populates="fundamentals")

    __table_args__ = (UniqueConstraint("equity_id", "as_of_date", "source", name="uq_fundamentals"),)


class ModelArtifact(Base):
    __tablename__ = "model_artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_name: Mapped[str] = mapped_column(String(64), nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    features: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    metrics: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    artifact_path: Mapped[str] = mapped_column(String(512), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (UniqueConstraint("model_name", "model_version", name="uq_model_artifacts"),)


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    equity_id: Mapped[int] = mapped_column(ForeignKey("equities.id", ondelete="CASCADE"), index=True)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False, default=20)

    model_name: Mapped[str] = mapped_column(String(64), nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)

    predicted_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    predicted_prob_up: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "equity_id",
            "as_of_date",
            "horizon_days",
            "model_name",
            "model_version",
            name="uq_predictions",
        ),
    )


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    equity_id: Mapped[int] = mapped_column(ForeignKey("equities.id", ondelete="CASCADE"), index=True)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    drop_period_days: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False, default=60)

    # price features
    return_1d: Mapped[float | None] = mapped_column(Float, nullable=True)
    return_5d: Mapped[float | None] = mapped_column(Float, nullable=True)
    return_20d: Mapped[float | None] = mapped_column(Float, nullable=True)
    return_60d: Mapped[float | None] = mapped_column(Float, nullable=True)
    drawdown_252: Mapped[float | None] = mapped_column(Float, nullable=True)

    # indicators
    rsi: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd_signal: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd_hist: Mapped[float | None] = mapped_column(Float, nullable=True)
    ma20: Mapped[float | None] = mapped_column(Float, nullable=True)
    ma50: Mapped[float | None] = mapped_column(Float, nullable=True)
    ma200: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume_z: Mapped[float | None] = mapped_column(Float, nullable=True)

    # scoring
    fundamentals_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    technical_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    drop_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    label: Mapped[str] = mapped_column(String(16), nullable=False, default="Watchlist")
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    equity: Mapped["Equity"] = relationship(back_populates="signals")

    __table_args__ = (
        UniqueConstraint(
            "equity_id",
            "as_of_date",
            "drop_period_days",
            "horizon_days",
            name="uq_signals",
        ),
    )

