"""
tests/unit/test_models.py
──────────────────────────
Unit tests for Machine Learning models and rule-based baselines.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from app.core.constants import SignalDirection
from app.features.pipeline import FeaturePipeline
from app.models.lightgbm_model import HAS_LIGHTGBM, LightGBMModel
from app.models.logistic import LogisticModel
from app.models.random_forest import RandomForestModel
from app.models.technical import TechnicalModel
from app.models.xgboost_model import XGBoostModel
from app.prediction.labels import generate_labels, select_primary_label


@pytest.fixture
def dataset_ready(synthetic_candles_df: pd.DataFrame):
    pipeline = FeaturePipeline()
    df_feat = pipeline.compute(synthetic_candles_df)
    df_labeled = generate_labels(df_feat)
    y = select_primary_label(df_labeled)
    X, _ = pipeline.get_feature_matrix(df_labeled)
    return X, y


def test_xgboost_training_and_predict(dataset_ready):
    X, y = dataset_ready
    split = int(len(X) * 0.8)
    X_train, y_train = X.iloc[:split], y.iloc[:split]
    X_test = X.iloc[split:]

    model = XGBoostModel(version="test_v1")
    train_metrics = model.train(X_train, y_train)

    assert model.is_trained
    assert "accuracy" in train_metrics

    output = model.predict(X_test, symbol="BTCUSDT", timeframe="15")
    assert output.model == "xgboost"
    assert output.prediction in (SignalDirection.LONG, SignalDirection.SHORT, SignalDirection.NO_TRADE)
    assert 0.0 <= output.confidence <= 1.0
    assert np.isclose(
        output.probability_long + output.probability_short + output.probability_no_trade,
        1.0,
        atol=1e-3,
    )

    # Test persistence (save/load)
    with tempfile.TemporaryDirectory() as tmpdir:
        save_path = Path(tmpdir)
        model.save(save_path)
        loaded_model = XGBoostModel(version="test_v1")
        loaded_model.load(save_path)
        assert loaded_model.is_trained
        loaded_output = loaded_model.predict(X_test, symbol="BTCUSDT", timeframe="15")
        assert loaded_output.prediction == output.prediction


@pytest.mark.skipif(not HAS_LIGHTGBM, reason="LightGBM not installed in test environment")
def test_lightgbm_training_and_predict(dataset_ready):
    X, y = dataset_ready
    split = int(len(X) * 0.8)
    X_train, y_train = X.iloc[:split], y.iloc[:split]
    X_test = X.iloc[split:]

    model = LightGBMModel(version="test_lgb")
    model.train(X_train, y_train)
    assert model.is_trained

    output = model.predict(X_test, symbol="BTCUSDT", timeframe="15")
    assert output.model == "lightgbm"
    assert output.confidence >= 0.0


def test_random_forest_training_and_predict(dataset_ready):
    X, y = dataset_ready
    split = int(len(X) * 0.8)
    X_train, y_train = X.iloc[:split], y.iloc[:split]
    X_test = X.iloc[split:]

    rf = RandomForestModel(version="test_rf")
    rf.train(X_train, y_train)
    assert rf.is_trained

    output = rf.predict(X_test, symbol="BTCUSDT", timeframe="15")
    assert output.model == "random_forest"
    assert output.prediction in (SignalDirection.LONG, SignalDirection.SHORT, SignalDirection.NO_TRADE)


def test_technical_model_baseline(synthetic_candles_df: pd.DataFrame):
    pipeline = FeaturePipeline()
    df_feat = pipeline.compute(synthetic_candles_df)

    tech = TechnicalModel()
    output = tech.predict(df_feat, symbol="BTCUSDT", timeframe="15")
    assert output.model == "technical"
    assert output.prediction in (SignalDirection.LONG, SignalDirection.SHORT, SignalDirection.NO_TRADE)
    assert 0.0 <= output.confidence <= 1.0
