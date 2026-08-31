"""
app/features/derivatives.py
─────────────────────────────
Derivatives market features: funding rate, open interest, their relationships.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def compute_derivatives_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add derivatives features to a DataFrame.
    Expects columns: close, funding_rate, open_interest (may be NaN if unavailable).
    """
    out = df.copy()

    if "funding_rate" in out.columns:
        fr = out["funding_rate"]
        out["funding_rate_abs"] = fr.abs()
        out["funding_rate_positive"] = (fr > 0).astype(float)
        out["funding_rate_extreme"] = (fr.abs() > 0.001).astype(float)  # > 0.1% per 8h
        out["funding_rate_zscore"] = (fr - fr.rolling(48).mean()) / fr.rolling(48).std().replace(0, np.nan)
        out["funding_rate_ma"] = fr.rolling(8).mean()

    if "open_interest" in out.columns:
        oi = out["open_interest"]
        out["oi_change_1"] = oi.pct_change(1)
        out["oi_change_5"] = oi.pct_change(5)
        out["oi_ma"] = oi.rolling(20).mean()
        out["oi_zscore"] = (oi - out["oi_ma"]) / oi.rolling(20).std().replace(0, np.nan)

        if "close" in out.columns:
            c = out["close"]
            # Price/OI divergence: price rises but OI falls = weakening move
            price_dir = c.pct_change(5)
            oi_dir = oi.pct_change(5)
            out["price_oi_divergence"] = np.sign(price_dir) * np.sign(oi_dir)  # +1 confirm, -1 diverge
            out["long_squeeze_risk"] = (
                (c < c.shift(1)) & (oi > oi.shift(1))
            ).astype(float)  # price down but OI up = more shorts, potential short squeeze squeeze signal
            out["short_squeeze_risk"] = (
                (c > c.shift(1)) & (oi > oi.shift(1))
            ).astype(float)

    return out
