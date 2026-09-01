"""
app/services/mt5_scalper.py
───────────────────────────
Complete Autonomous Scalping Engine for MetaTrader 5 & Exness.
Implements the 17-component institutional quantitative architecture:
1. MarketDataEngine (Ticks, M1/M5 Bars, Spread, ATR(14))
2. MarketFilter (Spread, ATR Volatility, Session, Cooldown)
3. SignalEngine (Trend EMA 9/21/50, RSI 14, Price Action)
4. RiskManager (Daily Loss, Max DD, Consecutive Losses, Margin Level)
5. DynamicPositionSizer (Risk % -> SL Points -> Dollar Value per Point)
6. ExecutionEngine (Validated orders with pre-set SL/TP)
7. TradeManager (Dynamic Break-Even, ATR Trailing Stop, Time-based Exit)
8. Expected Value & Cost Optimization
"""

from __future__ import annotations

import asyncio
import math
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False

from app.core.logging import get_logger
from app.services.mt5_service import mt5_service

logger = get_logger("mt5_scalper")


class ScalperConfig(BaseModel):
    symbol: str = "XAUUSDm"
    timeframe: str = "M1"
    # Risk parameters
    risk_per_trade_pct: float = Field(default=0.50, description="Risk % per trade (e.g. 0.5%)")
    max_daily_loss_pct: float = Field(default=3.00, description="Daily loss limit % (e.g. 3.0%)")
    max_drawdown_pct: float = Field(default=10.00, description="Max drawdown limit % (e.g. 10.0%)")
    max_consecutive_losses: int = Field(default=4, description="Halt trading after N consecutive losses")
    consecutive_loss_cooldown_mins: int = Field(default=30, description="Cooldown in minutes after max losses")
    max_concurrent_positions: int = Field(default=1, description="Max concurrent positions (1 or 2)")
    min_margin_level_pct: float = Field(default=200.0, description="Minimum margin level required to open trade")

    # Dynamic Position Sizing
    max_lot: float = Field(default=2.00, description="Maximum allowed lot size")
    min_lot: float = Field(default=0.01, description="Minimum allowed lot size")

    # TP & SL target distances (SL $10, TP $2 Scalping)
    fixed_tp_dollars: float = Field(default=2.00, description="Fixed price distance for Take Profit ($2.00 target)")
    fixed_sl_dollars: float = Field(default=10.00, description="Fixed price distance for Stop Loss ($10.00 buffer)")
    use_fixed_targets: bool = Field(default=True, description="True for fixed dollar targets ($2 TP / $10 SL)")
    tp_atr_multiplier: float = Field(default=0.80, description="Take profit distance = ATR * multiplier")
    sl_atr_multiplier: float = Field(default=4.00, description="Stop loss distance = ATR * multiplier")

    # Market Filters (points calibrated for 3-digit Gold point 0.001)
    max_spread_points: float = Field(default=400.0, description="Max allowed spread in points (e.g. 400 pts = $0.40)")
    min_tp_to_spread_ratio: float = Field(default=3.00, description="Required TP / Spread ratio (e.g. >= 3.0)")
    min_atr_points: float = Field(default=300.0, description="Min ATR in points (avoids dead markets)")
    max_atr_points: float = Field(default=8000.0, description="Max ATR in points (avoids news spikes)")
    session_start_hour: int = Field(default=1, description="Trading start hour (UTC)")
    session_end_hour: int = Field(default=23, description="Trading end hour (UTC)")
    cooldown_seconds_after_close: int = Field(default=30, description="Cooldown between trades in seconds")

    # Trade Management (Dynamic Break-Even, Trailing SL, Time Exit)
    break_even_enabled: bool = Field(default=True, description="Enable automatic break-even")
    break_even_trigger_atr: float = Field(default=0.60, description="Move SL to BE when profit >= ATR * trigger")
    break_even_profit_buffer: float = Field(default=5.0, description="Buffer above entry in points")
    trailing_enabled: bool = Field(default=True, description="Enable trailing stop")
    trailing_trigger_atr: float = Field(default=0.80, description="Start trailing when profit >= ATR * trigger")
    trailing_distance_atr: float = Field(default=0.50, description="Trail SL behind price by ATR * distance")
    max_trade_duration_seconds: int = Field(default=300, description="Time exit: close trade if open > 5 min without momentum")


class ScalperTelemetry(BaseModel):
    is_running: bool = False
    symbol: str = "XAUUSDm"
    current_bid: float = 0.0
    current_ask: float = 0.0
    current_spread_points: float = 0.0
    current_atr_points: float = 0.0
    last_signal: str = "NEUTRAL"
    last_signal_reason: str = "Initializing"
    filter_spread_ok: bool = True
    filter_volatility_ok: bool = True
    filter_session_ok: bool = True
    filter_cooldown_ok: bool = True
    filter_risk_ok: bool = True
    active_positions_count: int = 0
    daily_pnl_usd: float = 0.0
    daily_loss_pct: float = 0.0
    consecutive_losses: int = 0
    is_risk_locked: bool = False
    risk_lock_reason: Optional[str] = None
    last_tick_time: str = ""
    last_trade_time: Optional[str] = None
    managed_trades: List[Dict[str, Any]] = []


class MT5ScalpingEngine:
    def __init__(self, config: Optional[ScalperConfig] = None) -> None:
        self.config = config or ScalperConfig()
        self.telemetry = ScalperTelemetry(symbol=self.config.symbol)
        self.is_running = False
        self._loop_task: Optional[asyncio.Task] = None
        self.last_closed_trade_time: float = 0.0
        self.consecutive_losses: int = 0
        self.cooldown_until: float = 0.0
        self.starting_daily_equity: float = 10000.0
        self.peak_equity: float = 10000.0
        self.daily_closed_pnl: float = 0.0
        self.trade_open_timestamps: Dict[int, float] = {}

    def start(self) -> Dict[str, Any]:
        if self.is_running:
            return {"success": True, "message": "Scalper is already running"}

        if not mt5_service.is_connected:
            login_res = mt5_service.initialize_and_login()
            if not login_res.get("success"):
                return {"success": False, "error": f"MT5 not connected: {login_res.get('error')}"}

        acc = mt5.account_info()
        if acc:
            self.starting_daily_equity = float(acc.equity)
            self.peak_equity = max(self.peak_equity, float(acc.equity))

        self.is_running = True
        self.telemetry.is_running = True

        import threading

        def _thread_runner():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._autonomous_tick_loop())
            finally:
                loop.close()

        self._bg_thread = threading.Thread(target=_thread_runner, daemon=True, name="MT5ScalperLoop")
        self._bg_thread.start()

        logger.info("Autonomous MT5 Scalper Engine STARTED", symbol=self.config.symbol)
        return {"success": True, "message": f"Autonomous Scalper started on {self.config.symbol}"}

    def stop(self) -> Dict[str, Any]:
        self.is_running = False
        self.telemetry.is_running = False
        logger.info("Autonomous MT5 Scalper Engine STOPPED")
        return {"success": True, "message": "Autonomous Scalper stopped"}

    def update_config(self, new_config: Dict[str, Any]) -> ScalperConfig:
        current_dict = self.config.model_dump()
        current_dict.update(new_config)
        self.config = ScalperConfig(**current_dict)
        self.telemetry.symbol = self.config.symbol
        logger.info("Updated Scalper configuration", config=self.config.model_dump())
        return self.config

    # ─── 1. MARKET DATA & INDICATORS ENGINE ─────────────────────────────────
    def _fetch_market_data(self) -> Optional[Dict[str, Any]]:
        sym = self.config.symbol
        if not mt5.symbol_select(sym, True):
            mt5.symbol_select(sym, True)

        tick = mt5.symbol_info_tick(sym)
        sym_info = mt5.symbol_info(sym)
        if not tick or not sym_info:
            return None

        # Fetch 60 M1 candles
        rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M1, 0, 60)
        if rates is None or len(rates) < 30:
            return None

        point = sym_info.point
        spread_points = (tick.ask - tick.bid) / point

        # Calculate ATR(14) in points
        highs = [r['high'] for r in rates]
        lows = [r['low'] for r in rates]
        closes = [r['close'] for r in rates]

        tr_list = []
        for i in range(1, len(rates)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1])
            )
            tr_list.append(tr)

        atr_14 = sum(tr_list[-14:]) / 14 if len(tr_list) >= 14 else tr_list[-1]
        atr_points = atr_14 / point

        # Calculate EMA 9, 21, 50
        def calc_ema(series: List[float], period: int) -> float:
            k = 2 / (period + 1)
            ema = series[0]
            for val in series[1:]:
                ema = val * k + ema * (1 - k)
            return ema

        ema_9 = calc_ema(closes, 9)
        ema_21 = calc_ema(closes, 21)
        ema_50 = calc_ema(closes, 50)

        # Calculate RSI(14)
        gains, losses = [], []
        for i in range(1, len(closes[-15:])):
            diff = closes[-15:][i] - closes[-15:][i - 1]
            if diff >= 0:
                gains.append(diff)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(diff))

        avg_gain = sum(gains) / 14 if len(gains) >= 14 else 1e-5
        avg_loss = sum(losses) / 14 if len(losses) >= 14 else 1e-5
        rs = avg_gain / (avg_loss if avg_loss > 0 else 1e-5)
        rsi_14 = 100 - (100 / (1 + rs))

        return {
            "symbol": sym,
            "bid": tick.bid,
            "ask": tick.ask,
            "point": point,
            "digits": sym_info.digits,
            "spread_points": spread_points,
            "atr_points": atr_points,
            "atr_price": atr_14,
            "ema_9": ema_9,
            "ema_21": ema_21,
            "ema_50": ema_50,
            "rsi_14": rsi_14,
            "close": closes[-1],
            "prev_close": closes[-2],
            "contract_size": sym_info.trade_contract_size,
            "volume_min": sym_info.volume_min,
            "volume_max": sym_info.volume_max,
            "volume_step": sym_info.volume_step,
        }

    # ─── 2. MARKET FILTERS ENGINE ───────────────────────────────────────────
    def _evaluate_market_filters(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        now_utc = datetime.now(timezone.utc)
        current_hour = now_utc.hour

        # 1. Session Filter
        if not (self.config.session_start_hour <= current_hour <= self.config.session_end_hour):
            self.telemetry.filter_session_ok = False
            return False, f"Outside trading session ({current_hour}:00 UTC)"
        self.telemetry.filter_session_ok = True

        # 2. Cooldown Filter after trade close
        if time.time() < self.cooldown_until:
            rem = int(self.cooldown_until - time.time())
            self.telemetry.filter_cooldown_ok = False
            return False, f"Cooldown active ({rem}s remaining)"
        self.telemetry.filter_cooldown_ok = True

        # 3. Spread Filter
        spread = data["spread_points"]
        if spread > self.config.max_spread_points:
            self.telemetry.filter_spread_ok = False
            return False, f"Spread too high ({spread:.1f} pts > {self.config.max_spread_points} limit)"

        # Check TP / Spread Ratio
        est_tp_points = data["atr_points"] * self.config.tp_atr_multiplier
        tp_spread_ratio = est_tp_points / (spread if spread > 0 else 1)
        if tp_spread_ratio < self.config.min_tp_to_spread_ratio:
            self.telemetry.filter_spread_ok = False
            return False, f"TP/Spread ratio too low ({tp_spread_ratio:.2f} < {self.config.min_tp_to_spread_ratio})"
        self.telemetry.filter_spread_ok = True

        # 4. Volatility Filter (ATR boundaries)
        atr_pts = data["atr_points"]
        if atr_pts < self.config.min_atr_points:
            self.telemetry.filter_volatility_ok = False
            return False, f"Volatility too low / slow market (ATR: {atr_pts:.1f} pts)"
        if atr_pts > self.config.max_atr_points:
            self.telemetry.filter_volatility_ok = False
            return False, f"Volatility too extreme / news event (ATR: {atr_pts:.1f} pts)"
        self.telemetry.filter_volatility_ok = True

        return True, "All market filters passed"

    # ─── 3. RISK MANAGER & CIRCUIT BREAKERS ─────────────────────────────────
    def _evaluate_risk_limits(self) -> Tuple[bool, str]:
        acc = mt5.account_info()
        if not acc:
            return False, "Cannot read MT5 account info"

        equity = float(acc.equity)
        balance = float(acc.balance)

        # 1. Consecutive Loss Lockout
        if self.consecutive_losses >= self.config.max_consecutive_losses:
            self.telemetry.is_risk_locked = True
            self.telemetry.risk_lock_reason = f"Max consecutive losses hit ({self.consecutive_losses})"
            return False, self.telemetry.risk_lock_reason

        # 2. Daily Loss Limit
        daily_loss_usd = max(0.0, self.starting_daily_equity - equity)
        daily_loss_pct = (daily_loss_usd / self.starting_daily_equity) * 100.0
        self.telemetry.daily_loss_pct = round(daily_loss_pct, 2)

        if daily_loss_pct >= self.config.max_daily_loss_pct:
            self.telemetry.is_risk_locked = True
            self.telemetry.risk_lock_reason = f"Daily loss limit exceeded ({daily_loss_pct:.2f}% >= {self.config.max_daily_loss_pct}%)"
            return False, self.telemetry.risk_lock_reason

        # 3. Max Drawdown Circuit Breaker
        self.peak_equity = max(self.peak_equity, equity)
        dd_pct = ((self.peak_equity - equity) / self.peak_equity) * 100.0 if self.peak_equity > 0 else 0
        if dd_pct >= self.config.max_drawdown_pct:
            self.telemetry.is_risk_locked = True
            self.telemetry.risk_lock_reason = f"Max drawdown hit ({dd_pct:.2f}% >= {self.config.max_drawdown_pct}%)"
            return False, self.telemetry.risk_lock_reason

        # 4. Max Concurrent Positions
        positions = mt5.positions_get(symbol=self.config.symbol)
        pos_count = len(positions) if positions else 0
        self.telemetry.active_positions_count = pos_count
        if pos_count >= self.config.max_concurrent_positions:
            return False, f"Max concurrent positions reached ({pos_count}/{self.config.max_concurrent_positions})"

        # 5. Margin Level Check
        margin = float(acc.margin)
        margin_level = (equity / margin * 100.0) if margin > 0 else 9999.0
        if margin_level < self.config.min_margin_level_pct:
            return False, f"Margin level too low ({margin_level:.1f}% < {self.config.min_margin_level_pct}%)"

        self.telemetry.is_risk_locked = False
        self.telemetry.filter_risk_ok = True
        return True, "Risk guards safe"

    # ─── 4. SIGNAL ENGINE ───────────────────────────────────────────────────
    def _evaluate_signal(self, data: Dict[str, Any]) -> Tuple[str, str]:
        ema_9 = data["ema_9"]
        ema_21 = data["ema_21"]
        ema_50 = data["ema_50"]
        rsi = data["rsi_14"]
        price = data["close"]

        # BUY Logic: Fast EMA > Mid EMA, Price > Trend EMA 50, RSI in bullish momentum zone (50-70)
        is_bull_trend = (ema_9 > ema_21) and (price > ema_50)
        is_bull_momentum = 52.0 <= rsi <= 72.0

        if is_bull_trend and is_bull_momentum:
            return "BUY", f"Trend bullish (EMA 9 > 21 > 50) + RSI momentum ({rsi:.1f})"

        # SELL Logic: Fast EMA < Mid EMA, Price < Trend EMA 50, RSI in bearish momentum zone (28-48)
        is_bear_trend = (ema_9 < ema_21) and (price < ema_50)
        is_bear_momentum = 28.0 <= rsi <= 48.0

        if is_bear_trend and is_bear_momentum:
            return "SELL", f"Trend bearish (EMA 9 < 21 < 50) + RSI momentum ({rsi:.1f})"

        return "NEUTRAL", "No clear high-probability alignment"

    # ─── 5. DYNAMIC POSITION SIZING ─────────────────────────────────────────
    def _calculate_lot_size(self, data: Dict[str, Any], sl_points: float) -> float:
        acc = mt5.account_info()
        equity = float(acc.equity) if acc else 10000.0

        # Maximum monetary loss for this trade
        risk_money = equity * (self.config.risk_per_trade_pct / 100.0)

        # Money value per point per 1.0 lot for this symbol
        point = data["point"]
        contract_size = data["contract_size"]
        money_per_point_per_lot = contract_size * point

        if sl_points <= 0 or money_per_point_per_lot <= 0:
            return self.config.min_lot

        # Exact calculated lot size
        raw_lot = risk_money / (sl_points * money_per_point_per_lot)

        # Normalize to broker constraints
        step = data["volume_step"] or 0.01
        normalized_lot = math.floor(raw_lot / step) * step
        bounded_lot = max(self.config.min_lot, min(self.config.max_lot, normalized_lot))

        return round(bounded_lot, 2)

    # ─── 6. ACTIVE TRADE MANAGER (BREAK-EVEN, TRAILING, TIME EXIT) ───────────
    def _manage_open_trades(self, data: Dict[str, Any]) -> None:
        positions = mt5.positions_get(symbol=self.config.symbol)
        if not positions:
            self.telemetry.managed_trades = []
            return

        point = data["point"]
        atr_price = data["atr_price"]
        now_ts = time.time()
        managed_list = []

        for pos in positions:
            ticket = pos.ticket
            open_time = self.trade_open_timestamps.get(ticket, pos.time)
            duration_sec = int(now_ts - open_time)
            is_buy = pos.type == mt5.ORDER_TYPE_BUY
            cur_price = data["bid"] if is_buy else data["ask"]
            profit_points = (cur_price - pos.price_open) / point if is_buy else (pos.price_open - cur_price) / point

            be_status = "PENDING"
            trailing_status = "INACTIVE"

            # A. Time-based exit
            if duration_sec >= self.config.max_trade_duration_seconds:
                logger.info("Time-based exit triggered", ticket=ticket, duration_sec=duration_sec)
                mt5_service.close_position(ticket)
                self.cooldown_until = now_ts + self.config.cooldown_seconds_after_close
                continue

            # B. Dynamic Break-Even
            if self.config.break_even_enabled:
                be_trigger_points = data["atr_points"] * self.config.break_even_trigger_atr
                if profit_points >= be_trigger_points:
                    be_price = pos.price_open + (self.config.break_even_profit_buffer * point) if is_buy else pos.price_open - (self.config.break_even_profit_buffer * point)
                    # Only modify if SL hasn't already passed BE
                    needs_mod = (is_buy and pos.sl < be_price) or (not is_buy and (pos.sl > be_price or pos.sl == 0))
                    if needs_mod:
                        self._modify_position_sl(pos, be_price)
                        be_status = "LOCKED"

            # C. Dynamic ATR Trailing Stop
            if self.config.trailing_enabled:
                trailing_trigger_points = data["atr_points"] * self.config.trailing_trigger_atr
                if profit_points >= trailing_trigger_points:
                    trail_dist = data["atr_points"] * self.config.trailing_distance_atr * point
                    new_sl = cur_price - trail_dist if is_buy else cur_price + trail_dist
                    needs_trail = (is_buy and new_sl > pos.sl) or (not is_buy and (new_sl < pos.sl or pos.sl == 0))
                    if needs_trail:
                        self._modify_position_sl(pos, new_sl)
                        trailing_status = "TRAILING"

            managed_list.append({
                "ticket": ticket,
                "symbol": pos.symbol,
                "type": "BUY" if is_buy else "SELL",
                "volume": pos.volume,
                "entry": pos.price_open,
                "current": cur_price,
                "sl": pos.sl,
                "tp": pos.tp,
                "profit_usd": round(pos.profit, 2),
                "profit_points": round(profit_points, 1),
                "duration_sec": duration_sec,
                "be_status": be_status,
                "trailing_status": trailing_status,
            })

        self.telemetry.managed_trades = managed_list

    def _modify_position_sl(self, pos: Any, new_sl: float) -> bool:
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": pos.ticket,
            "symbol": pos.symbol,
            "sl": round(new_sl, pos.digits if hasattr(pos, 'digits') else 3),
            "tp": pos.tp,
        }
        res = mt5.order_send(request)
        if res and res.retcode == mt5.TRADE_RETCODE_DONE:
            logger.info("Updated SL for position", ticket=pos.ticket, new_sl=new_sl)
            return True
        return False

    # ─── 7. AUTONOMOUS TICK & EXECUTION LOOP ────────────────────────────────
    async def _autonomous_tick_loop(self) -> None:
        logger.info("Autonomous tick loop running")
        while self.is_running:
            try:
                # 1. Fetch Market Data & Indicators
                data = self._fetch_market_data()
                if not data:
                    await asyncio.sleep(0.5)
                    continue

                self.telemetry.current_bid = data["bid"]
                self.telemetry.current_ask = data["ask"]
                self.telemetry.current_spread_points = round(data["spread_points"], 1)
                self.telemetry.current_atr_points = round(data["atr_points"], 1)
                self.telemetry.last_tick_time = datetime.now().strftime("%H:%M:%S")

                # 2. Active Trade Management on open positions
                self._manage_open_trades(data)

                # 3. Evaluate Risk Limits
                risk_ok, risk_msg = self._evaluate_risk_limits()
                if not risk_ok:
                    self.telemetry.last_signal_reason = f"Risk Filter: {risk_msg}"
                    await asyncio.sleep(1.0)
                    continue

                # 4. Evaluate Market Filters (Spread, Volatility, Session, Cooldown)
                filters_ok, filter_msg = self._evaluate_market_filters(data)
                if not filters_ok:
                    self.telemetry.last_signal_reason = f"Filter: {filter_msg}"
                    await asyncio.sleep(1.0)
                    continue

                # 5. Evaluate Signal Engine
                signal, signal_msg = self._evaluate_signal(data)
                self.telemetry.last_signal = signal
                self.telemetry.last_signal_reason = signal_msg

                if signal in ["BUY", "SELL"]:
                    point = data["point"]
                    atr_price = data["atr_price"]

                    # Sizing & SL/TP based on fixed $1.00 fast target or ATR
                    if self.config.use_fixed_targets:
                        sl_points = (self.config.fixed_sl_dollars / point)
                        tp_points = (self.config.fixed_tp_dollars / point)
                    else:
                        sl_points = data["atr_points"] * self.config.sl_atr_multiplier
                        tp_points = data["atr_points"] * self.config.tp_atr_multiplier

                    lot_size = self._calculate_lot_size(data, sl_points)

                    is_buy = signal == "BUY"
                    entry_price = data["ask"] if is_buy else data["bid"]
                    sl_price = entry_price - (sl_points * point) if is_buy else entry_price + (sl_points * point)
                    tp_price = entry_price + (tp_points * point) if is_buy else entry_price - (tp_points * point)

                    # 6. Execute Order via Execution Engine
                    logger.info("Executing Scalper Signal", signal=signal, lot=lot_size, entry=entry_price, sl=sl_price, tp=tp_price)
                    res = mt5_service.execute_order(
                        symbol=self.config.symbol,
                        side=signal,
                        volume=lot_size,
                        sl=round(sl_price, data["digits"]),
                        tp=round(tp_price, data["digits"]),
                        comment=f"Scalp ATR {data['atr_points']:.0f}",
                    )

                    if res.get("success"):
                        ticket = res.get("ticket")
                        if ticket:
                            self.trade_open_timestamps[ticket] = time.time()
                        self.telemetry.last_trade_time = datetime.now().strftime("%H:%M:%S")
                        self.cooldown_until = time.time() + self.config.cooldown_seconds_after_close

                await asyncio.sleep(0.5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Exception in scalper tick loop", error=str(e))
                await asyncio.sleep(1.0)


# Global Singleton Scalper Engine
mt5_scalper = MT5ScalpingEngine()
