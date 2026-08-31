"""
app/ensemble/weighting.py
──────────────────────────
Dynamic ensemble weight calculation.
Weights are based on: recent perf, long-term perf, current regime,
timeframe, asset-specific perf, calibration, and drawdown.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Optional

import numpy as np

from app.core.constants import MarketRegime, ModelName
from app.core.logging import get_logger

logger = get_logger("model")

# Minimum weight any model can receive (prevents zeroing out)
MIN_WEIGHT = 0.02
# Initial default weights (before performance data accumulates)
DEFAULT_WEIGHTS: dict[str, float] = {
    ModelName.XGBOOST: 0.25,
    ModelName.LIGHTGBM: 0.20,
    ModelName.TRANSFORMER: 0.20,
    ModelName.LSTM: 0.12,
    ModelName.GRU: 0.08,
    ModelName.RANDOM_FOREST: 0.07,
    ModelName.LOGISTIC: 0.03,
    ModelName.ARIMA: 0.03,
    ModelName.GARCH: 0.01,
    ModelName.TECHNICAL: 0.01,
}


class EnsembleWeightCalculator:
    """
    Calculates dynamic model weights for the ensemble.

    Weights are updated after each prediction cycle based on
    rolling model performance.
    """

    def __init__(self) -> None:
        # Stores rolling performance per model: {model_name: [recent_win_rates]}
        self._performance_history: dict[str, list[float]] = defaultdict(list)
        self._regime_performance: dict[str, dict[str, float]] = defaultdict(dict)
        self._current_weights: dict[str, float] = dict(DEFAULT_WEIGHTS)

    def calculate_weights(
        self,
        model_names: list[str],
        symbol: str,
        timeframe: str,
        regime: Optional[str] = None,
        performance_data: Optional[dict[str, dict]] = None,
    ) -> dict[str, float]:
        """
        Calculate normalized weights for the given models.

        Args:
            model_names: Active model names
            symbol: Trading symbol
            timeframe: Timeframe being predicted
            regime: Current market regime
            performance_data: {model_name: {win_rate, profit_factor, accuracy, drawdown}}

        Returns:
            Normalized weight dict summing to 1.0
        """
        weights: dict[str, float] = {}

        for name in model_names:
            base_weight = DEFAULT_WEIGHTS.get(name, 0.05)

            if performance_data and name in performance_data:
                perf = performance_data[name]

                # Reward win rate
                win_rate = perf.get("win_rate", 0.5)
                win_rate_factor = 0.5 + win_rate  # [0.5, 1.5]

                # Reward profit factor (capped)
                pf = min(perf.get("profit_factor", 1.0), 3.0)
                pf_factor = 0.5 + pf / 3  # [0.5, 1.5]

                # Penalize drawdown
                mdd = perf.get("max_drawdown", 0.0)
                dd_factor = max(1.0 - mdd * 2, 0.3)  # large MDD → lower weight

                # Regime-specific performance
                regime_factor = 1.0
                if regime and regime in self._regime_performance.get(name, {}):
                    regime_perf = self._regime_performance[name][regime]
                    regime_factor = 0.5 + regime_perf  # [0.5, 1.5]

                adjusted = base_weight * win_rate_factor * pf_factor * dd_factor * regime_factor
            else:
                adjusted = base_weight

            weights[name] = max(adjusted, MIN_WEIGHT)

        # Normalize to sum = 1
        return self._normalize(weights)

    def update_performance(
        self,
        model_name: str,
        win_rate: float,
        regime: Optional[str] = None,
    ) -> None:
        """Update rolling performance for a model."""
        history = self._performance_history[model_name]
        history.append(win_rate)
        # Keep last 100 outcomes
        if len(history) > 100:
            self._performance_history[model_name] = history[-100:]

        if regime:
            # Exponential moving average of regime-specific win rate
            current = self._regime_performance[model_name].get(regime, 0.5)
            self._regime_performance[model_name][regime] = 0.9 * current + 0.1 * win_rate

    def get_current_weights(self) -> dict[str, float]:
        return dict(self._current_weights)

    @staticmethod
    def _normalize(weights: dict[str, float]) -> dict[str, float]:
        total = sum(weights.values())
        if total == 0:
            n = len(weights)
            return {k: 1 / n for k in weights}
        return {k: round(v / total, 4) for k, v in weights.items()}
