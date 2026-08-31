"""
app/models/base.py
───────────────────
Abstract base class for all ML models.
Every model must implement this interface.
Standardized output schema (Section 16 of spec).
"""

from __future__ import annotations

import abc
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from app.core.constants import ModelName, SignalDirection
from app.core.logging import get_logger

logger = get_logger("model")


# ─────────────────────────────────────────────
# Standardized Model Output
# ─────────────────────────────────────────────

class ModelOutput(BaseModel):
    """
    Standardized output that every model must return.
    All models use the same interface.
    """
    model: str
    version: str
    symbol: str
    timeframe: str
    timestamp: datetime
    prediction: SignalDirection
    probability_long: float = Field(ge=0.0, le=1.0)
    probability_short: float = Field(ge=0.0, le=1.0)
    probability_no_trade: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    inference_ms: Optional[float] = None
    features_used: Optional[int] = None
    explanation: Optional[dict] = None

    @property
    def top_prediction(self) -> SignalDirection:
        probs = {
            SignalDirection.LONG: self.probability_long,
            SignalDirection.SHORT: self.probability_short,
            SignalDirection.NO_TRADE: self.probability_no_trade,
        }
        return max(probs, key=lambda k: probs[k])

    def to_dict(self) -> dict:
        return {
            "model": self.model,
            "version": self.version,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "timestamp": self.timestamp.isoformat(),
            "prediction": self.prediction.value,
            "probability_long": round(self.probability_long, 4),
            "probability_short": round(self.probability_short, 4),
            "probability_no_trade": round(self.probability_no_trade, 4),
            "confidence": round(self.confidence, 4),
            "inference_ms": self.inference_ms,
        }


# ─────────────────────────────────────────────
# Abstract Model
# ─────────────────────────────────────────────

class BaseMLModel(abc.ABC):
    """
    Abstract base class for all ML models in the system.

    Subclasses must implement:
    - train(X, y) -> None
    - predict(X) -> ModelOutput
    - save(path) -> None
    - load(path) -> None
    """

    def __init__(self, model_name: str, version: str = "v1") -> None:
        self.model_name = model_name
        self.version = version
        self._is_trained = False
        self._feature_names: list[str] = []
        self._training_date: Optional[datetime] = None

    # ── Abstract interface ────────────────────

    @abc.abstractmethod
    def train(self, X: pd.DataFrame, y: pd.Series, **kwargs: Any) -> dict:
        """
        Train the model.

        Args:
            X: Feature matrix (training data only — no future data)
            y: Labels (0=NO_TRADE, 1=LONG, 2=SHORT or similar encoding)

        Returns:
            dict of training metrics
        """
        ...

    @abc.abstractmethod
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        Return probability array of shape [n_samples, 3].
        Columns: [prob_no_trade, prob_long, prob_short]
        """
        ...

    @abc.abstractmethod
    def save(self, path: Path) -> None:
        """Persist the model to disk."""
        ...

    @abc.abstractmethod
    def load(self, path: Path) -> None:
        """Load the model from disk."""
        ...

    # ── Concrete methods ──────────────────────

    def predict(
        self,
        X: pd.DataFrame,
        symbol: str,
        timeframe: str,
        timestamp: Optional[datetime] = None,
    ) -> ModelOutput:
        """
        Run inference and return standardized ModelOutput.
        Times the inference.
        """
        if not self._is_trained:
            return self._untrained_output(symbol, timeframe, timestamp)

        start = time.perf_counter()
        try:
            # Align features to trained columns
            X_aligned = self._align_features(X)
            proba = self.predict_proba(X_aligned)
            elapsed_ms = (time.perf_counter() - start) * 1000

            # proba shape: [n_samples, 3] — take last row for current candle
            if proba.ndim == 2:
                p = proba[-1]
            else:
                p = proba

            # Map: [prob_no_trade, prob_long, prob_short]
            prob_no_trade = float(p[0])
            prob_long = float(p[1])
            prob_short = float(p[2])

            # Normalize
            total = prob_long + prob_short + prob_no_trade
            if total > 0:
                prob_long /= total
                prob_short /= total
                prob_no_trade /= total

            # Pick direction
            if prob_long >= prob_short and prob_long >= prob_no_trade:
                direction = SignalDirection.LONG
                confidence = prob_long
            elif prob_short >= prob_long and prob_short >= prob_no_trade:
                direction = SignalDirection.SHORT
                confidence = prob_short
            else:
                direction = SignalDirection.NO_TRADE
                confidence = prob_no_trade

            return ModelOutput(
                model=self.model_name,
                version=self.version,
                symbol=symbol,
                timeframe=timeframe,
                timestamp=timestamp or datetime.utcnow(),
                prediction=direction,
                probability_long=round(prob_long, 4),
                probability_short=round(prob_short, 4),
                probability_no_trade=round(prob_no_trade, 4),
                confidence=round(confidence, 4),
                inference_ms=round(elapsed_ms, 2),
                features_used=len(self._feature_names),
            )
        except Exception as e:
            logger.error(
                "Model prediction failed",
                model=self.model_name,
                error=str(e),
            )
            return self._error_output(symbol, timeframe, timestamp)

    def evaluate(self, X: pd.DataFrame, y: pd.Series) -> dict:
        """Compute evaluation metrics on a holdout set."""
        from sklearn.metrics import (
            accuracy_score,
            brier_score_loss,
            f1_score,
            precision_score,
            recall_score,
            roc_auc_score,
        )

        proba = self.predict_proba(self._align_features(X))
        y_pred = proba.argmax(axis=1)

        metrics: dict = {}
        try:
            metrics["accuracy"] = float(accuracy_score(y, y_pred))
            metrics["f1_macro"] = float(f1_score(y, y_pred, average="macro", zero_division=0))
            metrics["precision"] = float(
                precision_score(y, y_pred, average="macro", zero_division=0)
            )
            metrics["recall"] = float(recall_score(y, y_pred, average="macro", zero_division=0))
            # Brier score (for binary long vs not-long)
            y_binary = (y == 1).astype(int)
            metrics["brier_score"] = float(brier_score_loss(y_binary, proba[:, 1]))
            if len(np.unique(y)) > 1:
                metrics["roc_auc"] = float(
                    roc_auc_score(
                        y,
                        proba,
                        multi_class="ovr",
                        average="macro",
                    )
                )
        except Exception as e:
            logger.warning("Evaluation metric failed", error=str(e))

        return metrics

    def _align_features(self, X: pd.DataFrame) -> pd.DataFrame:
        """Align feature columns to those used during training."""
        if not self._feature_names:
            return X
        # Add missing columns as 0
        for col in self._feature_names:
            if col not in X.columns:
                X = X.copy()
                X[col] = 0.0
        return X[self._feature_names]

    def _untrained_output(
        self, symbol: str, timeframe: str, timestamp: Optional[datetime]
    ) -> ModelOutput:
        return ModelOutput(
            model=self.model_name,
            version=self.version,
            symbol=symbol,
            timeframe=timeframe,
            timestamp=timestamp or datetime.utcnow(),
            prediction=SignalDirection.NO_TRADE,
            probability_long=0.0,
            probability_short=0.0,
            probability_no_trade=1.0,
            confidence=0.0,
        )

    def _error_output(
        self, symbol: str, timeframe: str, timestamp: Optional[datetime]
    ) -> ModelOutput:
        return self._untrained_output(symbol, timeframe, timestamp)

    @property
    def is_trained(self) -> bool:
        return self._is_trained
