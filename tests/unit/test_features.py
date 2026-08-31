"""
tests/unit/test_features.py
────────────────────────────
Unit tests for technical, statistical, derivatives, and orderbook features.
Crucially tests that no lookahead bias / future data leakage occurs.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.features.orderbook import orderbook_features
from app.features.pipeline import FeaturePipeline
from app.features.technical import ema, rsi, macd, atr, bollinger_bands


def test_technical_indicators_calculation(synthetic_candles_df: pd.DataFrame):
    df = synthetic_candles_df
    close = df["close"]
    high = df["high"]
    low = df["low"]

    # 1. EMA
    ema20 = ema(close, 20)
    assert len(ema20) == len(close)
    assert not ema20.isna().all()

    # 2. RSI
    rsi14 = rsi(close, 14)
    assert len(rsi14) == len(close)
    valid_rsi = rsi14.dropna()
    assert (valid_rsi >= 0.0).all() and (valid_rsi <= 100.0).all()

    # 3. MACD
    macd_line, sig_line, hist = macd(close)
    assert len(macd_line) == len(close)
    assert np.isclose((macd_line - sig_line).iloc[-1], hist.iloc[-1])

    # 4. ATR
    atr14 = atr(high, low, close, 14)
    assert (atr14.dropna() > 0).all()

    # 5. Bollinger Bands
    upper, mid, lower = bollinger_bands(close, 20, 2.0)
    valid_mask = ~upper.isna()
    assert (upper[valid_mask] >= mid[valid_mask]).all()
    assert (mid[valid_mask] >= lower[valid_mask]).all()


def test_feature_pipeline_no_future_leak(synthetic_candles_df: pd.DataFrame):
    """
    CRITICAL TEST: Ensure that modifying future rows (after cut_time)
    does NOT alter the computed features at or before cut_time.
    """
    df1 = synthetic_candles_df.copy()
    pipeline = FeaturePipeline()
    features1 = pipeline.compute(df1)

    cut_idx = 300
    target_time = df1.loc[cut_idx, "open_time"]

    # Create modified dataset where ALL data AFTER cut_time is drastically altered
    df2 = synthetic_candles_df.copy()
    df2.loc[df2["open_time"] > target_time, "close"] *= 5.0
    df2.loc[df2["open_time"] > target_time, "high"] *= 5.0
    df2.loc[df2["open_time"] > target_time, "low"] *= 5.0
    df2.loc[df2["open_time"] > target_time, "volume"] *= 100.0

    features2 = pipeline.compute(df2)

    # Compare the exact row with open_time == target_time
    row1 = features1[features1["open_time"] == target_time].iloc[0].to_dict()
    row2 = features2[features2["open_time"] == target_time].iloc[0].to_dict()

    # Check all engineered feature columns
    for feat in pipeline.feature_columns:
        val1 = row1[feat]
        val2 = row2[feat]
        if isinstance(val1, (float, np.floating)) and np.isnan(val1):
            assert np.isnan(val2), f"Feature {feat} changed NaN status"
        elif isinstance(val1, (int, float, np.number)):
            assert np.isclose(val1, val2, atol=1e-5), f"Future leakage detected in feature {feat}: {val1} != {val2}"


def test_orderbook_features(sample_orderbook):
    ob_feats = orderbook_features(sample_orderbook)
    assert "bid_volume" in ob_feats
    assert "ask_volume" in ob_feats
    assert "imbalance" in ob_feats
    assert "spread" in ob_feats
    assert ob_feats["spread"] > 0
    assert -1.0 <= ob_feats["imbalance"] <= 1.0
