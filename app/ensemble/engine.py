"""
app/ensemble/engine.py
───────────────────────
Ensemble engine — orchestrates all models and produces the final prediction.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import pandas as pd

from app.core.config import settings
from app.core.constants import ModelName, SignalDirection
from app.core.logging import get_logger
from app.ensemble.consensus import ConsensusEngine
from app.ensemble.weighting import EnsembleWeightCalculator
from app.models.base import BaseMLModel, ModelOutput

logger = get_logger("model")


class EnsembleEngine:
    """
    Orchestrates all active ML models.

    1. Runs each model independently
    2. Calculates dynamic weights
    3. Computes weighted ensemble prediction
    4. Applies model agreement threshold
    5. Performs multi-timeframe consensus (if multiple TF results provided)
    """

    def __init__(
        self,
        models: dict[str, BaseMLModel],
        performance_data: Optional[dict[str, dict]] = None,
    ) -> None:
        self.models = models
        self._weight_calculator = EnsembleWeightCalculator()
        self._consensus = ConsensusEngine(min_agreement=settings.min_model_agreement)
        self._performance_data = performance_data or {}

    def predict(
        self,
        X: pd.DataFrame,
        symbol: str,
        timeframe: str,
        timestamp: Optional[datetime] = None,
        regime: Optional[str] = None,
    ) -> dict:
        """
        Run all models and return an ensemble prediction.

        Returns:
            {
                "direction": SignalDirection,
                "confidence": float,
                "model_agreement": float,
                "probability_long": float,
                "probability_short": float,
                "probability_no_trade": float,
                "model_outputs": [ModelOutput],
                "weights": dict,
                "model_table": str,  # human-readable table
            }
        """
        ts = timestamp or datetime.utcnow()
        outputs: list[ModelOutput] = []

        # ── Run each model ────────────────────────────
        for name, model in self.models.items():
            if not model.is_trained:
                logger.debug("Skipping untrained model", model=name)
                continue
            try:
                output = model.predict(X, symbol, timeframe, ts)
                outputs.append(output)
                logger.debug(
                    "Model prediction",
                    model=name,
                    direction=output.prediction.value,
                    confidence=output.confidence,
                    inference_ms=output.inference_ms,
                )
            except Exception as e:
                logger.error("Model prediction failed", model=name, error=str(e))

        if not outputs:
            logger.warning("No model produced output", symbol=symbol, timeframe=timeframe)
            return self._empty_result(symbol, timeframe, ts)

        # ── Calculate dynamic weights ─────────────────
        model_names = [o.model for o in outputs]
        weights = self._weight_calculator.calculate_weights(
            model_names=model_names,
            symbol=symbol,
            timeframe=timeframe,
            regime=regime,
            performance_data=self._performance_data,
        )

        # ── Consensus ─────────────────────────────────
        result = self._consensus.calculate(outputs, weights)
        result["model_outputs"] = outputs
        result["weights"] = weights
        result["symbol"] = symbol
        result["timeframe"] = timeframe
        result["timestamp"] = ts
        result["model_table"] = self._format_model_table(outputs, weights)

        logger.info(
            "Ensemble result",
            symbol=symbol,
            timeframe=timeframe,
            direction=result["direction"].value if hasattr(result["direction"], "value") else result["direction"],
            confidence=result["confidence"],
            agreement=result["model_agreement"],
            models=len(outputs),
        )

        return result

    def update_performance(self, model_name: str, win: bool, regime: Optional[str] = None) -> None:
        """Update model performance after a trade outcome is known."""
        self._weight_calculator.update_performance(
            model_name=model_name,
            win_rate=1.0 if win else 0.0,
            regime=regime,
        )

    def set_performance_data(self, performance_data: dict[str, dict]) -> None:
        """Update performance data (called after evaluation cycle)."""
        self._performance_data = performance_data

    @staticmethod
    def _format_model_table(outputs: list[ModelOutput], weights: dict[str, float]) -> str:
        """Format model outputs as a readable table for Telegram."""
        lines = []
        for out in sorted(outputs, key=lambda x: weights.get(x.model, 0), reverse=True):
            w = weights.get(out.model, 0)
            dir_emoji = "🟢" if out.prediction == SignalDirection.LONG else (
                "🔴" if out.prediction == SignalDirection.SHORT else "⚪"
            )
            lines.append(
                f"{out.model.ljust(14)} {dir_emoji} {out.prediction.value.ljust(8)} "
                f"{out.confidence*100:.0f}%  (w:{w*100:.0f}%)"
            )
        return "\n".join(lines)

    @staticmethod
    def _empty_result(symbol: str, timeframe: str, ts: datetime) -> dict:
        return {
            "direction": SignalDirection.NO_TRADE,
            "confidence": 0.0,
            "model_agreement": 0.0,
            "probability_long": 0.0,
            "probability_short": 0.0,
            "probability_no_trade": 1.0,
            "model_outputs": [],
            "weights": {},
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": ts,
            "model_table": "",
        }
