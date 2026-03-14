from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from stock_scout.ai.dataset import FEATURE_COLUMNS, build_latest_features
from stock_scout.config import Settings
from stock_scout.db.repositories import upsert_prediction


def predict_latest(
    session: Session,
    settings: Settings,
    *,
    horizon_days: int,
    model_name: str | None = None,
    model_version: str | None = None,
    artifact_path: str | None = None,
) -> int:
    _require_joblib()
    from joblib import load

    model_name = model_name or settings.ai_model_name
    model_version = model_version or settings.ai_model_version

    if artifact_path is None:
        default_path = Path(settings.artifacts_dir) / "models" / f"{model_name}_{model_version}_h{horizon_days}.joblib"
        artifact_path = str(default_path)

    model = load(artifact_path)
    features = build_latest_features(session, settings, horizon_days=horizon_days)
    X = features[FEATURE_COLUMNS]
    preds = model.predict(X)

    now = datetime.now(timezone.utc)
    n = 0
    for row, pred in zip(features.to_dict(orient="records"), preds):
        upsert_prediction(
            session,
            row={
                "equity_id": int(row["equity_id"]),
                "as_of_date": row["as_of_date"],
                "horizon_days": horizon_days,
                "model_name": model_name,
                "model_version": model_version,
                "predicted_return": float(pred),
                "predicted_prob_up": None,
                "created_at": now,
            },
        )
        n += 1
    return n


def _require_joblib() -> None:
    try:
        import joblib  # noqa: F401
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "Missing AI dependencies. Install with: pip install -e \".[ai]\""
        ) from e
