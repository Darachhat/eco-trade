"""
app/models/xgboost_model.py
────────────────────────────
XGBoost classifier — primary tabular ML model.
Supports multi-class: NO_TRADE=0, LONG=1, SHORT=2.
Includes SHAP explainability.
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import StandardScaler

from app.core.logging import get_logger
from app.models.base import BaseMLModel

logger = get_logger("model")


class XGBoostModel(BaseMLModel):
    """
    XGBoost gradient boosting classifier.

    Default hyperparameters are production-ready defaults.
    Use Optuna (in retrainer.py) to optimize on training data.
    """

    DEFAULT_PARAMS: dict = {
        "n_estimators": 500,
        "max_depth": 6,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "min_child_weight": 5,
        "gamma": 0.1,
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
        "objective": "multi:softprob",
        "num_class": 3,
        "eval_metric": "mlogloss",
        "random_state": 42,
        "n_jobs": -1,
        "tree_method": "hist",
    }

    def __init__(self, version: str = "v1", params: Optional[dict] = None) -> None:
        super().__init__(model_name="xgboost", version=version)
        self._params = {**self.DEFAULT_PARAMS, **(params or {})}
        self._model: Optional[xgb.XGBClassifier] = None
        self._calibrated: Optional[CalibratedClassifierCV] = None
        self._scaler: Optional[StandardScaler] = None
        self._use_calibration = False

    def train(self, X: pd.DataFrame, y: pd.Series, **kwargs: Any) -> dict:
        """
        Train XGBoost on the feature matrix.

        Args:
            X: Feature DataFrame (training set only — already split)
            y: Labels (0=NO_TRADE, 1=LONG, 2=SHORT)

        IMPORTANT: X and y must NOT contain future data.
        Scaler is fitted ONLY on X (training data).
        """
        logger.info("Training XGBoost", version=self.version, samples=len(X))

        self._feature_names = list(X.columns)
        X_arr = X.values.astype(np.float32)

        # Scale features (fitted only on training data)
        self._scaler = StandardScaler()
        X_scaled = self._scaler.fit_transform(X_arr)

        val_X = kwargs.get("val_X")
        val_y = kwargs.get("val_y")

        eval_set = None
        model_params = dict(self._params)
        if val_X is not None and val_y is not None:
            val_scaled = self._scaler.transform(val_X.values.astype(np.float32))
            eval_set = [(val_scaled, val_y.values)]
            model_params["early_stopping_rounds"] = 50

        self._model = xgb.XGBClassifier(**model_params)
        self._model.fit(
            X_scaled,
            y.values,
            eval_set=eval_set,
            verbose=False,
        )

        self._is_trained = True
        logger.info("XGBoost training complete", best_ntree=getattr(self._model, "best_ntree_limit", None))

        return self.evaluate(X, y)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Return [n_samples, 3] probability array."""
        if self._model is None:
            raise RuntimeError("Model not trained")
        X_arr = X.values.astype(np.float32)
        if self._scaler is not None:
            X_arr = self._scaler.transform(X_arr)
        return self._model.predict_proba(X_arr)

    def get_shap_values(self, X: pd.DataFrame) -> Optional[dict]:
        """
        Compute SHAP values for explainability.
        Returns top features contributing to the prediction.
        """
        if self._model is None:
            return None
        try:
            import shap
            explainer = shap.TreeExplainer(self._model)
            X_arr = X.values.astype(np.float32)
            if self._scaler:
                X_arr = self._scaler.transform(X_arr)
            shap_values = explainer.shap_values(X_arr[-1:])
            feature_names = self._feature_names

            if isinstance(shap_values, list) and len(shap_values) > 1:
                sv = shap_values[1][0]  # LONG class, first sample
            else:
                sv = shap_values[0]

            indices = np.argsort(np.abs(sv))[::-1][:10]
            top_features = {
                feature_names[i]: round(float(sv[i]), 4)
                for i in indices
                if i < len(feature_names)
            }
            return top_features
        except Exception as e:
            logger.debug("SHAP computation failed", error=str(e))
            return None

    def save(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        model_path = path / f"xgboost_{self.version}.pkl"
        payload = {
            "model": self._model,
            "scaler": self._scaler,
            "feature_names": self._feature_names,
            "version": self.version,
            "params": self._params,
        }
        with open(model_path, "wb") as f:
            pickle.dump(payload, f)
        logger.info("XGBoost model saved", path=str(model_path))

    def load(self, path: Path) -> None:
        model_path = path / f"xgboost_{self.version}.pkl"
        if not model_path.exists():
            raise FileNotFoundError(f"XGBoost model not found: {model_path}")
        with open(model_path, "rb") as f:
            payload = pickle.load(f)
        self._model = payload["model"]
        self._scaler = payload.get("scaler")
        self._feature_names = payload["feature_names"]
        self.version = payload["version"]
        self._params = payload.get("params", self._params)
        self._is_trained = True
        logger.info("XGBoost model loaded", path=str(model_path), version=self.version)

    @property
    def feature_importance(self) -> Optional[dict]:
        if self._model is None:
            return None
        importance = self._model.feature_importances_
        return dict(sorted(
            zip(self._feature_names, importance.tolist()),
            key=lambda x: x[1],
            reverse=True,
        ))
