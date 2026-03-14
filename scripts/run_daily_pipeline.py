from __future__ import annotations

import logging
from pathlib import Path

from stock_scout.analysis.signals import generate_signals
from stock_scout.config import Settings
from stock_scout.db.engine import session_scope
from stock_scout.ingest import ingest_fundamentals, ingest_prices
from stock_scout.logging import configure_logging
from stock_scout.universe import load_universe_csv


def main() -> None:
    configure_logging(level=logging.INFO)
    settings = Settings()
    universe = load_universe_csv(settings.universe_path)

    with session_scope(settings.database_url) as session:
        ingest_prices(session, settings, universe, start=None, end=None)
        ingest_fundamentals(session, settings, universe)

        # Optional: if an AI model artifact exists, produce predictions before scoring.
        model_path = Path(settings.artifacts_dir) / "models" / f"{settings.ai_model_name}_{settings.ai_model_version}_h{settings.ai_horizon_days}.joblib"
        if model_path.exists():
            try:
                from stock_scout.ai.predict import predict_latest

                predict_latest(
                    session,
                    settings,
                    horizon_days=settings.ai_horizon_days,
                    artifact_path=str(model_path),
                )
            except Exception:
                logging.exception("AI prediction step failed; continuing without AI")

        generate_signals(session, settings, drop_period_days=20, horizon_days=60)


if __name__ == "__main__":
    main()

