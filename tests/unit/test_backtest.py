"""
tests/unit/test_backtest.py
────────────────────────────
Unit tests for the Backtest Engine and quantitative performance metrics.
"""

from __future__ import annotations

import pandas as pd
import pytest

from app.backtest.engine import BacktestEngine
from app.backtest.metrics import calculate_metrics
from app.core.constants import SignalDirection
from app.features.pipeline import FeaturePipeline


def test_metrics_calculation():
    # Synthetic trade list
    trades = [
        {"pnl_usd": 300.0, "pnl_pct": 0.03, "fee": 10.0, "duration_bars": 5, "mfe_pct": 0.04, "mae_pct": 0.01},
        {"pnl_usd": 200.0, "pnl_pct": 0.02, "fee": 10.0, "duration_bars": 8, "mfe_pct": 0.025, "mae_pct": 0.005},
        {"pnl_usd": -100.0, "pnl_pct": -0.01, "fee": 10.0, "duration_bars": 3, "mfe_pct": 0.005, "mae_pct": 0.012},
    ]
    metrics = calculate_metrics(trades, initial_capital=10000.0)

    assert metrics.total_trades == 3
    assert metrics.winning_trades == 2
    assert metrics.losing_trades == 1
    assert round(metrics.win_rate, 2) == 0.67
    assert metrics.profit_factor == 5.0  # 500 gross win / 100 gross loss
    assert metrics.net_pnl_usd == 370.0  # 400 gross pnl - 30 fees


def test_backtest_engine_run(synthetic_candles_df: pd.DataFrame):
    pipeline = FeaturePipeline()
    df_feat = pipeline.compute(synthetic_candles_df)

    # Simple moving average crossover mock signal
    def mock_signal(df: pd.DataFrame, idx: int):
        if idx < 60:
            return None
        sub = df.iloc[: idx + 1]
        c = float(sub["close"].iloc[-1])
        ema9 = float(sub["ema_9"].iloc[-1])
        ema20 = float(sub["ema_20"].iloc[-1])

        if ema9 > ema20 and idx % 20 == 0:
            return {
                "direction": SignalDirection.LONG,
                "sl": c * 0.98,
                "tp1": c * 1.03,
                "tp2": c * 1.05,
                "tp3": c * 1.08,
            }
        return None

    engine = BacktestEngine(initial_capital=10000.0, risk_per_trade=0.01)
    metrics, trades, equity_curve = engine.run(df_feat, mock_signal, symbol="BTCUSDT")

    assert len(equity_curve) > 0
    assert metrics.total_trades == len(trades)
    assert 0.0 <= metrics.win_rate <= 1.0
