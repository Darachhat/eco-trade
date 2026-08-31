"""
tests/unit/test_ensemble.py
────────────────────────────
Unit tests for dynamic ensemble weighting, consensus calculation, and MTF alignment.
"""

from __future__ import annotations

from datetime import datetime
import pytest

from app.core.constants import SignalDirection
from app.ensemble.consensus import ConsensusEngine
from app.ensemble.weighting import EnsembleWeightCalculator
from app.models.base import ModelOutput


def test_ensemble_weight_normalization():
    calc = EnsembleWeightCalculator()
    weights = calc.calculate_weights(
        model_names=["xgboost", "lightgbm", "transformer", "random_forest"],
        symbol="BTCUSDT",
        timeframe="15",
    )
    assert len(weights) == 4
    assert np_sum_close(list(weights.values()), 1.0)


def test_consensus_agreement_threshold():
    consensus = ConsensusEngine(min_agreement=0.70)

    # 1. High agreement (3 of 4 agree on LONG = 75% > 70%)
    outputs_bullish = [
        ModelOutput(model="xgboost", version="v1", symbol="BTCUSDT", timeframe="15", timestamp=datetime.utcnow(),
                    prediction=SignalDirection.LONG, probability_long=0.8, probability_short=0.1, probability_no_trade=0.1, confidence=0.8),
        ModelOutput(model="lightgbm", version="v1", symbol="BTCUSDT", timeframe="15", timestamp=datetime.utcnow(),
                    prediction=SignalDirection.LONG, probability_long=0.75, probability_short=0.15, probability_no_trade=0.1, confidence=0.75),
        ModelOutput(model="transformer", version="v1", symbol="BTCUSDT", timeframe="15", timestamp=datetime.utcnow(),
                    prediction=SignalDirection.LONG, probability_long=0.85, probability_short=0.05, probability_no_trade=0.1, confidence=0.85),
        ModelOutput(model="arima", version="v1", symbol="BTCUSDT", timeframe="15", timestamp=datetime.utcnow(),
                    prediction=SignalDirection.SHORT, probability_long=0.2, probability_short=0.6, probability_no_trade=0.2, confidence=0.6),
    ]

    weights = {"xgboost": 0.3, "lightgbm": 0.3, "transformer": 0.3, "arima": 0.1}
    res = consensus.calculate(outputs_bullish, weights)

    assert res["direction"] == SignalDirection.LONG
    assert res["model_agreement"] == 0.75
    assert res["confidence"] > 0.70

    # 2. Conflicted agreement (2 LONG, 2 SHORT = 50% < 70% min required)
    outputs_conflicted = [
        outputs_bullish[0],
        outputs_bullish[1],
        ModelOutput(model="transformer", version="v1", symbol="BTCUSDT", timeframe="15", timestamp=datetime.utcnow(),
                    prediction=SignalDirection.SHORT, probability_long=0.1, probability_short=0.8, probability_no_trade=0.1, confidence=0.8),
        outputs_bullish[3],
    ]
    res_conflict = consensus.calculate(outputs_conflicted, weights)
    # Should force NO_TRADE due to lack of consensus
    assert res_conflict["direction"] == SignalDirection.NO_TRADE


def np_sum_close(vals: list[float], target: float) -> bool:
    import numpy as np
    return bool(np.isclose(sum(vals), target, atol=1e-3))
