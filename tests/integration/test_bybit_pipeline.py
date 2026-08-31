"""
tests/integration/test_bybit_pipeline.py
─────────────────────────────────────────
Integration tests covering the end-to-end data and signal pipeline:
Raw Bybit Parser -> Features -> Regime Detection -> Ensemble -> Signal Engine -> Paper Execution.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
import pytest

from app.core.constants import SignalDirection
from app.ensemble.engine import EnsembleEngine
from app.exchange.bybit.parser import parse_rest_candle, parse_ws_kline, parse_ws_orderbook
from app.execution.paper import PaperExecutionEngine
from app.features.pipeline import FeaturePipeline, candles_to_dataframe
from app.models.technical import TechnicalModel
from app.models.xgboost_model import XGBoostModel
from app.prediction.labels import generate_labels, select_primary_label
from app.regime.detector import MarketRegimeDetector
from app.strategy.signal_engine import SignalEngine


def test_bybit_parsers():
    # 1. Test REST Candle parser
    raw_rest_kline = ["1704067200000", "50000", "50500", "49800", "50200", "120.5", "6049100"]
    candle = parse_rest_candle(raw_rest_kline, symbol="BTCUSDT", timeframe="15")
    assert candle is not None
    assert candle.symbol == "BTCUSDT"
    assert candle.open == 50000.0
    assert candle.high == 50500.0

    # 2. Test WS Kline parser
    raw_ws_msg = {
        "topic": "kline.15.BTCUSDT",
        "data": [
            {
                "start": 1704067200000,
                "open": "50000",
                "high": "50500",
                "low": "49800",
                "close": "50200",
                "volume": "120.5",
                "turnover": "6049100",
                "confirm": True,
            }
        ],
    }
    ws_candles = parse_ws_kline(raw_ws_msg)
    assert len(ws_candles) == 1
    assert ws_candles[0].symbol == "BTCUSDT"
    assert ws_candles[0].close == 50200.0


@pytest.mark.asyncio
async def test_end_to_end_decision_pipeline(synthetic_candles_df):
    # 1. Feature Engineering
    pipeline = FeaturePipeline()
    df_feat = pipeline.compute(synthetic_candles_df)
    assert df_feat.shape[1] > 20

    # 2. Market Regime Detection
    regime_detector = MarketRegimeDetector()
    regime_res = regime_detector.detect(df_feat, symbol="BTCUSDT", timeframe="15")
    assert regime_res.regime is not None
    assert 0.0 <= regime_res.confidence <= 1.0

    # 3. Train a lightweight XGBoost model + Technical Baseline
    df_labeled = generate_labels(df_feat)
    y = select_primary_label(df_labeled)
    X, _ = pipeline.get_feature_matrix(df_labeled)

    xgb_model = XGBoostModel(version="int_test")
    xgb_model.train(X, y)

    tech_model = TechnicalModel()

    # 4. Ensemble Engine
    models = {"xgboost": xgb_model, "technical": tech_model}
    ensemble = EnsembleEngine(models=models)
    ens_res = ensemble.predict(X, symbol="BTCUSDT", timeframe="15", regime=str(regime_res.regime))
    assert ens_res["direction"] is not None

    # 5. Signal Engine
    sig_engine = SignalEngine()
    current_price = float(df_feat["close"].iloc[-1])
    trade_signal = sig_engine.generate(
        ensemble_result=ens_res,
        df=df_feat,
        symbol="BTCUSDT",
        timeframe="15",
        regime=regime_res,
        current_price=current_price,
    )
    assert trade_signal.symbol == "BTCUSDT"

    # 6. Paper Execution simulation
    if trade_signal.direction in (SignalDirection.LONG, SignalDirection.SHORT):
        paper = PaperExecutionEngine()
        pos = await paper.open_position(
            signal_id="SIG-INT-001",
            symbol="BTCUSDT",
            direction=trade_signal.direction.value,
            entry_price=current_price,
            qty=0.1,
            stop_loss=trade_signal.stop_loss.price,
            take_profit_1=trade_signal.take_profit.tp1,
        )
        assert pos["status"] == "OPEN"

        # Simulate price tick hitting TP1
        await paper.update_mark_price("BTCUSDT", trade_signal.take_profit.tp1)
        open_pos = await paper.get_open_positions()
        assert len(open_pos) == 0  # Position closed
