"""
app/backtest/walk_forward.py
─────────────────────────────
Walk-forward optimization and chronological out-of-sample validation.

Strictly preserves temporal causality:
- No lookahead bias or random train/test shuffling.
- Supports expanding window and rolling window splits.
- Calculates combined out-of-sample performance across all time folds.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

import numpy as np
import pandas as pd

from app.backtest.engine import BacktestEngine
from app.backtest.metrics import BacktestMetrics, calculate_metrics
from app.core.logging import get_logger

logger = get_logger("model")


@dataclass
class WalkForwardFold:
    fold_idx: int
    train_start: Any
    train_end: Any
    test_start: Any
    test_end: Any
    train_metrics: BacktestMetrics
    test_metrics: BacktestMetrics
    test_trades: list[dict]


@dataclass
class WalkForwardResult:
    total_folds: int
    combined_oos_metrics: BacktestMetrics
    folds: list[WalkForwardFold]
    is_robust: bool
    consistency_score: float  # Percentage of folds that were profitable


class WalkForwardValidator:
    """
    Chronological Walk-Forward Validator.

    Splits historical data into train and out-of-sample (OOS) validation folds.
    """

    def __init__(
        self,
        train_bars: int = 2000,
        test_bars: int = 500,
        step_bars: int = 500,
        expanding_window: bool = True,
        initial_capital: float = 10000.0,
    ) -> None:
        self.train_bars = train_bars
        self.test_bars = test_bars
        self.step_bars = step_bars
        self.expanding_window = expanding_window
        self.initial_capital = initial_capital
        self.engine = BacktestEngine(initial_capital=initial_capital)

    def validate(
        self,
        df: pd.DataFrame,
        train_and_predict_fn: Callable[[pd.DataFrame, pd.DataFrame], Callable[[pd.DataFrame, int], Optional[dict]]],
        symbol: str = "BTCUSDT",
    ) -> WalkForwardResult:
        """
        Execute chronological walk-forward validation across all folds.

        Args:
            df: Full historical DataFrame with features
            train_and_predict_fn: Callable that accepts (df_train, df_test)
                                  trains models on df_train, and returns
                                  a signal_fn(df_slice, idx) for the backtest engine.
            symbol: Asset symbol

        Returns:
            WalkForwardResult with combined out-of-sample metrics and fold summaries.
        """
        n = len(df)
        min_required = self.train_bars + self.test_bars
        if n < min_required:
            raise ValueError(f"Insufficient data for walk-forward validation: {n} bars available, {min_required} required.")

        folds: list[WalkForwardFold] = []
        all_oos_trades: list[dict] = []
        profitable_folds = 0
        start_idx = 0
        fold_idx = 1

        logger.info("Starting Walk-Forward Validation", total_bars=n, train_bars=self.train_bars, test_bars=self.test_bars)

        while (start_idx + self.train_bars + self.test_bars) <= n:
            train_start = 0 if self.expanding_window else start_idx
            train_end = start_idx + self.train_bars
            test_start = train_end
            test_end = min(test_start + self.test_bars, n)

            df_train = df.iloc[train_start:train_end].copy()
            df_test = df.iloc[test_start:test_end].copy()

            t_start_val = df_train["open_time"].iloc[0] if "open_time" in df_train.columns else df_train.index[0]
            t_end_val = df_train["open_time"].iloc[-1] if "open_time" in df_train.columns else df_train.index[-1]
            test_s_val = df_test["open_time"].iloc[0] if "open_time" in df_test.columns else df_test.index[0]
            test_e_val = df_test["open_time"].iloc[-1] if "open_time" in df_test.columns else df_test.index[-1]

            logger.info(
                f"Processing Walk-Forward Fold {fold_idx}",
                train_period=f"{t_start_val} -> {t_end_val}",
                test_period=f"{test_s_val} -> {test_e_val}",
            )

            # 1. Train model on in-sample data and obtain inference signal generator
            signal_fn = train_and_predict_fn(df_train, df_test)

            # 2. Run backtest strictly on out-of-sample data
            test_metrics, test_trades, _ = self.engine.run(df_test, signal_fn, symbol=symbol)
            train_metrics, _, _ = self.engine.run(df_train, signal_fn, symbol=symbol)

            if test_metrics.net_pnl_usd > 0:
                profitable_folds += 1

            all_oos_trades.extend(test_trades)

            fold = WalkForwardFold(
                fold_idx=fold_idx,
                train_start=t_start_val,
                train_end=t_end_val,
                test_start=test_s_val,
                test_end=test_e_val,
                train_metrics=train_metrics,
                test_metrics=test_metrics,
                test_trades=test_trades,
            )
            folds.append(fold)

            start_idx += self.step_bars
            fold_idx += 1

        # Combined out-of-sample metrics
        combined_oos = calculate_metrics(all_oos_trades, initial_capital=self.initial_capital)
        total_folds = len(folds)
        consistency = (profitable_folds / total_folds) if total_folds > 0 else 0.0

        # System is considered robust if > 60% of OOS folds are profitable and overall Profit Factor > 1.25
        is_robust = consistency >= 0.60 and combined_oos.profit_factor >= 1.25 and combined_oos.max_drawdown_pct <= 0.20

        logger.info(
            "Walk-Forward Validation Complete",
            total_folds=total_folds,
            profitable_folds=profitable_folds,
            consistency=f"{consistency:.1%}",
            combined_pf=combined_oos.profit_factor,
            combined_win_rate=f"{combined_oos.win_rate:.1%}",
            is_robust=is_robust,
        )

        return WalkForwardResult(
            total_folds=total_folds,
            combined_oos_metrics=combined_oos,
            folds=folds,
            is_robust=is_robust,
            consistency_score=round(consistency, 4),
        )
