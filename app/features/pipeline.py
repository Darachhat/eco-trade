"""
app/features/pipeline.py
─────────────────────────
Versioned feature pipeline orchestrator.

Responsibilities:
- Accept raw candle DataFrames
- Apply all feature generators in order
- Validate no future leakage
- Version the pipeline (v1, v2, ...)
- Return feature-enriched DataFrames
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

from app.core.constants import FEATURE_VERSION
from app.core.logging import get_logger
from app.features.derivatives import compute_derivatives_features
from app.features.statistical import compute_statistical_features
from app.features.technical import compute_technical_features

logger = get_logger("model")

# Columns that represent raw market data (not features)
RAW_COLUMNS = {
    "open", "high", "low", "close", "volume",
    "turnover", "open_time", "close_time",
    "symbol", "timeframe",
    # Optional derivatives columns (added before pipeline)
    "funding_rate", "open_interest",
}


class FeaturePipeline:
    """
    Versioned feature engineering pipeline.

    Usage:
        pipeline = FeaturePipeline(version="v1")
        df_features = pipeline.compute(df_raw)
    """

    def __init__(self, version: str = FEATURE_VERSION) -> None:
        self.version = version
        self._feature_columns: list[str] = []

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run the full feature pipeline on a candle DataFrame.

        Input: DataFrame with columns [open, high, low, close, volume, open_time, ...]
        Output: Same DataFrame with all feature columns added.

        CRITICAL: No future information enters any feature.
        """
        if df.empty:
            logger.warning("Feature pipeline received empty DataFrame")
            return df

        self._validate_input(df)

        # Apply feature generators in order
        df_out = compute_technical_features(df)
        df_out = compute_statistical_features(df_out)
        df_out = compute_derivatives_features(df_out)

        # Drop rows with insufficient history (NaN at start)
        df_out = self._drop_warmup(df_out)

        # Record feature column names (excluding raw)
        self._feature_columns = [
            col for col in df_out.columns if col not in RAW_COLUMNS
        ]

        logger.debug(
            "Feature pipeline complete",
            version=self.version,
            rows=len(df_out),
            features=len(self._feature_columns),
        )

        return df_out

    def get_feature_matrix(
        self,
        df: pd.DataFrame,
        feature_names: Optional[list[str]] = None,
    ) -> tuple[pd.DataFrame, list[str]]:
        """
        Return the feature matrix X (only feature columns, no raw data).
        If feature_names is provided, use exactly those columns.
        """
        cols = feature_names or self._feature_columns
        # Only return columns that exist in df
        valid_cols = [c for c in cols if c in df.columns]
        missing = [c for c in cols if c not in df.columns]
        if missing:
            logger.warning("Missing feature columns", missing=missing[:10])

        X = df[valid_cols].copy()
        # Replace inf values with NaN then fill
        X = X.replace([np.inf, -np.inf], np.nan)
        X = X.ffill().bfill()
        return X, valid_cols

    def _validate_input(self, df: pd.DataFrame) -> None:
        """Validate that the input DataFrame has the required columns."""
        required = {"open", "high", "low", "close", "volume"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Feature pipeline missing required columns: {missing}")

        # Validate timestamp ordering (no future leakage check)
        if "open_time" in df.columns:
            if not df["open_time"].is_monotonic_increasing:
                raise ValueError(
                    "Feature pipeline: open_time is not monotonically increasing. "
                    "Data may contain future leakage."
                )

    def _drop_warmup(self, df: pd.DataFrame, max_nan_pct: float = 0.5) -> pd.DataFrame:
        """
        Drop initial rows where too many features are NaN (warmup period).
        """
        feature_cols = [c for c in df.columns if c not in RAW_COLUMNS]
        if not feature_cols:
            return df

        nan_pct = df[feature_cols].isnull().mean(axis=1)
        # Keep rows where fewer than max_nan_pct of features are NaN
        return df[nan_pct < max_nan_pct].copy()

    @property
    def feature_columns(self) -> list[str]:
        return self._feature_columns

    @property
    def feature_count(self) -> int:
        return len(self._feature_columns)


def candles_to_dataframe(candles: list) -> pd.DataFrame:
    """
    Convert a list of Candle objects to a pandas DataFrame.
    Sets open_time as index after validation.
    """
    rows = [
        {
            "open_time": c.open_time,
            "close_time": c.close_time,
            "open": float(c.open),
            "high": float(c.high),
            "low": float(c.low),
            "close": float(c.close),
            "volume": float(c.volume),
            "turnover": float(c.turnover) if c.turnover else None,
        }
        for c in candles
    ]
    df = pd.DataFrame(rows)
    df = df.sort_values("open_time").reset_index(drop=True)
    return df


def dataframe_to_feature_rows(
    df: pd.DataFrame,
    symbol: str,
    timeframe: str,
    version: str = FEATURE_VERSION,
) -> list[dict]:
    """
    Convert a feature DataFrame to a list of dicts suitable for DB insertion.
    One row per (timestamp, feature_name).
    """
    rows = []
    feature_cols = [c for c in df.columns if c not in RAW_COLUMNS]

    for _, row in df.iterrows():
        ts = row.get("open_time")
        if ts is None:
            continue
        for feat_name in feature_cols:
            val = row.get(feat_name)
            if val is None or (isinstance(val, float) and np.isnan(val)):
                continue
            rows.append({
                "symbol": symbol,
                "timeframe": timeframe,
                "timestamp": ts,
                "feature_name": feat_name,
                "feature_value": float(val),
                "feature_version": version,
            })
    return rows
