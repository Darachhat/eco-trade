"""
app/models/arima.py
────────────────────
ARIMA statistical model — price direction support model.
Converts price forecast direction to LONG/SHORT/NO_TRADE probabilities.
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

try:
    from statsmodels.tsa.arima.model import ARIMA, ARIMAResults
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False
    ARIMA = None
    ARIMAResults = None

from app.core.logging import get_logger
from app.models.base import BaseMLModel

logger = get_logger("model")


class ARIMAModel(BaseMLModel):
    def __init__(self, version: str = "v1", order: tuple = (2, 1, 2), horizon: int = 5) -> None:
        super().__init__(model_name="arima", version=version)
        self.order = order
        self.horizon = horizon
        self._fitted = None
        self._last_prices: Optional[np.ndarray] = None

    def train(self, X: pd.DataFrame, y: pd.Series, **kwargs: Any) -> dict:
        if not HAS_STATSMODELS:
            logger.warning("statsmodels not installed in environment")
            return {}
        logger.info("Training ARIMA", version=self.version)
        self._feature_names = list(X.columns) if not X.empty else []

        prices = kwargs.get("prices")
        if prices is None and "close" in X.columns:
            prices = X["close"].values
        elif prices is None:
            logger.warning("ARIMA: no price series provided, skipping")
            return {}

        log_prices = np.log(prices)
        try:
            model = ARIMA(log_prices, order=self.order)
            self._fitted = model.fit()
            self._last_prices = log_prices
            self._is_trained = True
            logger.info("ARIMA trained", aic=self._fitted.aic)
        except Exception as e:
            logger.error("ARIMA training failed", error=str(e))
        return {}

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        if not HAS_STATSMODELS or self._fitted is None or self._last_prices is None:
            return np.array([[1/3, 1/3, 1/3]])

        try:
            if "close" in X.columns:
                recent_prices = np.log(X["close"].values[-50:])
                model = ARIMA(recent_prices, order=self.order)
                fitted = model.fit()
            else:
                fitted = self._fitted

            forecast = fitted.forecast(steps=self.horizon)
            current_log = fitted.model.endog[-1] if hasattr(fitted.model, "endog") else 0

            expected_return = float(forecast.mean() - current_log)
            confidence = min(abs(expected_return) * 10, 0.8)

            if expected_return > 0.001:
                return np.array([[0.1, confidence, 0.9 - confidence]])
            elif expected_return < -0.001:
                return np.array([[0.1, 0.9 - confidence, confidence]])
            else:
                return np.array([[0.8, 0.1, 0.1]])
        except Exception as e:
            logger.debug("ARIMA predict failed", error=str(e))
            return np.array([[1/3, 1/3, 1/3]])

    def save(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        with open(path / f"arima_{self.version}.pkl", "wb") as f:
            pickle.dump({"fitted": self._fitted, "order": self.order,
                         "horizon": self.horizon, "last_prices": self._last_prices}, f)

    def load(self, path: Path) -> None:
        with open(path / f"arima_{self.version}.pkl", "rb") as f:
            d = pickle.load(f)
        self._fitted = d["fitted"]
        self.order = d["order"]
        self.horizon = d["horizon"]
        self._last_prices = d["last_prices"]
        self._is_trained = True
