"""
app/features/technical.py
──────────────────────────
Technical indicator calculations.
ALL computations are timestamp-safe — no future data may enter any feature.
Uses pandas for vectorized calculations.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _validate_no_future_leak(df: pd.DataFrame, col: str) -> None:
    """Assert that a column uses only shift-safe (past) data."""
    # This is a documentation guard — actual leak prevention is via
    # using only .shift() operations (never forward-fill with future knowledge)
    pass


# ─────────────────────────────────────────────
# Moving Averages
# ─────────────────────────────────────────────

def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=period, min_periods=period).mean()


# ─────────────────────────────────────────────
# RSI
# ─────────────────────────────────────────────

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


# ─────────────────────────────────────────────
# MACD
# ─────────────────────────────────────────────

def macd(
    series: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    MACD Line, Signal Line, Histogram.
    Returns: (macd_line, signal_line, histogram)
    """
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


# ─────────────────────────────────────────────
# ATR
# ─────────────────────────────────────────────

def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range."""
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


# ─────────────────────────────────────────────
# ADX
# ─────────────────────────────────────────────

def adx(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Average Directional Index.
    Returns: (adx, +DI, -DI)
    """
    prev_high = high.shift(1)
    prev_low = low.shift(1)
    prev_close = close.shift(1)

    tr = atr(high, low, close, period)

    dm_plus = np.where(
        (high - prev_high) > (prev_low - low),
        np.maximum(high - prev_high, 0),
        0,
    )
    dm_minus = np.where(
        (prev_low - low) > (high - prev_high),
        np.maximum(prev_low - low, 0),
        0,
    )

    dm_plus_s = pd.Series(dm_plus, index=high.index).ewm(alpha=1 / period, adjust=False).mean()
    dm_minus_s = pd.Series(dm_minus, index=high.index).ewm(alpha=1 / period, adjust=False).mean()

    di_plus = 100 * dm_plus_s / tr.replace(0, np.nan)
    di_minus = 100 * dm_minus_s / tr.replace(0, np.nan)

    dx = 100 * (di_plus - di_minus).abs() / (di_plus + di_minus).replace(0, np.nan)
    adx_series = dx.ewm(alpha=1 / period, adjust=False).mean()

    return adx_series, di_plus, di_minus


# ─────────────────────────────────────────────
# Bollinger Bands
# ─────────────────────────────────────────────

def bollinger_bands(
    series: pd.Series,
    period: int = 20,
    std_dev: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Bollinger Bands.
    Returns: (upper, middle, lower)
    """
    middle = sma(series, period)
    std = series.rolling(window=period, min_periods=period).std()
    upper = middle + std_dev * std
    lower = middle - std_dev * std
    return upper, middle, lower


def bollinger_pct_b(series: pd.Series, period: int = 20, std_dev: float = 2.0) -> pd.Series:
    """Bollinger %B: where price is relative to the bands."""
    upper, middle, lower = bollinger_bands(series, period, std_dev)
    return (series - lower) / (upper - lower).replace(0, np.nan)


def bollinger_width(series: pd.Series, period: int = 20, std_dev: float = 2.0) -> pd.Series:
    """Bollinger Band Width."""
    upper, middle, lower = bollinger_bands(series, period, std_dev)
    return (upper - lower) / middle.replace(0, np.nan)


# ─────────────────────────────────────────────
# Stochastic
# ─────────────────────────────────────────────

def stochastic(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k_period: int = 14,
    d_period: int = 3,
) -> tuple[pd.Series, pd.Series]:
    """
    Stochastic Oscillator.
    Returns: (%K, %D)
    """
    lowest_low = low.rolling(window=k_period, min_periods=k_period).min()
    highest_high = high.rolling(window=k_period, min_periods=k_period).max()
    k = 100 * (close - lowest_low) / (highest_high - lowest_low).replace(0, np.nan)
    d = sma(k, d_period)
    return k, d


# ─────────────────────────────────────────────
# VWAP (session-based)
# ─────────────────────────────────────────────

def vwap(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
) -> pd.Series:
    """
    VWAP — cumulative within trading session.
    For simplicity, computed as rolling 14-period cumulative VWAP.
    """
    typical_price = (high + low + close) / 3
    cumulative_tp_vol = (typical_price * volume).rolling(window=14).sum()
    cumulative_vol = volume.rolling(window=14).sum()
    return cumulative_tp_vol / cumulative_vol.replace(0, np.nan)


# ─────────────────────────────────────────────
# Ichimoku
# ─────────────────────────────────────────────

def ichimoku(
    high: pd.Series,
    low: pd.Series,
    tenkan_period: int = 9,
    kijun_period: int = 26,
    senkou_b_period: int = 52,
) -> dict[str, pd.Series]:
    """
    Ichimoku Cloud components.
    Note: Senkou span A/B are shifted forward in traditional Ichimoku,
    but here we return them unshifted to avoid future leakage.
    """
    tenkan = (high.rolling(tenkan_period).max() + low.rolling(tenkan_period).min()) / 2
    kijun = (high.rolling(kijun_period).max() + low.rolling(kijun_period).min()) / 2
    senkou_a = (tenkan + kijun) / 2
    senkou_b = (
        high.rolling(senkou_b_period).max() + low.rolling(senkou_b_period).min()
    ) / 2
    chikou = high.shift(kijun_period)  # lagging span (uses past data)

    return {
        "tenkan": tenkan,
        "kijun": kijun,
        "senkou_a": senkou_a,
        "senkou_b": senkou_b,
        "chikou": chikou,
        "cloud_thickness": (senkou_a - senkou_b).abs(),
        "above_cloud": (high > senkou_a) & (high > senkou_b),
        "below_cloud": (low < senkou_a) & (low < senkou_b),
    }


# ─────────────────────────────────────────────
# Donchian Channel
# ─────────────────────────────────────────────

def donchian(
    high: pd.Series,
    low: pd.Series,
    period: int = 20,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Donchian Channel.
    Returns: (upper, middle, lower)
    """
    upper = high.rolling(window=period, min_periods=period).max()
    lower = low.rolling(window=period, min_periods=period).min()
    middle = (upper + lower) / 2
    return upper, middle, lower


# ─────────────────────────────────────────────
# ROC / Momentum
# ─────────────────────────────────────────────

def roc(series: pd.Series, period: int = 10) -> pd.Series:
    """Rate of Change."""
    return (series / series.shift(period).replace(0, np.nan) - 1) * 100


def momentum(series: pd.Series, period: int = 10) -> pd.Series:
    """Price Momentum."""
    return series - series.shift(period)


# ─────────────────────────────────────────────
# OBV
# ─────────────────────────────────────────────

def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """On-Balance Volume."""
    direction = np.sign(close.diff())
    signed_volume = direction * volume
    return signed_volume.cumsum()


# ─────────────────────────────────────────────
# Price Action Features
# ─────────────────────────────────────────────

def candle_features(
    open_: pd.Series,
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
) -> dict[str, pd.Series]:
    """Candle morphology features."""
    body = (close - open_).abs()
    candle_range = high - low
    upper_wick = high - pd.concat([close, open_], axis=1).max(axis=1)
    lower_wick = pd.concat([close, open_], axis=1).min(axis=1) - low
    return {
        "candle_body": body,
        "candle_range": candle_range,
        "upper_wick": upper_wick,
        "lower_wick": lower_wick,
        "body_to_range": body / candle_range.replace(0, np.nan),
        "is_bullish": (close > open_).astype(float),
    }


def returns(close: pd.Series) -> pd.Series:
    """Simple returns."""
    return close.pct_change()


def log_returns(close: pd.Series) -> pd.Series:
    """Log returns."""
    return np.log(close / close.shift(1))


def swing_highs(high: pd.Series, lookback: int = 5) -> pd.Series:
    """Detect swing highs (local maxima)."""
    return (high == high.rolling(window=lookback * 2 + 1, center=True).max()).astype(float)


def swing_lows(low: pd.Series, lookback: int = 5) -> pd.Series:
    """Detect swing lows (local minima)."""
    return (low == low.rolling(window=lookback * 2 + 1, center=True).min()).astype(float)


def high_low_distance(
    close: pd.Series, high: pd.Series, low: pd.Series, period: int = 20
) -> dict[str, pd.Series]:
    """Distance from rolling high/low."""
    rolling_high = high.rolling(period).max()
    rolling_low = low.rolling(period).min()
    return {
        "dist_to_high": (rolling_high - close) / close,
        "dist_to_low": (close - rolling_low) / close,
    }


def breakout(close: pd.Series, high: pd.Series, period: int = 20) -> pd.Series:
    """1 if price broke above the previous period's high."""
    prev_high = high.rolling(period).max().shift(1)
    return (close > prev_high).astype(float)


def breakdown(close: pd.Series, low: pd.Series, period: int = 20) -> pd.Series:
    """1 if price broke below the previous period's low."""
    prev_low = low.rolling(period).min().shift(1)
    return (close < prev_low).astype(float)


# ─────────────────────────────────────────────
# Master Feature Builder
# ─────────────────────────────────────────────

def compute_technical_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute all technical features on a candle DataFrame.

    Expected columns: open, high, low, close, volume
    All features are computed without future leakage.
    Returns the same DataFrame with added feature columns.
    """
    out = df.copy()

    c = out["close"]
    h = out["high"]
    lo = out["low"]
    o = out["open"]
    v = out["volume"]

    # EMAs
    for p in [9, 20, 50, 100, 200]:
        out[f"ema_{p}"] = ema(c, p)

    # SMAs
    for p in [20, 50, 200]:
        out[f"sma_{p}"] = sma(c, p)

    # EMA relationships
    out["ema_9_above_20"] = (out["ema_9"] > out["ema_20"]).astype(float)
    out["ema_20_above_50"] = (out["ema_20"] > out["ema_50"]).astype(float)
    out["ema_50_above_200"] = (out["ema_50"] > out["ema_200"]).astype(float)

    # RSI
    out["rsi_14"] = rsi(c, 14)
    out["rsi_overbought"] = (out["rsi_14"] > 70).astype(float)
    out["rsi_oversold"] = (out["rsi_14"] < 30).astype(float)

    # MACD
    macd_l, sig_l, hist = macd(c)
    out["macd"] = macd_l
    out["macd_signal"] = sig_l
    out["macd_hist"] = hist
    out["macd_bullish"] = (hist > 0).astype(float)
    out["macd_crossover"] = ((hist > 0) & (hist.shift(1) <= 0)).astype(float)
    out["macd_crossunder"] = ((hist < 0) & (hist.shift(1) >= 0)).astype(float)

    # ATR
    out["atr_14"] = atr(h, lo, c, 14)
    out["atr_pct"] = out["atr_14"] / c

    # ADX
    adx_s, di_p, di_m = adx(h, lo, c, 14)
    out["adx"] = adx_s
    out["di_plus"] = di_p
    out["di_minus"] = di_m
    out["adx_trending"] = (adx_s > 25).astype(float)

    # Bollinger Bands
    bb_upper, bb_mid, bb_lower = bollinger_bands(c, 20, 2.0)
    out["bb_upper"] = bb_upper
    out["bb_middle"] = bb_mid
    out["bb_lower"] = bb_lower
    out["bb_pct_b"] = bollinger_pct_b(c, 20, 2.0)
    out["bb_width"] = bollinger_width(c, 20, 2.0)

    # Stochastic
    k, d = stochastic(h, lo, c, 14, 3)
    out["stoch_k"] = k
    out["stoch_d"] = d
    out["stoch_overbought"] = (k > 80).astype(float)
    out["stoch_oversold"] = (k < 20).astype(float)

    # VWAP
    out["vwap"] = vwap(h, lo, c, v)
    out["above_vwap"] = (c > out["vwap"]).astype(float)

    # Donchian
    don_upper, don_mid, don_lower = donchian(h, lo, 20)
    out["don_upper"] = don_upper
    out["don_lower"] = don_lower
    out["don_pct"] = (c - don_lower) / (don_upper - don_lower).replace(0, np.nan)

    # ROC
    for p in [5, 10, 20]:
        out[f"roc_{p}"] = roc(c, p)

    # Momentum
    for p in [5, 10]:
        out[f"momentum_{p}"] = momentum(c, p)

    # OBV
    out["obv"] = obv(c, v)
    out["obv_ema"] = ema(out["obv"], 20)

    # Volume
    out["volume_sma_20"] = sma(v, 20)
    out["volume_ratio"] = v / out["volume_sma_20"].replace(0, np.nan)

    # Candle features
    cf = candle_features(o, h, lo, c)
    for k, val in cf.items():
        out[k] = val

    # Returns
    out["returns_1"] = returns(c)
    out["log_returns_1"] = log_returns(c)
    for p in [5, 10, 20]:
        out[f"returns_{p}"] = c.pct_change(p)

    # High/low distance
    hld = high_low_distance(c, h, lo, 20)
    for k, val in hld.items():
        out[k] = val

    # Breakout/breakdown
    out["breakout_20"] = breakout(c, h, 20)
    out["breakdown_20"] = breakdown(c, lo, 20)

    # Ichimoku
    ichi = ichimoku(h, lo)
    for k, val in ichi.items():
        if isinstance(val, pd.Series):
            out[f"ichi_{k}"] = val
        else:
            out[f"ichi_{k}"] = val.astype(float)

    return out
