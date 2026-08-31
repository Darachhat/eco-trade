"""
app/monitoring/drift.py
────────────────────────
Data and Model Drift Detection Framework.

Monitors:
- Population Stability Index (PSI) for feature distribution drift.
- Kolmogorov-Smirnov (KS) tests for statistical shift.
- Prediction distribution shifts (e.g. sudden extreme bias to LONG/SHORT).
- Rolling accuracy, F1, and Brier calibration decay.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats

from app.core.logging import get_logger

logger = get_logger("model")


@dataclass
class FeatureDriftReport:
    feature_name: str
    psi_value: float
    ks_statistic: float
    ks_pvalue: float
    is_drifted: bool
    severity: str  # "NONE" | "MODERATE" | "SEVERE"


@dataclass
class DriftSummary:
    timestamp: datetime
    total_features_checked: int
    drifted_features: list[FeatureDriftReport]
    prediction_drift_detected: bool
    performance_drift_detected: bool
    requires_retraining: bool
    details: dict = field(default_factory=dict)


def calculate_psi(reference: np.ndarray, current: np.ndarray, num_buckets: int = 10) -> float:
    """
    Calculate Population Stability Index (PSI) between baseline and current data.

    PSI < 0.10: No significant change
    0.10 <= PSI < 0.25: Moderate change / slight drift
    PSI >= 0.25: Significant change / severe drift
    """
    reference = reference[~np.isnan(reference)]
    current = current[~np.isnan(current)]

    if len(reference) == 0 or len(current) == 0:
        return 0.0

    # Determine quantile bins from reference distribution
    quantiles = np.linspace(0, 100, num_buckets + 1)
    bins = np.percentile(reference, quantiles)
    bins[0] -= 1e-5
    bins[-1] += 1e-5
    bins = np.unique(bins)

    if len(bins) < 2:
        return 0.0

    ref_counts, _ = np.histogram(reference, bins=bins)
    cur_counts, _ = np.histogram(current, bins=bins)

    # Convert to fractions and add small epsilon to avoid division by zero
    eps = 1e-4
    ref_pct = (ref_counts / len(reference)) + eps
    cur_pct = (cur_counts / len(current)) + eps

    # Normalize back
    ref_pct /= np.sum(ref_pct)
    cur_pct /= np.sum(cur_pct)

    psi_value = np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct))
    return float(psi_value)


class DriftDetector:
    """
    Monitors data and model drift against baseline distributions.
    """

    def __init__(
        self,
        psi_threshold_moderate: float = 0.10,
        psi_threshold_severe: float = 0.25,
        ks_alpha: float = 0.01,
    ) -> None:
        self.psi_threshold_moderate = psi_threshold_moderate
        self.psi_threshold_severe = psi_threshold_severe
        self.ks_alpha = ks_alpha

    def check_feature_drift(
        self,
        reference_df: pd.DataFrame,
        current_df: pd.DataFrame,
        feature_cols: Optional[list[str]] = None,
    ) -> list[FeatureDriftReport]:
        """
        Evaluate feature distribution shift using PSI and KS-test.
        """
        cols = feature_cols or [c for c in reference_df.columns if c in current_df.columns and np.issubdtype(reference_df[c].dtype, np.number)]
        reports: list[FeatureDriftReport] = []

        for col in cols:
            ref_vals = reference_df[col].dropna().values.astype(np.float64)
            cur_vals = current_df[col].dropna().values.astype(np.float64)

            if len(ref_vals) < 30 or len(cur_vals) < 30:
                continue

            psi = calculate_psi(ref_vals, cur_vals)
            ks_res = stats.ks_2samp(ref_vals, cur_vals)
            ks_stat = float(ks_res.statistic)
            ks_pval = float(ks_res.pvalue)

            if psi >= self.psi_threshold_severe:
                severity = "SEVERE"
                is_drifted = True
            elif psi >= self.psi_threshold_moderate:
                severity = "MODERATE"
                is_drifted = True
            else:
                severity = "NONE"
                is_drifted = False

            reports.append(
                FeatureDriftReport(
                    feature_name=col,
                    psi_value=round(psi, 4),
                    ks_statistic=round(ks_stat, 4),
                    ks_pvalue=round(ks_pval, 6),
                    is_drifted=is_drifted,
                    severity=severity,
                )
            )

        return reports

    def check_prediction_drift(
        self,
        historical_predictions: list[str],
        recent_predictions: list[str],
        max_class_shift: float = 0.35,
    ) -> bool:
        """
        Detect sudden extreme bias in model predictions.
        (e.g., historical predictions are balanced, but recent predictions are 90% LONG).
        """
        if len(historical_predictions) < 50 or len(recent_predictions) < 20:
            return False

        hist_counts = pd.Series(historical_predictions).value_counts(normalize=True)
        rec_counts = pd.Series(recent_predictions).value_counts(normalize=True)

        for label in ["LONG", "SHORT", "NO_TRADE"]:
            hist_freq = hist_counts.get(label, 0.0)
            rec_freq = rec_counts.get(label, 0.0)
            if abs(rec_freq - hist_freq) > max_class_shift:
                logger.warning(
                    f"Prediction drift detected for {label}: Hist={hist_freq:.1%}, Recent={rec_freq:.1%}"
                )
                return True

        return False

    def evaluate_drift(
        self,
        reference_features: pd.DataFrame,
        current_features: pd.DataFrame,
        historical_preds: list[str],
        recent_preds: list[str],
        rolling_win_rate: Optional[float] = None,
        expected_win_rate: float = 0.55,
    ) -> DriftSummary:
        """
        Comprehensive drift assessment combining feature, prediction, and performance checks.
        """
        feat_reports = self.check_feature_drift(reference_features, current_features)
        severe_drifts = [r for r in feat_reports if r.severity == "SEVERE"]
        moderate_drifts = [r for r in feat_reports if r.severity == "MODERATE"]

        pred_drift = self.check_prediction_drift(historical_preds, recent_preds)

        perf_drift = False
        if rolling_win_rate is not None and rolling_win_rate < (expected_win_rate - 0.15):
            # Win rate degraded by > 15%
            perf_drift = True
            logger.warning(
                f"Model performance drift detected! Current WinRate={rolling_win_rate:.1%}, Expected={expected_win_rate:.1%}"
            )

        # Trigger retraining if: > 3 severe feature drifts OR prediction drift + performance decay
        requires_retrain = len(severe_drifts) >= 3 or (pred_drift and perf_drift) or (perf_drift)

        summary = DriftSummary(
            timestamp=datetime.utcnow(),
            total_features_checked=len(feat_reports),
            drifted_features=[r for r in feat_reports if r.is_drifted],
            prediction_drift_detected=pred_drift,
            performance_drift_detected=perf_drift,
            requires_retraining=requires_retrain,
            details={
                "severe_feature_drifts": [r.feature_name for r in severe_drifts],
                "moderate_feature_drifts": [r.feature_name for r in moderate_drifts],
                "rolling_win_rate": rolling_win_rate,
            },
        )

        logger.info(
            "Drift evaluation completed",
            severe_drifts=len(severe_drifts),
            moderate_drifts=len(moderate_drifts),
            prediction_drift=pred_drift,
            performance_drift=perf_drift,
            requires_retraining=requires_retrain,
        )

        return summary
