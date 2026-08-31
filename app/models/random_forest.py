"""
app/models/random_forest.py — Random Forest classifier
app/models/logistic.py — Logistic Regression baseline
app/models/lightgbm_model.py — LightGBM classifier
"""

# ─── random_forest.py ───────────────────────────────────────────────────────

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

from app.core.logging import get_logger
from app.models.base import BaseMLModel

logger = get_logger("model")


class RandomForestModel(BaseMLModel):
    DEFAULT_PARAMS = {
        "n_estimators": 300,
        "max_depth": 10,
        "min_samples_leaf": 10,
        "max_features": "sqrt",
        "class_weight": "balanced",
        "random_state": 42,
        "n_jobs": -1,
    }

    def __init__(self, version: str = "v1", params: Optional[dict] = None) -> None:
        super().__init__(model_name="random_forest", version=version)
        self._params = {**self.DEFAULT_PARAMS, **(params or {})}
        self._model: Optional[RandomForestClassifier] = None
        self._scaler: Optional[StandardScaler] = None

    def train(self, X: pd.DataFrame, y: pd.Series, **kwargs: Any) -> dict:
        logger.info("Training RandomForest", version=self.version, samples=len(X))
        self._feature_names = list(X.columns)
        self._scaler = StandardScaler()
        X_scaled = self._scaler.fit_transform(X.values.astype(np.float32))
        self._model = RandomForestClassifier(**self._params)
        self._model.fit(X_scaled, y.values)
        self._is_trained = True
        return self.evaluate(X, y)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        if self._model is None:
            raise RuntimeError("Model not trained")
        X_arr = X.values.astype(np.float32)
        if self._scaler:
            X_arr = self._scaler.transform(X_arr)
        return self._model.predict_proba(X_arr)

    def save(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        with open(path / f"random_forest_{self.version}.pkl", "wb") as f:
            pickle.dump({"model": self._model, "scaler": self._scaler, "features": self._feature_names}, f)

    def load(self, path: Path) -> None:
        with open(path / f"random_forest_{self.version}.pkl", "rb") as f:
            d = pickle.load(f)
        self._model = d["model"]
        self._scaler = d.get("scaler")
        self._feature_names = d["features"]
        self._is_trained = True
