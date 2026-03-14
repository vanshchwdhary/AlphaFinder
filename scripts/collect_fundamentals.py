from __future__ import annotations

import logging

from stock_scout.config import Settings
from stock_scout.db.engine import session_scope
from stock_scout.ingest import ingest_fundamentals
from stock_scout.logging import configure_logging
from stock_scout.universe import load_universe_csv


def main() -> None:
    configure_logging(level=logging.INFO)
    settings = Settings()
    universe = load_universe_csv(settings.universe_path)

    with session_scope(settings.database_url) as session:
        ingest_fundamentals(session, settings, universe)


if __name__ == "__main__":
    main()

