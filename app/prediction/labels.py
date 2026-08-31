"""
app/prediction/labels.py
─────────────────────────
Trading-oriented label generation.

Labels are NOT simple next-candle UP/DOWN.
They represent realistic trade outcomes:
  - LONG_SUCCESS (1): TP reached before SL
  - SHORT_SUCCESS (2): TP (downside) reached before SL  
  - NO_TRADE (0): Neither TP nor SL reached in horizon

CRITICAL: Labels are generated using ONLY future data that is
explicitly acknowledged as the "look-ahead window" for labeling.
At inference time, this future window is NOT available.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.core.logging import get_logger

logger = get_logger("model")

# Label encoding
LABEL_NO_TRADE = 0
LABEL_LONG = 1
LABEL_SHORT = 2


def generate_labels(
    df: pd.DataFrame,
    atr_multiplier_tp: float = 2.0,
    atr_multiplier_sl: float = 1.0,
    horizons: list[int] | None = None,
) -> pd.DataFrame:
    """
    Generate multi-horizon trading labels for a candle DataFrame.

    For each candle at time T:
    - Define entry = close[T]
    - Define SL = entry - ATR * sl_multiplier (for LONG)
    - Define TP = entry + ATR * tp_multiplier (for LONG)
    - Simulate over the next N candles
    - Label = LONG (1) if TP hit first, SHORT (2) if SL hit first, NO_TRADE (0) otherwise

    Returns:
        DataFrame with added columns: label_h{N} for each horizon N
    """
    if horizons is None:
        horizons = [5, 10, 20, 50]

    required = {"close", "high", "low", "atr_14"}
    if not required.issubset(df.columns):
        logger.warning("Label generation missing required columns", missing=required - set(df.columns))
        return df

    out = df.copy()

    for horizon in horizons:
        labels = _generate_for_horizon(out, horizon, atr_multiplier_tp, atr_multiplier_sl)
        out[f"label_h{horizon}"] = labels

    return out


def _generate_for_horizon(
    df: pd.DataFrame,
    horizon: int,
    tp_mult: float,
    sl_mult: float,
) -> pd.Series:
    """
    Generate labels for a single horizon.

    This uses FORWARD data — it is ONLY used for historical labeling.
    At inference time, the model receives features from T, not labels.
    """
    n = len(df)
    labels = np.zeros(n, dtype=np.int32)

    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    atr = df["atr_14"].values

    for i in range(n - horizon):
        entry = close[i]
        atr_val = atr[i]
        if np.isnan(atr_val) or atr_val == 0:
            labels[i] = LABEL_NO_TRADE
            continue

        long_tp = entry + atr_val * tp_mult
        long_sl = entry - atr_val * sl_mult
        short_tp = entry - atr_val * tp_mult
        short_sl = entry + atr_val * sl_mult

        long_result = _simulate(high[i+1:i+1+horizon], low[i+1:i+1+horizon], long_tp, long_sl, direction="long")
        short_result = _simulate(high[i+1:i+1+horizon], low[i+1:i+1+horizon], short_tp, short_sl, direction="short")

        if long_result == "tp" and short_result != "tp":
            labels[i] = LABEL_LONG
        elif short_result == "tp" and long_result != "tp":
            labels[i] = LABEL_SHORT
        else:
            labels[i] = LABEL_NO_TRADE

    # Last 'horizon' rows can't be labeled (no future data)
    labels[n - horizon:] = LABEL_NO_TRADE

    return pd.Series(labels, index=df.index)


def _simulate(
    high: np.ndarray,
    low: np.ndarray,
    tp: float,
    sl: float,
    direction: str,
) -> str:
    """
    Simulate a trade over a window of candles.
    Returns: 'tp', 'sl', or 'neither'
    """
    for h, l in zip(high, low):
        if direction == "long":
            if h >= tp:
                return "tp"
            if l <= sl:
                return "sl"
        else:  # short
            if l <= tp:
                return "tp"
            if h >= sl:
                return "sl"
    return "neither"


def select_primary_label(df: pd.DataFrame, primary_horizon: int = 20) -> pd.Series:
    """Select the primary label column for training."""
    col = f"label_h{primary_horizon}"
    if col not in df.columns:
        raise ValueError(f"Label column {col} not found. Run generate_labels() first.")
    return df[col]


def label_distribution(labels: pd.Series) -> dict:
    """Show class balance."""
    counts = labels.value_counts()
    total = len(labels)
    return {
        "no_trade": int(counts.get(0, 0)),
        "long": int(counts.get(1, 0)),
        "short": int(counts.get(2, 0)),
        "no_trade_pct": round(counts.get(0, 0) / total * 100, 1),
        "long_pct": round(counts.get(1, 0) / total * 100, 1),
        "short_pct": round(counts.get(2, 0) / total * 100, 1),
        "total": total,
    }
