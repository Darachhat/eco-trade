"""
tests/unit/test_drift.py
────────────────────────
Unit tests for PSI and drift detection module.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.monitoring.drift import DriftDetector, calculate_psi


def test_psi_identical_distributions():
    np.random.seed(42)
    ref = np.random.normal(0, 1, 1000)
    cur = np.random.normal(0, 1, 1000)
    psi = calculate_psi(ref, cur)
    # PSI for identical distributions should be very close to 0 (< 0.05)
    assert psi < 0.05


def test_psi_shifted_distribution():
    np.random.seed(42)
    ref = np.random.normal(0, 1, 1000)
    cur = np.random.normal(3, 1, 1000)  # Significant mean shift
    psi = calculate_psi(ref, cur)
    # PSI for severely shifted distributions should be large (> 0.25)
    assert psi > 0.25


def test_drift_detector():
    np.random.seed(42)
    ref_df = pd.DataFrame({"feat_1": np.random.normal(0, 1, 200), "feat_2": np.random.normal(5, 2, 200)})
    cur_df = pd.DataFrame({"feat_1": np.random.normal(0, 1, 200), "feat_2": np.random.normal(15, 2, 200)})  # feat_2 shifted

    detector = DriftDetector()
    reports = detector.check_feature_drift(ref_df, cur_df)

    assert len(reports) == 2
    r_map = {r.feature_name: r for r in reports}
    assert not r_map["feat_1"].is_drifted
    assert r_map["feat_2"].is_drifted
