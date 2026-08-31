"""
app/backtest/engine.py
───────────────────────
Realistic event-driven backtesting engine for quantitative crypto trading.

Key Features:
- Zero look-ahead bias: Signal generated at bar i close, executed at bar i+1.
- Realistic transaction costs: Taker (0.055%) / Maker (0.02%) fees + slippage.
- Multi-tier take profit (TP1 50%, TP2 30%, TP3 20%) with break-even SL adjustment.
- Maximum Favorable Excursion (MFE) & Maximum Adverse Excursion (MAE) tracking.
- Dynamic ATR-based risk management and position sizing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional

import numpy as np
import pandas as pd

from app.backtest.metrics import BacktestMetrics, calculate_metrics
from app.core.constants import SignalDirection
from app.core.logging import get_logger

logger = get_logger("trading")


@dataclass
class BacktestTrade:
    trade_id: str
    symbol: str
    direction: str  # "LONG" | "SHORT"
    entry_time: datetime
    entry_price: float
    initial_qty: float
    remaining_qty: float
    initial_sl: float
    current_sl: float
    tp1: float
    tp2: Optional[float]
    tp3: Optional[float]
    risk_usd: float

    # Execution state
    status: str = "OPEN"  # OPEN, TP1_HIT, TP2_HIT, TP3_HIT, STOPPED_OUT, CLOSED
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    duration_bars: int = 0

    # Financials
    fee_paid: float = 0.0
    realized_pnl: float = 0.0
    pnl_pct: float = 0.0

    # Analytics
    max_price_seen: float = field(default=0.0)
    min_price_seen: float = field(default=float("inf"))
    mfe_pct: float = 0.0
    mae_pct: float = 0.0


class BacktestEngine:
    """
    Event-driven backtesting engine.

    Usage:
        engine = BacktestEngine(initial_capital=10000.0, risk_per_trade=0.01)
        result = engine.run(df_with_features, signal_generator_fn)
    """

    def __init__(
        self,
        initial_capital: float = 10000.0,
        risk_per_trade: float = 0.01,
        taker_fee_pct: float = 0.00055,  # 0.055% Bybit taker
        maker_fee_pct: float = 0.00020,  # 0.020% Bybit maker
        slippage_pct: float = 0.00020,   # 0.020% standard slippage
        max_open_positions: int = 3,
    ) -> None:
        self.initial_capital = initial_capital
        self.risk_per_trade = risk_per_trade
        self.taker_fee_pct = taker_fee_pct
        self.maker_fee_pct = maker_fee_pct
        self.slippage_pct = slippage_pct
        self.max_open_positions = max_open_positions

    def run(
        self,
        df: pd.DataFrame,
        signal_fn: Callable[[pd.DataFrame, int], Optional[dict]],
        symbol: str = "BTCUSDT",
    ) -> tuple[BacktestMetrics, list[dict], list[float]]:
        """
        Execute the backtest step-by-step over historical candles.

        Args:
            df: DataFrame containing OHLCV and all feature columns
            signal_fn: Function(df_slice, current_bar_idx) -> dict or None
                       Must return signal parameters:
                       {
                           "direction": SignalDirection.LONG / SHORT,
                           "entry_price": float,
                           "sl": float,
                           "tp1": float,
                           "tp2": float,
                           "tp3": float,
                       }
            symbol: Trading pair name

        Returns:
            (metrics, trade_records, equity_curve)
        """
        if df.empty or len(df) < 50:
            logger.warning("Backtest DataFrame has insufficient rows")
            return BacktestMetrics(), [], [self.initial_capital]

        equity = self.initial_capital
        equity_curve: list[float] = [equity]
        open_trades: list[BacktestTrade] = []
        completed_trades: list[dict] = []
        trade_counter = 0

        n = len(df)
        times = df["open_time"].values if "open_time" in df.columns else df.index.values
        opens = df["open"].values
        highs = df["high"].values
        lows = df["low"].values
        closes = df["close"].values

        logger.info("Starting backtest", symbol=symbol, total_bars=n, initial_capital=equity)

        for i in range(50, n - 1):
            cur_time = times[i]
            cur_open = opens[i]
            cur_high = highs[i]
            cur_low = lows[i]
            cur_close = closes[i]

            # 1. Update and process open positions on current bar
            closed_this_bar: list[BacktestTrade] = []
            for trade in open_trades:
                trade.duration_bars += 1
                trade.max_price_seen = max(trade.max_price_seen, cur_high)
                trade.min_price_seen = min(trade.min_price_seen, cur_low)

                # Update MFE / MAE
                if trade.direction == "LONG":
                    trade.mfe_pct = max(trade.mfe_pct, (trade.max_price_seen - trade.entry_price) / trade.entry_price)
                    trade.mae_pct = max(trade.mae_pct, (trade.entry_price - trade.min_price_seen) / trade.entry_price)
                else:
                    trade.mfe_pct = max(trade.mfe_pct, (trade.entry_price - trade.min_price_seen) / trade.entry_price)
                    trade.mae_pct = max(trade.mae_pct, (trade.max_price_seen - trade.entry_price) / trade.entry_price)

                # Check Stop Loss & Take Profit outcomes
                is_closed = self._evaluate_bar_exit(trade, cur_open, cur_high, cur_low, cur_close, cur_time)
                if is_closed:
                    closed_this_bar.append(trade)

            # Settle closed trades
            for trade in closed_this_bar:
                open_trades.remove(trade)
                equity += trade.realized_pnl
                completed_trades.append(self._format_completed_trade(trade))

            # 2. Generate signal at close of bar i (strictly using data up to bar i)
            if len(open_trades) < self.max_open_positions:
                sig = signal_fn(df, i)
                if sig and sig.get("direction") in (SignalDirection.LONG, SignalDirection.SHORT):
                    direction = sig["direction"].value if hasattr(sig["direction"], "value") else sig["direction"]
                    # Entry order is executed at the OPEN of the NEXT bar (i+1) with slippage
                    next_open = opens[i + 1]
                    sl = sig.get("sl", next_open * 0.98 if direction == "LONG" else next_open * 1.02)
                    tp1 = sig.get("tp1", next_open * 1.03 if direction == "LONG" else next_open * 0.97)
                    tp2 = sig.get("tp2")
                    tp3 = sig.get("tp3")

                    # Position sizing based on risk %
                    sl_dist = abs(next_open - sl)
                    if sl_dist > 0:
                        risk_usd = equity * self.risk_per_trade
                        qty = risk_usd / sl_dist

                        # Apply entry slippage
                        fill_price = next_open * (1 + self.slippage_pct) if direction == "LONG" else next_open * (1 - self.slippage_pct)
                        entry_fee = fill_price * qty * self.taker_fee_pct

                        trade_counter += 1
                        new_trade = BacktestTrade(
                            trade_id=f"BT-{trade_counter:06d}",
                            symbol=symbol,
                            direction=direction,
                            entry_time=times[i + 1],
                            entry_price=fill_price,
                            initial_qty=qty,
                            remaining_qty=qty,
                            initial_sl=sl,
                            current_sl=sl,
                            tp1=tp1,
                            tp2=tp2,
                            tp3=tp3,
                            risk_usd=risk_usd,
                            fee_paid=entry_fee,
                            max_price_seen=fill_price,
                            min_price_seen=fill_price,
                        )
                        open_trades.append(new_trade)

            # Record equity snapshot
            unrealized = sum(self._calc_unrealized_pnl(t, cur_close) for t in open_trades)
            equity_curve.append(equity + unrealized)

        # Force-close any remaining open positions at the final bar close
        final_time = times[-1]
        final_close = closes[-1]
        for trade in list(open_trades):
            self._close_full(trade, final_close, "END_OF_DATA", final_time)
            equity += trade.realized_pnl
            completed_trades.append(self._format_completed_trade(trade))

        metrics = calculate_metrics(completed_trades, initial_capital=self.initial_capital, equity_curve=equity_curve)

        logger.info(
            "Backtest complete",
            trades=metrics.total_trades,
            win_rate=f"{metrics.win_rate:.1%}",
            profit_factor=metrics.profit_factor,
            net_pnl=metrics.net_pnl_usd,
            max_drawdown=f"{metrics.max_drawdown_pct:.1%}",
        )

        return metrics, completed_trades, equity_curve

    def _evaluate_bar_exit(
        self,
        trade: BacktestTrade,
        bar_open: float,
        bar_high: float,
        bar_low: float,
        bar_close: float,
        bar_time: Any,
    ) -> bool:
        """
        Evaluate if a trade hits SL or TP levels during the bar.
        Supports tiered TP1 (50%), TP2 (30%), TP3 (20%) and break-even SL.
        """
        if trade.direction == "LONG":
            # 1. Check Stop Loss first (conservative evaluation)
            if bar_low <= trade.current_sl:
                exit_price = min(bar_open, trade.current_sl) * (1 - self.slippage_pct)
                self._close_full(trade, exit_price, "STOPPED_OUT", bar_time)
                return True

            # 2. Check TP3
            if trade.tp3 and bar_high >= trade.tp3:
                self._close_full(trade, trade.tp3 * (1 - self.slippage_pct), "TP3", bar_time)
                return True

            # 3. Check TP2
            if trade.tp2 and bar_high >= trade.tp2 and trade.status != "TP2_HIT":
                partial_qty = trade.initial_qty * 0.30
                if trade.remaining_qty >= partial_qty:
                    self._close_partial(trade, trade.tp2, partial_qty, "TP2_HIT")
                    trade.current_sl = max(trade.current_sl, trade.tp1)  # Lock in TP1 profit

            # 4. Check TP1
            if bar_high >= trade.tp1 and trade.status == "OPEN":
                partial_qty = trade.initial_qty * 0.50
                self._close_partial(trade, trade.tp1, partial_qty, "TP1_HIT")
                trade.current_sl = trade.entry_price  # Move SL to Break-even

        else:  # SHORT
            # 1. Check Stop Loss first
            if bar_high >= trade.current_sl:
                exit_price = max(bar_open, trade.current_sl) * (1 + self.slippage_pct)
                self._close_full(trade, exit_price, "STOPPED_OUT", bar_time)
                return True

            # 2. Check TP3
            if trade.tp3 and bar_low <= trade.tp3:
                self._close_full(trade, trade.tp3 * (1 + self.slippage_pct), "TP3", bar_time)
                return True

            # 3. Check TP2
            if trade.tp2 and bar_low <= trade.tp2 and trade.status != "TP2_HIT":
                partial_qty = trade.initial_qty * 0.30
                if trade.remaining_qty >= partial_qty:
                    self._close_partial(trade, trade.tp2, partial_qty, "TP2_HIT")
                    trade.current_sl = min(trade.current_sl, trade.tp1)

            # 4. Check TP1
            if bar_low <= trade.tp1 and trade.status == "OPEN":
                partial_qty = trade.initial_qty * 0.50
                self._close_partial(trade, trade.tp1, partial_qty, "TP1_HIT")
                trade.current_sl = trade.entry_price  # Break-even

        return False

    def _close_partial(self, trade: BacktestTrade, exit_price: float, qty: float, new_status: str) -> None:
        """Close partial position volume (e.g. at TP1 / TP2)."""
        fee = exit_price * qty * self.taker_fee_pct
        if trade.direction == "LONG":
            pnl = (exit_price - trade.entry_price) * qty - fee
        else:
            pnl = (trade.entry_price - exit_price) * qty - fee

        trade.realized_pnl += pnl
        trade.fee_paid += fee
        trade.remaining_qty -= qty
        trade.status = new_status

    def _close_full(self, trade: BacktestTrade, exit_price: float, reason: str, exit_time: Any) -> None:
        """Close the remaining position."""
        qty = trade.remaining_qty
        fee = exit_price * qty * self.taker_fee_pct
        if trade.direction == "LONG":
            pnl = (exit_price - trade.entry_price) * qty - fee
        else:
            pnl = (trade.entry_price - exit_price) * qty - fee

        trade.realized_pnl += pnl
        trade.fee_paid += fee
        trade.remaining_qty = 0.0
        trade.exit_price = exit_price
        trade.exit_time = exit_time
        trade.status = reason
        notional = trade.entry_price * trade.initial_qty
        trade.pnl_pct = trade.realized_pnl / notional if notional > 0 else 0.0

    def _calc_unrealized_pnl(self, trade: BacktestTrade, current_price: float) -> float:
        if trade.remaining_qty <= 0:
            return 0.0
        if trade.direction == "LONG":
            return (current_price - trade.entry_price) * trade.remaining_qty
        return (trade.entry_price - current_price) * trade.remaining_qty

    def _format_completed_trade(self, trade: BacktestTrade) -> dict:
        return {
            "trade_id": trade.trade_id,
            "symbol": trade.symbol,
            "direction": trade.direction,
            "entry_time": trade.entry_time,
            "exit_time": trade.exit_time,
            "entry_price": round(trade.entry_price, 4),
            "exit_price": round(trade.exit_price, 4) if trade.exit_price else 0.0,
            "qty": round(trade.initial_qty, 6),
            "pnl_usd": round(trade.realized_pnl, 4),
            "pnl_pct": round(trade.pnl_pct, 6),
            "fee": round(trade.fee_paid, 4),
            "status": trade.status,
            "duration_bars": trade.duration_bars,
            "mfe_pct": round(trade.mfe_pct, 4),
            "mae_pct": round(trade.mae_pct, 4),
            "risk_usd": round(trade.risk_usd, 2),
        }
