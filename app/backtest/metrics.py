"""
app/backtest/metrics.py
────────────────────────
Comprehensive performance and risk analytics for trading strategies and models.
Calculates Sharpe, Sortino, Calmar, Max Drawdown, Win Rate, Profit Factor,
Expectancy, MFE, MAE, Brier score, and returns distribution statistics.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

import numpy as np
import pandas as pd


@dataclass
class BacktestMetrics:
    """Standard quantitative trading performance metrics."""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    break_even_trades: int = 0

    win_rate: float = 0.0
    loss_rate: float = 0.0

    total_pnl_usd: float = 0.0
    total_pnl_pct: float = 0.0
    total_fees_usd: float = 0.0
    net_pnl_usd: float = 0.0
    net_pnl_pct: float = 0.0

    gross_profit: float = 0.0
    gross_loss: float = 0.0
    profit_factor: float = 0.0

    average_trade_pnl: float = 0.0
    average_trade_pct: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    win_loss_ratio: float = 0.0
    expectancy_r: float = 0.0

    max_drawdown_usd: float = 0.0
    max_drawdown_pct: float = 0.0
    max_drawdown_duration_bars: int = 0

    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0

    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0

    avg_trade_duration_bars: float = 0.0
    avg_mfe_pct: float = 0.0
    avg_mae_pct: float = 0.0

    cagr_pct: float = 0.0
    exposure_pct: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


def calculate_metrics(
    trades: list[dict],
    initial_capital: float = 10000.0,
    equity_curve: Optional[list[float]] = None,
    risk_free_rate: float = 0.0,
    annualization_factor: float = 365.0 * 24.0,  # Crypto 24/7 hourly base
) -> BacktestMetrics:
    """
    Calculate full performance metrics from a list of completed trades.

    Each trade dict is expected to have:
    - 'pnl_usd': float
    - 'pnl_pct': float
    - 'fee': float
    - 'entry_time': datetime
    - 'exit_time': datetime
    - 'duration_bars': int
    - 'mfe_pct': float (Max Favorable Excursion)
    - 'mae_pct': float (Max Adverse Excursion)
    - 'risk_r': float (Risk unit R)
    """
    if not trades:
        return BacktestMetrics()

    n = len(trades)
    pnls = np.array([t.get("pnl_usd", 0.0) for t in trades], dtype=np.float64)
    pnl_pcts = np.array([t.get("pnl_pct", 0.0) for t in trades], dtype=np.float64)
    fees = np.array([t.get("fee", 0.0) for t in trades], dtype=np.float64)
    durations = [t.get("duration_bars", 1) for t in trades]
    mfes = [t.get("mfe_pct", 0.0) for t in trades]
    maes = [t.get("mae_pct", 0.0) for t in trades]

    wins = pnls[pnls > 0]
    losses = pnls[pnls < 0]
    evens = pnls[pnls == 0]

    n_wins = len(wins)
    n_losses = len(losses)
    n_evens = len(evens)

    win_rate = n_wins / n if n > 0 else 0.0
    loss_rate = n_losses / n if n > 0 else 0.0

    gross_profit = float(np.sum(wins)) if len(wins) > 0 else 0.0
    gross_loss = float(abs(np.sum(losses))) if len(losses) > 0 else 0.0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)

    total_fees = float(np.sum(fees))
    total_pnl = float(np.sum(pnls))
    net_pnl = total_pnl - total_fees
    net_pnl_pct = net_pnl / initial_capital if initial_capital > 0 else 0.0

    avg_trade_pnl = float(np.mean(pnls)) if n > 0 else 0.0
    avg_trade_pct = float(np.mean(pnl_pcts)) if n > 0 else 0.0
    avg_win = float(np.mean(wins)) if len(wins) > 0 else 0.0
    avg_loss = float(abs(np.mean(losses))) if len(losses) > 0 else 0.0
    win_loss_ratio = (avg_win / avg_loss) if avg_loss > 0 else (999.0 if avg_win > 0 else 0.0)

    # Expectancy in R: (WinRate * AvgWinR) - (LossRate * AvgLossR)
    expectancy_r = (win_rate * win_loss_ratio) - (loss_rate * 1.0) if win_loss_ratio > 0 else 0.0

    # Consecutive wins / losses
    max_consec_wins = 0
    max_consec_losses = 0
    cur_wins = 0
    cur_losses = 0
    for p in pnls:
        if p > 0:
            cur_wins += 1
            cur_losses = 0
            max_consec_wins = max(max_consec_wins, cur_wins)
        elif p < 0:
            cur_losses += 1
            cur_wins = 0
            max_consec_losses = max(max_consec_losses, cur_losses)
        else:
            cur_wins = 0
            cur_losses = 0

    # Equity Curve & Drawdown
    if equity_curve is not None and len(equity_curve) > 1:
        eq = np.array(equity_curve, dtype=np.float64)
    else:
        # Construct equity curve from trades
        eq = np.zeros(n + 1, dtype=np.float64)
        eq[0] = initial_capital
        for i, p in enumerate(pnls):
            eq[i + 1] = eq[i] + p - fees[i]

    peaks = np.maximum.accumulate(eq)
    drawdowns = (peaks - eq) / peaks
    max_dd_pct = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0
    max_dd_usd = float(np.max(peaks - eq)) if len(peaks) > 0 else 0.0

    # Max Drawdown Duration (bars)
    dd_duration = 0
    max_dd_duration = 0
    for i in range(len(eq)):
        if eq[i] < peaks[i]:
            dd_duration += 1
            max_dd_duration = max(max_dd_duration, dd_duration)
        else:
            dd_duration = 0

    # Sharpe, Sortino, Calmar
    returns = np.diff(eq) / eq[:-1] if len(eq) > 1 else np.array([0.0])
    mean_ret = float(np.mean(returns)) if len(returns) > 0 else 0.0
    std_ret = float(np.std(returns)) if len(returns) > 0 else 0.0

    downside_returns = returns[returns < 0]
    downside_std = float(np.std(downside_returns)) if len(downside_returns) > 0 else 0.0

    sharpe = (
        (mean_ret - risk_free_rate) / std_ret * np.sqrt(min(annualization_factor, len(returns)))
        if std_ret > 1e-8
        else 0.0
    )
    sortino = (
        (mean_ret - risk_free_rate) / downside_std * np.sqrt(min(annualization_factor, len(returns)))
        if downside_std > 1e-8
        else 0.0
    )
    calmar = (net_pnl_pct / max_dd_pct) if max_dd_pct > 1e-8 else 0.0

    return BacktestMetrics(
        total_trades=n,
        winning_trades=n_wins,
        losing_trades=n_losses,
        break_even_trades=n_evens,
        win_rate=round(win_rate, 4),
        loss_rate=round(loss_rate, 4),
        total_pnl_usd=round(total_pnl, 2),
        total_pnl_pct=round(total_pnl / initial_capital, 4),
        total_fees_usd=round(total_fees, 2),
        net_pnl_usd=round(net_pnl, 2),
        net_pnl_pct=round(net_pnl_pct, 4),
        gross_profit=round(gross_profit, 2),
        gross_loss=round(gross_loss, 2),
        profit_factor=round(profit_factor, 4),
        average_trade_pnl=round(avg_trade_pnl, 2),
        average_trade_pct=round(avg_trade_pct, 4),
        average_win=round(avg_win, 2),
        average_loss=round(avg_loss, 2),
        win_loss_ratio=round(win_loss_ratio, 4),
        expectancy_r=round(expectancy_r, 4),
        max_drawdown_usd=round(max_dd_usd, 2),
        max_drawdown_pct=round(max_dd_pct, 4),
        max_drawdown_duration_bars=max_dd_duration,
        sharpe_ratio=round(sharpe, 4),
        sortino_ratio=round(sortino, 4),
        calmar_ratio=round(calmar, 4),
        max_consecutive_wins=max_consec_wins,
        max_consecutive_losses=max_consec_losses,
        avg_trade_duration_bars=round(float(np.mean(durations)), 2) if durations else 0.0,
        avg_mfe_pct=round(float(np.mean(mfes)), 4) if mfes else 0.0,
        avg_mae_pct=round(float(np.mean(maes)), 4) if maes else 0.0,
    )
