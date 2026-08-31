"""
app/models/technical.py
────────────────────────
Rule-based technical strategy baseline.
Uses: EMA trend + RSI + MACD + ADX + support/resistance.
Benchmark for AI models — transparent and interpretable.
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


class TechnicalModel(BaseMLModel):
    """
    Rule-based strategy using classic technical analysis.

    Provides a transparent baseline to benchmark AI models against.
    Does NOT train on data — uses hard-coded rules.
    """

    def __init__(self, version: str = "v1") -> None:
        super().__init__(model_name="technical", version=version)
        self._is_trained = True  # Rule-based doesn't need training

    def train(self, X: pd.DataFrame, y: pd.Series, **kwargs: Any) -> dict:
        """Rule-based model doesn't train. Just records feature names."""
        self._feature_names = list(X.columns)
        self._is_trained = True
        return self.evaluate(X, y)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        Apply rule-based logic to generate probabilities.
        """
        if X.empty:
            return np.array([[1/3, 1/3, 1/3]])

        row = X.iloc[-1]

        bullish_signals = 0
        bearish_signals = 0
        total_signals = 0

        # ── EMA Trend ─────────────────────────────────
        if "ema_9_above_20" in X.columns:
            total_signals += 1
            bullish_signals += float(row.get("ema_9_above_20", 0.5))
            bearish_signals += 1 - float(row.get("ema_9_above_20", 0.5))

        if "ema_20_above_50" in X.columns:
            total_signals += 1
            bullish_signals += float(row.get("ema_20_above_50", 0.5))
            bearish_signals += 1 - float(row.get("ema_20_above_50", 0.5))

        if "ema_50_above_200" in X.columns:
            total_signals += 1
            bullish_signals += float(row.get("ema_50_above_200", 0.5))
            bearish_signals += 1 - float(row.get("ema_50_above_200", 0.5))

        # ── RSI ────────────────────────────────────────
        rsi = float(row.get("rsi_14", 50.0))
        total_signals += 2
        if rsi > 60:
            bullish_signals += 2
        elif rsi < 40:
            bearish_signals += 2
        elif rsi > 50:
            bullish_signals += 1
            bearish_signals += 0.5
        else:
            bearish_signals += 1
            bullish_signals += 0.5

        # ── MACD ────────────────────────────────────────
        if "macd_bullish" in X.columns:
            total_signals += 2
            if float(row.get("macd_bullish", 0.5)) > 0.5:
                bullish_signals += 2
            else:
                bearish_signals += 2

        if "macd_crossover" in X.columns:
            total_signals += 1
            crossover = float(row.get("macd_crossover", 0))
            crossunder = float(row.get("macd_crossunder", 0))
            if crossover > 0.5:
                bullish_signals += 1
            elif crossunder > 0.5:
                bearish_signals += 1

        # ── ADX (trend strength filter) ─────────────────
        adx_val = float(row.get("adx", 20.0))
        adx_weight = min(adx_val / 25.0, 1.5)  # Scale: weak=0.4x, strong=1.5x

        # ── Stochastic ──────────────────────────────────
        stoch_k = float(row.get("stoch_k", 50.0))
        total_signals += 1
        if stoch_k > 80 and bullish_signals > bearish_signals:
            bearish_signals += 1  # Overbought during uptrend → caution
        elif stoch_k < 20 and bearish_signals > bullish_signals:
            bullish_signals += 1  # Oversold during downtrend → caution
        elif stoch_k > 55:
            bullish_signals += 1
        elif stoch_k < 45:
            bearish_signals += 1

        # ── VWAP ────────────────────────────────────────
        if "above_vwap" in X.columns:
            total_signals += 1
            if float(row.get("above_vwap", 0.5)) > 0.5:
                bullish_signals += 1
            else:
                bearish_signals += 1

        # ── Calculate probabilities ──────────────────────
        if total_signals == 0:
            return np.array([[1/3, 1/3, 1/3]])

        bull_ratio = bullish_signals / total_signals * adx_weight
        bear_ratio = bearish_signals / total_signals * adx_weight

        # Threshold: need >65% agreement
        if bull_ratio > 0.65:
            p_long = min(bull_ratio * 0.8, 0.85)
            p_short = (1 - p_long) * 0.2
            p_no_trade = 1 - p_long - p_short
        elif bear_ratio > 0.65:
            p_short = min(bear_ratio * 0.8, 0.85)
            p_long = (1 - p_short) * 0.2
            p_no_trade = 1 - p_long - p_short
        else:
            # Conflicting signals — NO TRADE
            p_no_trade = 0.7
            p_long = 0.15
            p_short = 0.15

        # Normalize
        total = p_long + p_short + p_no_trade
        return np.array([[p_no_trade / total, p_long / total, p_short / total]])

    def save(self, path: Path) -> None:
        """Rule-based model has nothing to save except metadata."""
        path.mkdir(parents=True, exist_ok=True)
        with open(path / f"technical_{self.version}.pkl", "wb") as f:
            pickle.dump({"version": self.version, "features": self._feature_names}, f)

    def load(self, path: Path) -> None:
        model_path = path / f"technical_{self.version}.pkl"
        if model_path.exists():
            with open(model_path, "rb") as f:
                d = pickle.load(f)
            self._feature_names = d.get("features", [])
        self._is_trained = True
