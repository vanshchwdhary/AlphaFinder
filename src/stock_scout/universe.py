from __future__ import annotations

import csv
from pathlib import Path

from stock_scout.config import UniverseEntry


def load_universe_csv(path: str) -> list[UniverseEntry]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Universe file not found: {p.resolve()}")

    entries: list[UniverseEntry] = []
    with p.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            symbol = (row.get("symbol") or "").strip().upper()
            exchange = (row.get("exchange") or "").strip().upper()
            name = (row.get("name") or "").strip() or None
            if not symbol or not exchange:
                continue
            entries.append(UniverseEntry(symbol=symbol, exchange=exchange, name=name))
    if not entries:
        raise ValueError(f"Universe file had no valid entries: {p.resolve()}")
    return entries

