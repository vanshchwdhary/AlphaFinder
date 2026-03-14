from __future__ import annotations

import logging
from datetime import date

import typer
from rich import print

from stock_scout.config import Settings
from stock_scout.analysis.signals import generate_signals
from stock_scout.db.engine import get_engine, session_scope
from stock_scout.db.models import Base
from stock_scout.ingest import ingest_fundamentals, ingest_prices, parse_date
from stock_scout.logging import configure_logging
from stock_scout.universe import load_universe_csv

app = typer.Typer(add_completion=False, help="Stock Scout: NSE/BSE dip finder & analyzer")


@app.callback()
def _main(verbose: bool = typer.Option(False, "--verbose", help="Enable debug logging")) -> None:
    configure_logging(level=logging.DEBUG if verbose else logging.INFO)


@app.command()
def init_db() -> None:
    """Create DB tables."""
    settings = Settings()
    engine = get_engine(settings.database_url)
    Base.metadata.create_all(bind=engine)
    print(f"[green]OK[/green] DB initialized: {settings.database_url}")


@app.command("ingest-prices")
def ingest_prices_cmd(
    start: str | None = typer.Option(None, "--start", help="YYYY-MM-DD (defaults to incremental or ~5y back)"),
    end: str | None = typer.Option(None, "--end", help="YYYY-MM-DD (defaults to provider latest)"),
) -> None:
    """Fetch daily OHLCV and store in DB."""
    settings = Settings()
    universe = load_universe_csv(settings.universe_path)

    start_d: date | None = parse_date(start)
    end_d: date | None = parse_date(end)

    with session_scope(settings.database_url) as session:
        ingest_prices(session, settings, universe, start=start_d, end=end_d)
    print("[green]OK[/green] Prices ingested")


@app.command("ingest-fundamentals")
def ingest_fundamentals_cmd() -> None:
    """Fetch fundamentals snapshot and store in DB."""
    settings = Settings()
    universe = load_universe_csv(settings.universe_path)

    with session_scope(settings.database_url) as session:
        ingest_fundamentals(session, settings, universe)
    print("[green]OK[/green] Fundamentals ingested")


@app.command("generate-signals")
def generate_signals_cmd(
    drop_days: int = typer.Option(20, "--drop-days", help="Lookback days for 'falling' detection"),
    horizon_days: int = typer.Option(60, "--horizon-days", help="Evaluation horizon (for later backtests)"),
    min_history: int = typer.Option(220, "--min-history", help="Minimum bars required per stock"),
) -> None:
    """Compute indicators + scores and store signals in DB."""
    settings = Settings()
    with session_scope(settings.database_url) as session:
        generate_signals(
            session,
            settings,
            drop_period_days=drop_days,
            horizon_days=horizon_days,
            min_history=min_history,
        )
    print("[green]OK[/green] Signals generated")


@app.command("train-model")
def train_model_cmd(
    horizon_days: int = typer.Option(20, "--horizon-days", help="Predict forward return horizon (trading days)"),
    model_name: str | None = typer.Option(None, "--model-name", help="Override model name"),
    model_version: str | None = typer.Option(None, "--model-version", help="Override model version"),
) -> None:
    """Train baseline ML model to predict forward returns (optional)."""
    settings = Settings()
    try:
        from stock_scout.ai.train import train_and_save_model
    except Exception as e:
        raise typer.Exit(code=1) from e

    with session_scope(settings.database_url) as session:
        result = train_and_save_model(
            session,
            settings,
            horizon_days=horizon_days,
            model_name=model_name,
            model_version=model_version,
        )
    print(f"[green]OK[/green] Trained {result.model_name}:{result.model_version} h={result.horizon_days}")
    print(f"Artifact: {result.artifact_path}")


@app.command("predict")
def predict_cmd(
    horizon_days: int = typer.Option(20, "--horizon-days", help="Predict forward return horizon (trading days)"),
    artifact_path: str | None = typer.Option(None, "--artifact-path", help="Path to .joblib model artifact"),
    model_name: str | None = typer.Option(None, "--model-name", help="Override model name"),
    model_version: str | None = typer.Option(None, "--model-version", help="Override model version"),
) -> None:
    """Generate latest predictions and store in DB (optional)."""
    settings = Settings()
    try:
        from stock_scout.ai.predict import predict_latest
    except Exception as e:
        raise typer.Exit(code=1) from e

    with session_scope(settings.database_url) as session:
        n = predict_latest(
            session,
            settings,
            horizon_days=horizon_days,
            model_name=model_name,
            model_version=model_version,
            artifact_path=artifact_path,
        )
    print(f"[green]OK[/green] Stored predictions for {n} equities")
