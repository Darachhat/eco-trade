"""
app/models/garch.py
────────────────────
GARCH(1,1) volatility model.
Used for volatility regime detection and risk adjustment.
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

from app.core.logging import get_logger
from app.models.base import BaseMLModel

logger = get_logger("model")


class GARCHModel(BaseMLModel):
    """
    GARCH(1,1) volatility forecasting model.
    Primary output: volatility forecast used to adjust signal confidence.
    Direction prediction = NO_TRADE when volatility is extreme.
    """

    def __init__(self, version: str = "v1", p: int = 1, q: int = 1) -> None:
        super().__init__(model_name="garch", version=version)
        self.p = p
        self.q = q
        self._fitted = None
        self._vol_mean: float = 0.0
        self._vol_std: float = 1.0

    def train(self, X: pd.DataFrame, y: pd.Series, **kwargs: Any) -> dict:
        logger.info("Training GARCH", version=self.version)
        try:
            from arch import arch_model

            prices = kwargs.get("prices")
            if prices is None and "close" in X.columns:
                prices = X["close"].values
            else:
                logger.warning("GARCH: no price series, skipping")
                return {}

            returns = np.diff(np.log(prices)) * 100
            am = arch_model(returns, vol="Garch", p=self.p, q=self.q, rescale=False)
            self._fitted = am.fit(disp="off")

            # Store historical volatility stats for normalization
            cond_vol = self._fitted.conditional_volatility
            self._vol_mean = float(np.mean(cond_vol))
            self._vol_std = float(np.std(cond_vol))

            self._is_trained = True
            logger.info("GARCH fitted")
        except Exception as e:
            logger.error("GARCH training failed", error=str(e))
        return {}

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        Forecast volatility and convert to direction probabilities.
        High volatility → NO_TRADE.
        Normal volatility → defer to other models (return equal probs).
        """
        if self._fitted is None:
            return np.array([[1/3, 1/3, 1/3]])

        try:
            from arch import arch_model

            if "close" in X.columns:
                prices = X["close"].values[-100:]
                returns = np.diff(np.log(prices)) * 100
                am = arch_model(returns, vol="Garch", p=self.p, q=self.q, rescale=False)
                fitted = am.fit(disp="off", starting_values=self._fitted.params)
            else:
                fitted = self._fitted

            forecast = fitted.forecast(horizon=1)
            forecast_vol = float(np.sqrt(forecast.variance.values[-1, 0]))

            # Normalize
            z_score = (forecast_vol - self._vol_mean) / max(self._vol_std, 1e-8)

            if z_score > 2.0:
                # Very high volatility → NO_TRADE
                return np.array([[0.8, 0.1, 0.1]])
            elif z_score > 1.0:
                # Elevated volatility → slight NO_TRADE bias
                return np.array([[0.5, 0.25, 0.25]])
            else:
                # Normal volatility → neutral (rely on other models)
                return np.array([[1/3, 1/3, 1/3]])

        except Exception as e:
            logger.debug("GARCH predict failed", error=str(e))
            return np.array([[1/3, 1/3, 1/3]])

    def get_current_volatility(self, X: pd.DataFrame) -> Optional[float]:
        """Return the current forecasted volatility (annualized %)."""
        if self._fitted is None:
            return None
        try:
            from arch import arch_model
            if "close" in X.columns:
                prices = X["close"].values[-100:]
                returns = np.diff(np.log(prices)) * 100
                am = arch_model(returns, vol="Garch", p=self.p, q=self.q, rescale=False)
                fitted = am.fit(disp="off")
                forecast = fitted.forecast(horizon=1)
                daily_vol = float(np.sqrt(forecast.variance.values[-1, 0]))
                # Annualize (crypto: 365*24 hours)
                return daily_vol * np.sqrt(365 * 24) / 100
        except Exception:
            return None
        return None

    def save(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        with open(path / f"garch_{self.version}.pkl", "wb") as f:
            pickle.dump({"fitted": self._fitted, "p": self.p, "q": self.q,
                         "vol_mean": self._vol_mean, "vol_std": self._vol_std}, f)

    def load(self, path: Path) -> None:
        with open(path / f"garch_{self.version}.pkl", "rb") as f:
            d = pickle.load(f)
        self._fitted = d["fitted"]
        self.p = d["p"]
        self.q = d["q"]
        self._vol_mean = d["vol_mean"]
        self._vol_std = d["vol_std"]
        self._is_trained = True
