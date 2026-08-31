"""
app/features/statistical.py
────────────────────────────
Statistical features for ML models.
All features are timestamp-safe (rolling/lagged computations only).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def rolling_zscore(series: pd.Series, window: int = 20) -> pd.Series:
    """Rolling Z-score of a series."""
    mean = series.rolling(window=window, min_periods=window).mean()
    std = series.rolling(window=window, min_periods=window).std()
    return (series - mean) / std.replace(0, np.nan)


def rolling_skewness(series: pd.Series, window: int = 20) -> pd.Series:
    """Rolling skewness."""
    return series.rolling(window=window, min_periods=window).skew()


def rolling_kurtosis(series: pd.Series, window: int = 20) -> pd.Series:
    """Rolling kurtosis (excess kurtosis)."""
    return series.rolling(window=window, min_periods=window).kurt()


def rolling_autocorr(series: pd.Series, lag: int = 1, window: int = 20) -> pd.Series:
    """Rolling autocorrelation at a given lag."""
    return series.rolling(window=window).apply(
        lambda x: pd.Series(x).autocorr(lag=lag), raw=True
    )


def realized_volatility(log_returns: pd.Series, window: int = 20) -> pd.Series:
    """Annualized realized volatility from log returns."""
    return log_returns.rolling(window=window, min_periods=window).std() * np.sqrt(252 * 24)


def volatility_percentile(log_returns: pd.Series, window: int = 20, lookback: int = 252) -> pd.Series:
    """Percentile rank of current volatility vs past lookback."""
    rv = realized_volatility(log_returns, window)
    return rv.rolling(window=lookback, min_periods=max(window, 30)).rank(pct=True)


def volatility_regime(log_returns: pd.Series, window: int = 20) -> pd.Series:
    """
    Classify volatility regime.
    0 = low, 1 = normal, 2 = high
    """
    rv = realized_volatility(log_returns, window)
    p25 = rv.rolling(252, min_periods=30).quantile(0.25)
    p75 = rv.rolling(252, min_periods=30).quantile(0.75)
    regime = pd.Series(1, index=rv.index, dtype=float)
    regime[rv < p25] = 0.0
    regime[rv > p75] = 2.0
    return regime


def mean_reversion_score(series: pd.Series, window: int = 20) -> pd.Series:
    """
    Score measuring tendency to mean-revert.
    Negative autocorrelation → high mean reversion score.
    """
    ac = rolling_autocorr(series, lag=1, window=window)
    return -ac  # flip sign: negative AC = positive mean reversion


def momentum_persistence(series: pd.Series, window: int = 20) -> pd.Series:
    """
    Measures how persistent momentum is.
    Positive autocorrelation → trending / momentum persistence.
    """
    return rolling_autocorr(series, lag=1, window=window)


def compute_statistical_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add statistical features to a candle DataFrame.
    Expects: close, volume, log_returns_1 (from technical features)
    """
    out = df.copy()
    c = out["close"]

    # Use log_returns if available, otherwise compute
    if "log_returns_1" in out.columns:
        lr = out["log_returns_1"]
    else:
        lr = np.log(c / c.shift(1))

    # Z-score of price and returns
    out["close_zscore_20"] = rolling_zscore(c, 20)
    out["close_zscore_50"] = rolling_zscore(c, 50)
    out["returns_zscore_20"] = rolling_zscore(lr, 20)

    # Distribution shape
    out["returns_skew_20"] = rolling_skewness(lr, 20)
    out["returns_kurt_20"] = rolling_kurtosis(lr, 20)

    # Autocorrelation
    out["autocorr_1"] = rolling_autocorr(lr, lag=1, window=30)
    out["autocorr_5"] = rolling_autocorr(lr, lag=5, window=60)

    # Volatility
    out["realized_vol_20"] = realized_volatility(lr, 20)
    out["realized_vol_5"] = realized_volatility(lr, 5)
    out["vol_percentile"] = volatility_percentile(lr, 20)
    out["vol_regime"] = volatility_regime(lr, 20)
    out["vol_ratio"] = out["realized_vol_5"] / out["realized_vol_20"].replace(0, np.nan)

    # Mean reversion / momentum
    out["mean_reversion_score"] = mean_reversion_score(lr, 20)
    out["momentum_persistence"] = momentum_persistence(lr, 20)

    # Rolling statistics of returns
    for window in [5, 10, 20, 50]:
        out[f"returns_mean_{window}"] = lr.rolling(window).mean()
        out[f"returns_std_{window}"] = lr.rolling(window).std()
        out[f"returns_min_{window}"] = lr.rolling(window).min()
        out[f"returns_max_{window}"] = lr.rolling(window).max()

    return out
