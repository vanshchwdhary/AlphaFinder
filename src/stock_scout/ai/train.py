from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from stock_scout.ai.dataset import FEATURE_COLUMNS, build_dataset
from stock_scout.config import Settings
from stock_scout.db.repositories import upsert_model_artifact


@dataclass(frozen=True)
class TrainResult:
    model_name: str
    model_version: str
    horizon_days: int
    artifact_path: str
    metrics: dict[str, Any]


def train_and_save_model(
    session: Session,
    settings: Settings,
    *,
    horizon_days: int,
    model_name: str | None = None,
    model_version: str | None = None,
) -> TrainResult:
    _require_sklearn()
    from joblib import dump
    from sklearn.impute import SimpleImputer
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline
    from sklearn.ensemble import HistGradientBoostingRegressor

    model_name = model_name or settings.ai_model_name
    model_version = model_version or settings.ai_model_version

    ds = build_dataset(session, settings, horizon_days=horizon_days)
    X = ds.X
    y = ds.y
    meta = ds.meta

    # time-aware split by date (not perfect, but avoids random leakage)
    tmp = meta.copy()
    tmp["y"] = y.values
    tmp["idx"] = range(len(tmp))
    tmp = tmp.sort_values("date")
    cutoff = int(len(tmp) * 0.80)
    train_idx = tmp.iloc[:cutoff]["idx"].to_numpy()
    test_idx = tmp.iloc[cutoff:]["idx"].to_numpy()

    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

    model = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            (
                "reg",
                HistGradientBoostingRegressor(
                    max_depth=3,
                    learning_rate=0.05,
                    max_iter=400,
                    random_state=42,
                ),
            ),
        ]
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    metrics = {
        "mae": float(mean_absolute_error(y_test, preds)),
        "rmse": float(mean_squared_error(y_test, preds, squared=False)),
        "r2": float(r2_score(y_test, preds)),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "feature_columns": FEATURE_COLUMNS,
    }

    out_dir = Path(settings.artifacts_dir) / "models"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{model_name}_{model_version}_h{horizon_days}.joblib"
    dump(model, path)

    # register in DB
    upsert_model_artifact(
        session,
        row={
            "model_name": model_name,
            "model_version": model_version,
            "horizon_days": horizon_days,
            "trained_at": datetime.now(timezone.utc),
            "features": {"columns": FEATURE_COLUMNS},
            "metrics": metrics,
            "artifact_path": str(path),
        },
    )

    # also write sidecar metrics json (easy to inspect)
    metrics_path = path.with_suffix(".metrics.json")
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    return TrainResult(
        model_name=model_name,
        model_version=model_version,
        horizon_days=horizon_days,
        artifact_path=str(path),
        metrics=metrics,
    )


def _require_sklearn() -> None:
    try:
        import sklearn  # noqa: F401
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "Missing AI dependencies. Install with: pip install -e \".[ai]\""
        ) from e

