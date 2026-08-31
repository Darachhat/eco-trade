"""
app/models/lightgbm_model.py
─────────────────────────────
LightGBM gradient boosting classifier.
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any, Optional

try:
    import lightgbm as lgb
    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False
    lgb = None

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from app.core.logging import get_logger
from app.models.base import BaseMLModel

logger = get_logger("model")


class LightGBMModel(BaseMLModel):
    DEFAULT_PARAMS: dict = {
        "n_estimators": 500,
        "max_depth": 6,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "min_child_samples": 20,
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
        "objective": "multiclass",
        "num_class": 3,
        "metric": "multi_logloss",
        "verbose": -1,
        "random_state": 42,
        "n_jobs": -1,
    }

    def __init__(self, version: str = "v1", params: Optional[dict] = None) -> None:
        super().__init__(model_name="lightgbm", version=version)
        self._params = {**self.DEFAULT_PARAMS, **(params or {})}
        self._model = None
        self._scaler: Optional[StandardScaler] = None

    def train(self, X: pd.DataFrame, y: pd.Series, **kwargs: Any) -> dict:
        if not HAS_LIGHTGBM:
            logger.warning("LightGBM not installed in environment")
            return {}
        logger.info("Training LightGBM", version=self.version, samples=len(X))
        self._feature_names = list(X.columns)
        self._scaler = StandardScaler()
        X_scaled = self._scaler.fit_transform(X.values.astype(np.float32))

        val_X = kwargs.get("val_X")
        val_y = kwargs.get("val_y")
        callbacks = [lgb.early_stopping(50, verbose=False), lgb.log_evaluation(period=-1)]
        eval_set = None
        if val_X is not None and val_y is not None:
            val_scaled = self._scaler.transform(val_X.values.astype(np.float32))
            eval_set = [(val_scaled, val_y.values)]

        self._model = lgb.LGBMClassifier(**self._params)
        self._model.fit(
            X_scaled, y.values,
            eval_set=eval_set,
            callbacks=callbacks if eval_set else [lgb.log_evaluation(period=-1)],
        )
        self._is_trained = True
        return self.evaluate(X, y)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        if not HAS_LIGHTGBM or self._model is None:
            return np.array([[1/3, 1/3, 1/3]])
        X_arr = X.values.astype(np.float32)
        if self._scaler:
            X_arr = self._scaler.transform(X_arr)
        return self._model.predict_proba(X_arr)

    def save(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        with open(path / f"lightgbm_{self.version}.pkl", "wb") as f:
            pickle.dump({"model": self._model, "scaler": self._scaler, "features": self._feature_names}, f)

    def load(self, path: Path) -> None:
        with open(path / f"lightgbm_{self.version}.pkl", "rb") as f:
            d = pickle.load(f)
        self._model = d["model"]
        self._scaler = d.get("scaler")
        self._feature_names = d["features"]
        self._is_trained = True
