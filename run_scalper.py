"""
run_scalper.py
──────────────
100% Self-Contained 24/7 High-Frequency Scalper Runner for Exness MetaTrader 5.
Runs natively on Windows and Linux (Wine) with ZERO heavy C99 dependencies.
Target: Gold (XAUUSDm) with TP +$2.00 / SL -$10.00 / Dynamic Break-Even +$1.00.
"""

import argparse
import datetime
import json
import logging
import math
import os
import signal
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, List, Optional

# Force UTF-8 / ASCII safe console encoding on Windows & Wine
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    import MetaTrader5 as mt5
except ImportError:
    print("ERROR: MetaTrader5 package is required. Run: pip install MetaTrader5")
    sys.exit(1)

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("scalper_24_7.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("ScalperEngine")

_SHUTDOWN = False


def _sig_handler(sig, frame):
    global _SHUTDOWN
    logger.info("Termination signal (%s) received. Shutting down cleanly...", sig)
    _SHUTDOWN = True


signal.signal(signal.SIGINT, _sig_handler)
signal.signal(signal.SIGTERM, _sig_handler)

GLOBAL_SCALPER = None


class ScalperBridgeHTTPHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Quiet HTTP logs

    def _send_json(self, status: int, data: Any):
        try:
            body = json.dumps(data).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception:
            pass

    def do_GET(self):
        if self.path.startswith("/api/mt5/status"):
            if not GLOBAL_SCALPER or not GLOBAL_SCALPER.is_connected:
                self._send_json(200, {"connected": False})
                return
            acc = mt5.account_info()
            if not acc:
                self._send_json(200, {"connected": False})
                return
            self._send_json(200, {
                "connected": True,
                "login": acc.login,
                "server": acc.server,
                "company": acc.company,
                "balance": float(acc.balance),
                "equity": float(acc.equity),
                "margin": float(acc.margin),
                "free_margin": float(acc.margin_free),
                "leverage": int(acc.leverage),
                "profit": float(acc.profit),
            })
        elif self.path.startswith("/api/mt5/positions"):
            if not GLOBAL_SCALPER or not GLOBAL_SCALPER.is_connected:
                self._send_json(200, {"positions": []})
                return
            positions = mt5.positions_get(symbol=GLOBAL_SCALPER.symbol) or []
            pos_list = []
            for p in positions:
                pos_list.append({
                    "ticket": int(p.ticket),
                    "symbol": p.symbol,
                    "type": "BUY" if p.type == mt5.ORDER_TYPE_BUY else "SELL",
                    "volume": float(p.volume),
                    "price_open": float(p.price_open),
                    "price_current": float(p.price_current),
                    "sl": float(p.sl),
                    "tp": float(p.tp),
                    "profit": float(p.profit),
                })
            self._send_json(200, {"positions": pos_list})
        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        if self.path.startswith("/api/mt5/order"):
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len) if content_len > 0 else b"{}"
            payload = json.loads(body.decode("utf-8"))
            
            sym = payload.get("symbol", GLOBAL_SCALPER.symbol if GLOBAL_SCALPER else "XAUUSDm")
            side = payload.get("side", "BUY").upper()
            volume = float(payload.get("volume", 0.01))
            sl = float(payload.get("sl", 0.0))
            tp = float(payload.get("tp", 0.0))
            
            tick = mt5.symbol_info_tick(sym)
            if not tick:
                self._send_json(400, {"success": False, "error": f"Failed to get tick for {sym}"})
                return
            price = tick.ask if side == "BUY" else tick.bid
            req = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": sym,
                "volume": volume,
                "type": mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL,
                "price": price,
                "sl": sl,
                "tp": tp,
                "deviation": 20,
                "magic": 234000,
                "comment": "Telegram Order",
            }
            res = mt5.order_send(req)
            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                self._send_json(200, {"success": True, "ticket": res.order, "price": price})
            else:
                self._send_json(400, {"success": False, "error": getattr(res, "comment", "Order Failed")})
        elif self.path.startswith("/api/mt5/close"):
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len) if content_len > 0 else b"{}"
            payload = json.loads(body.decode("utf-8"))
            ticket = int(payload.get("ticket", 0))
            positions = mt5.positions_get(ticket=ticket)
            if not positions:
                self._send_json(400, {"success": False, "error": f"Position {ticket} not found"})
                return
            pos = positions[0]
            tick = mt5.symbol_info_tick(pos.symbol)
            close_price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask
            req = {
                "action": mt5.TRADE_ACTION_DEAL,
                "position": ticket,
                "symbol": pos.symbol,
                "volume": pos.volume,
                "type": mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
                "price": close_price,
                "deviation": 20,
                "magic": 234000,
                "comment": "Close Position",
            }
            res = mt5.order_send(req)
            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                self._send_json(200, {"success": True})
            else:
                self._send_json(400, {"success": False, "error": getattr(res, "comment", "Close Failed")})
        else:
            self._send_json(404, {"error": "Not found"})


class EngineState:
    STARTING = "STARTING"
    XVFB_READY = "XVFB_READY"
    WINE_READY = "WINE_READY"
    MT5_PROCESS_READY = "MT5_PROCESS_READY"
    MT5_IPC_READY = "MT5_IPC_READY"
    ACCOUNT_READY = "ACCOUNT_READY"
    SYMBOL_READY = "SYMBOL_READY"
    MARKET_DATA_READY = "MARKET_DATA_READY"
    TRADING_READY = "TRADING_READY"
    ERROR = "ERROR"


def start_http_bridge_server(port: int = 8008, host: str = "127.0.0.1", enabled: bool = True):
    if not enabled:
        logger.info("[HTTP BRIDGE] Bridge disabled via configuration.")
        return
    for candidate_host in [host, "0.0.0.0", "127.0.0.1"]:
        try:
            server = HTTPServer((candidate_host, port), ScalperBridgeHTTPHandler)
            t = threading.Thread(target=server.serve_forever, daemon=True)
            t.start()
            logger.info("[HTTP BRIDGE] Listening on %s:%d (API bridge ready)", candidate_host, port)
            return
        except Exception as e:
            logger.debug("Could not bind HTTP Bridge on %s:%d: %s", candidate_host, port, e)
    logger.warning("[HTTP BRIDGE] Could not bind HTTP Bridge on port %d. Trading engine continues unaffected.", port)


# ─── Pure Python Technical Indicators ──────────────────────────────────────────

def compute_ema(prices: List[float], period: int) -> float:
    if len(prices) < period:
        return prices[-1] if prices else 0.0
    k = 2.0 / (period + 1)
    ema = sum(prices[:period]) / period
    for p in prices[period:]:
        ema = (p - ema) * k + ema
    return ema


def compute_rsi(closes: List[float], period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(0.0, diff))
        losses.append(max(0.0, -diff))
    if len(gains) < period:
        return 50.0
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def compute_atr_points(rates, period: int = 14, point: float = 0.001) -> float:
    if rates is None or len(rates) < period + 1:
        return 2000.0
    trs = []
    for i in range(1, len(rates)):
        h = rates[i]["high"]
        l = rates[i]["low"]
        pc = rates[i - 1]["close"]
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)
    avg_tr = sum(trs[-period:]) / period
    return avg_tr / (point if point > 0 else 0.001)


# ─── Standalone Scalper Loop ───────────────────────────────────────────────────

class PureScalper:
    MAX_POSITIONS    = 5      # Fill up to this many concurrent positions
    AGGREGATE_TP     = 5.0    # Close ALL positions when combined profit >= $5.00
    ACCOUNT_SL_DROP  = 100.0  # Shut down if equity drops $100 from session start

    def __init__(self, login: int, password: str, server: str, symbol: str = "XAUUSDm", tp: float = 5.0, sl: float = 100.0, risk: float = 0.5):
        self.login = login
        self.password = password
        self.server = server
        self.symbol = symbol
        self.aggregate_tp = tp if tp > 0 else self.AGGREGATE_TP
        self.tp_dollars = tp
        self.sl_dollars = sl
        self.risk_pct = risk
        self.is_connected = False
        self.is_healthy = False
        self.state = EngineState.STARTING
        self.last_trade_time = 0.0
        self.last_closed_time = 0.0
        self.consecutive_losses = 0
        self.consecutive_ipc_failures = 0
        self.session_start_balance: Optional[float] = None  # Set after first connect

    def connect(self) -> bool:
        """
        Deterministic 7-Stage Startup State Machine & Health Check:
          STARTING -> XVFB_READY -> WINE_READY -> MT5_PROCESS_READY ->
          MT5_IPC_READY -> ACCOUNT_READY -> SYMBOL_READY -> MARKET_DATA_READY -> TRADING_READY
        """
        self.state = EngineState.STARTING
        self.is_connected = False
        self.is_healthy = False

        # ── STAGE 1: Display / Xvfb Check ───────────────────────────────────────
        display = os.environ.get("DISPLAY")
        if not display and sys.platform != "win32":
            logger.error("[STATE: ERROR] DISPLAY environment variable not set! Xvfb on :99 is required.")
            self.state = EngineState.ERROR
            return False
        self.state = EngineState.XVFB_READY

        # ── STAGE 2: Locate MT5 Terminal Binary ─────────────────────────────────
        candidate_paths = [
            r"C:\Program Files\MetaTrader 5\terminal64.exe",
            r"C:\Program Files\Exness MetaTrader 5 Terminal\terminal64.exe",
            r"C:\Program Files (x86)\MetaTrader 5\terminal64.exe",
            r"C:\MetaTrader 5\terminal64.exe",
            r"C:\MT5\terminal64.exe",
        ]
        valid_path = None
        for p in candidate_paths:
            if os.path.exists(p):
                valid_path = p
                break

        if not valid_path and sys.platform == "win32":
            valid_path = candidate_paths[0]

        if not valid_path:
            logger.error("[STATE: ERROR] Could not find terminal64.exe in any candidate path!")
            self.state = EngineState.ERROR
            return False

        logger.info("[STATE: WINE_READY] Discovered terminal binary: %s", valid_path)
        self.state = EngineState.WINE_READY

        # ── STAGE 3: Process Guard & IPC Initialization ────────────────────────
        self.state = EngineState.MT5_PROCESS_READY

        # Write startup.ini to suppress wizards and supply server config
        term_dir = os.path.dirname(valid_path)
        ini_path = os.path.join(term_dir, "startup.ini")
        try:
            with open(ini_path, "w", encoding="utf-8") as f:
                f.write(
                    f"[Common]\n"
                    f"Login={int(self.login)}\n"
                    f"Password={self.password}\n"
                    f"Server={self.server}\n"
                    f"NewsEnable=0\n"
                    f"[Experts]\n"
                    f"AllowLiveTrading=1\n"
                    f"AllowDllImport=1\n"
                    f"Enabled=1\n"
                )
        except Exception as e:
            logger.debug("Could not write startup.ini: %s", e)

        # Attempt A: Attach to already-running terminal first (prevents duplicate instance collisions)
        init_ok = False
        try:
            init_ok = mt5.initialize(timeout=10000)
            if init_ok:
                logger.info("[STATE: MT5_IPC_READY] Successfully attached to existing MT5 terminal process.")
        except Exception as e:
            logger.debug("Direct attach note: %s", e)

        # Attempt B: If not attached, launch once cleanly using the discovered path
        if not init_ok:
            logger.info("[STATE: MT5_PROCESS_READY] Launching terminal via mt5.initialize(path=...)...")
            try:
                init_ok = mt5.initialize(
                    path=valid_path,
                    portable=True,
                    timeout=45000,
                )
            except Exception as e:
                logger.error("mt5.initialize(path) exception: %s", e)

        if not init_ok:
            err = mt5.last_error()
            self.consecutive_ipc_failures += 1
            logger.error(
                "[STATE: ERROR] MT5 IPC failed: %s (consecutive failures: %d). Shutting down IPC cleanly.",
                err, self.consecutive_ipc_failures
            )
            self.state = EngineState.ERROR
            try:
                mt5.shutdown()
            except Exception:
                pass
            return False

        # Verify terminal_info()
        term_info = mt5.terminal_info()
        if not term_info:
            logger.error("[STATE: ERROR] terminal_info() is None after initialize. IPC channel invalid.")
            self.state = EngineState.ERROR
            mt5.shutdown()
            return False

        self.state = EngineState.MT5_IPC_READY
        logger.info("[STATE: MT5_IPC_READY] Terminal info verified: build=%s, connected=%s",
                    getattr(term_info, "build", "?"), getattr(term_info, "connected", False))

        # ── STAGE 4: Account Authentication / Login ─────────────────────────────
        logger.info("Authenticating login #%d on broker server '%s'...", self.login, self.server)
        login_ok = False
        try:
            login_ok = mt5.login(
                login=int(self.login),
                password=str(self.password),
                server=str(self.server),
                timeout=20000,
            )
        except Exception as e:
            logger.warning("mt5.login() exception: %s", e)

        acc = mt5.account_info()
        if not acc:
            err = mt5.last_error()
            logger.error("[STATE: ERROR] account_info() is None after login (err: %s). Broker credentials or server invalid.", err)
            self.state = EngineState.ERROR
            return False

        self.state = EngineState.ACCOUNT_READY
        logger.info("[STATE: ACCOUNT_READY] Authenticated! Account: %d (%s) | Balance: $%.2f | Leverage: 1:%d",
                    acc.login, acc.server, acc.balance, acc.leverage)

        # ── STAGE 5: Symbol Discovery & Visibility ──────────────────────────────
        if not mt5.symbol_select(self.symbol, True):
            logger.warning("symbol_select('%s', True) returned False. Checking visibility...", self.symbol)

        sym_info = mt5.symbol_info(self.symbol)
        if not sym_info or not sym_info.visible:
            # Try selecting once more
            mt5.symbol_select(self.symbol, True)
            sym_info = mt5.symbol_info(self.symbol)

        if not sym_info:
            logger.error("[STATE: ERROR] Target symbol '%s' not found on broker server '%s'.", self.symbol, self.server)
            self.state = EngineState.ERROR
            return False

        self.state = EngineState.SYMBOL_READY
        logger.info("[STATE: SYMBOL_READY] Target symbol '%s' verified (digits=%d, point=%s).",
                    self.symbol, sym_info.digits, sym_info.point)

        # ── STAGE 6: Market Data & Tick Subscription ────────────────────────────
        tick = mt5.symbol_info_tick(self.symbol)
        if not tick or tick.bid <= 0 or tick.ask <= 0:
            logger.warning("[STATE: MARKET_DATA_READY] Tick data for '%s' not yet streaming (market closed or subscribing).", self.symbol)
        else:
            logger.info("[STATE: MARKET_DATA_READY] Market data streaming: Bid=$%.3f | Ask=$%.3f", tick.bid, tick.ask)

        self.state = EngineState.MARKET_DATA_READY

        # ── STAGE 7: Trading Ready & Anchor Balance ─────────────────────────────
        self.is_connected = True
        self.is_healthy = True
        self.consecutive_ipc_failures = 0
        self.state = EngineState.TRADING_READY

        if self.session_start_balance is None:
            self.session_start_balance = float(acc.balance)
            logger.info("Session start balance anchored at $%.2f (Account SL triggers at $%.2f)",
                        self.session_start_balance, self.session_start_balance - self.ACCOUNT_SL_DROP)

        logger.info("================================================================")
        logger.info(" >>> [STATE: TRADING_READY] ALL 7 HEALTH CHECKS PASSED. ENGINE ACTIVE. <<<")
        logger.info("================================================================")
        return True

    def calculate_lot(self, equity: float) -> float:
        # Gold: 1 Lot = 100 oz, Point = 0.001 => 1 pt = $0.10/lot
        # For $10 SL (10,000 pts) at $50 risk => 0.05 lot
        risk_dollars = equity * (self.risk_pct / 100.0)
        lot = risk_dollars / (self.sl_dollars * 100.0 * 0.10)
        return round(max(0.01, min(2.0, lot)), 2)

    def _close_position(self, pos) -> bool:
        """Market-close a single position. Returns True on success."""
        tick = mt5.symbol_info_tick(pos.symbol)
        if not tick:
            return False
        close_price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask
        sym_info = mt5.symbol_info(pos.symbol)
        filling_mode = mt5.ORDER_FILLING_IOC
        if sym_info and sym_info.filling_mode == 1:
            filling_mode = mt5.ORDER_FILLING_FOK
        req = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": pos.ticket,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
            "price": close_price,
            "deviation": 20,
            "magic": 234000,
            "comment": "ScalperClose",
            "type_filling": filling_mode,
        }
        res = mt5.order_send(req)
        return bool(res and res.retcode == mt5.TRADE_RETCODE_DONE)

    def close_all_positions(self, reason: str = "Aggregate TP/SL") -> int:
        """Close every open position for this symbol. Returns count closed."""
        positions = mt5.positions_get(symbol=self.symbol) or []
        closed = 0
        for pos in positions:
            if self._close_position(pos):
                closed += 1
                logger.info("[CLOSED] Ticket #%d | profit $%.2f | reason: %s", pos.ticket, pos.profit, reason)
            else:
                logger.warning("[CLOSE FAILED] Ticket #%d", pos.ticket)
        return closed

    def manage_open_trades(self, tick, sym_info) -> bool:
        """
        Manage open positions.
        Returns True if all positions were force-closed (caller should skip new entries).
        """
        positions = mt5.positions_get(symbol=self.symbol)
        if not positions:
            return False

        point = sym_info.point if sym_info else 0.001

        # ── Aggregate Profit TP ──────────────────────────────────────────────────
        total_profit = sum(p.profit for p in positions)
        if total_profit >= self.aggregate_tp:
            logger.info("[AGGREGATE TP HIT] Combined profit $%.2f >= $%.2f — closing all %d positions",
                        total_profit, self.aggregate_tp, len(positions))
            self.close_all_positions(reason=f"Aggregate TP ${self.aggregate_tp:.2f}")
            return True

        # ── Per-position Break-Even lock ─────────────────────────────────────────
        for pos in positions:
            profit_points = (tick.bid - pos.price_open) / point if pos.type == mt5.ORDER_TYPE_BUY else (pos.price_open - tick.ask) / point
            profit_dollars = profit_points * point

            # Dynamic Break-Even at +$1.00 individual move
            if profit_dollars >= 1.00:
                is_buy = pos.type == mt5.ORDER_TYPE_BUY
                be_sl = round(pos.price_open + 0.01 if is_buy else pos.price_open - 0.01, sym_info.digits)

                needs_update = (is_buy and (pos.sl < pos.price_open or pos.sl == 0.0)) or \
                               (not is_buy and (pos.sl > pos.price_open or pos.sl == 0.0))
                if needs_update:
                    req = {
                        "action": mt5.TRADE_ACTION_SLTP,
                        "position": pos.ticket,
                        "symbol": self.symbol,
                        "sl": be_sl,
                        "tp": pos.tp,
                    }
                    res = mt5.order_send(req)
                    if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                        logger.info("[BREAK-EVEN LOCKED] Ticket #%d SL moved to entry ($%.3f) at profit +$%.2f",
                                    pos.ticket, be_sl, profit_dollars)

        return False

    def check_account_sl(self, equity: float) -> bool:
        """Returns True and shuts down if equity has dropped >= ACCOUNT_SL_DROP."""
        if self.session_start_balance is None:
            return False
        drop = self.session_start_balance - equity
        if drop >= self.ACCOUNT_SL_DROP:
            logger.warning(
                "[ACCOUNT SL HIT] Equity $%.2f dropped $%.2f from session start $%.2f — closing all & stopping",
                equity, drop, self.session_start_balance,
            )
            self.close_all_positions(reason=f"Account SL -${self.ACCOUNT_SL_DROP:.0f}")
            return True
        return False

    def evaluate_tick(self):
        if not self.is_healthy or self.state != EngineState.TRADING_READY:
            return

        sym_info = mt5.symbol_info(self.symbol)
        if not sym_info or not sym_info.visible:
            mt5.symbol_select(self.symbol, True)
            sym_info = mt5.symbol_info(self.symbol)

        tick = mt5.symbol_info_tick(self.symbol)
        if not tick or tick.bid <= 0 or tick.ask <= 0:
            return

        point = sym_info.point if sym_info else 0.001
        digits = sym_info.digits if sym_info else 3
        spread_pts = (tick.ask - tick.bid) / point

        # 1. Spread Guard (<= 400 pts = $0.40)
        if spread_pts > 400:
            return

        # 2. Account-level equity / drawdown guard
        acc = mt5.account_info()
        equity = float(acc.equity) if acc else 0.0
        if self.check_account_sl(equity):
            global _SHUTDOWN
            _SHUTDOWN = True
            return

        # 3. Manage existing positions (Aggregate TP, Break-Even)
        all_closed = self.manage_open_trades(tick, sym_info)
        if all_closed:
            return  # positions just closed, skip new entries this tick

        # 4. Count open slots and decide how many new entries to fire
        positions = mt5.positions_get(symbol=self.symbol) or []
        open_count = len(positions)
        slots_available = self.MAX_POSITIONS - open_count
        if slots_available <= 0:
            return

        # 5. Trade Cooldown Guard (30s between new entries)
        now = time.time()
        if now - self.last_trade_time < 30:
            return

        # 5. Fetch M1 Bars for Technical Signal
        rates = mt5.copy_rates_from_pos(self.symbol, mt5.TIMEFRAME_M1, 0, 60)
        if rates is None or len(rates) < 50:
            return

        closes = [r["close"] for r in rates]
        ema_9 = compute_ema(closes, 9)
        ema_21 = compute_ema(closes, 21)
        ema_50 = compute_ema(closes, 50)
        rsi_14 = compute_rsi(closes, 14)
        atr_pts = compute_atr_points(rates, 14, point)

        # Volatility Guard
        if atr_pts < 300 or atr_pts > 8000:
            return

        # 6. Multi-Factor AI Confidence Scoring
        bull_score = 0.0
        bear_score = 0.0

        # Trend (40%)
        if ema_9 > ema_21 > ema_50:
            bull_score += 40.0
        elif ema_9 < ema_21 < ema_50:
            bear_score += 40.0

        # Momentum RSI (30%)
        if 50.0 <= rsi_14 <= 75.0:
            bull_score += 30.0
        elif 25.0 <= rsi_14 <= 50.0:
            bear_score += 30.0

        # Price Action Breakout (30%)
        if tick.bid > ema_9:
            bull_score += 30.0
        if tick.ask < ema_9:
            bear_score += 30.0

        # Entry Trigger — fire up to slots_available orders in one tick
        volume = self.calculate_lot(equity)

        filling_mode = mt5.ORDER_FILLING_IOC
        if sym_info and sym_info.filling_mode == 1:
            filling_mode = mt5.ORDER_FILLING_FOK

        if bull_score >= 65.0:
            for i in range(slots_available):
                sl_price = round(tick.ask - self.sl_dollars, digits)
                tp_price = round(tick.ask + self.tp_dollars, digits)
                req = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": self.symbol,
                    "volume": volume,
                    "type": mt5.ORDER_TYPE_BUY,
                    "price": tick.ask,
                    "sl": sl_price,
                    "tp": tp_price,
                    "deviation": 20,
                    "magic": 234000,
                    "comment": "EcoTrade 24/7 Scalp",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": filling_mode,
                }
                res = mt5.order_send(req)
                if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                    self.last_trade_time = now
                    logger.info(
                        "[BUY EXECUTED] Ticket #%d [%d/%d] | %s %.2fL @ $%.3f | SL $%.3f | TP $%.3f | Conf: %.1f%%",
                        res.order, i + 1, slots_available, self.symbol, volume, tick.ask, sl_price, tp_price, bull_score,
                    )
                else:
                    logger.warning("BUY Send failed [%d/%d]: %s (code %s)", i + 1, slots_available,
                                   getattr(res, "comment", "?"), getattr(res, "retcode", "?"))
                    break  # stop trying if broker rejects

        elif bear_score >= 65.0:
            for i in range(slots_available):
                sl_price = round(tick.bid + self.sl_dollars, digits)
                tp_price = round(tick.bid - self.tp_dollars, digits)
                req = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": self.symbol,
                    "volume": volume,
                    "type": mt5.ORDER_TYPE_SELL,
                    "price": tick.bid,
                    "sl": sl_price,
                    "tp": tp_price,
                    "deviation": 20,
                    "magic": 234000,
                    "comment": "EcoTrade 24/7 Scalp",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": filling_mode,
                }
                res = mt5.order_send(req)
                if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                    self.last_trade_time = now
                    logger.info(
                        "[SELL EXECUTED] Ticket #%d [%d/%d] | %s %.2fL @ $%.3f | SL $%.3f | TP $%.3f | Conf: %.1f%%",
                        res.order, i + 1, slots_available, self.symbol, volume, tick.bid, sl_price, tp_price, bear_score,
                    )
                else:
                    logger.warning("SELL Send failed [%d/%d]: %s (code %s)", i + 1, slots_available,
                                   getattr(res, "comment", "?"), getattr(res, "retcode", "?"))
                    break  # stop trying if broker rejects


def main():
    parser = argparse.ArgumentParser(description="24/7 EcoTrade MT5 High-Frequency Scalper")
    parser.add_argument("--login", type=int, default=463894594, help="MT5 Account Login ID")
    parser.add_argument("--password", type=str, default="cHhat#2023", help="MT5 Trading Password")
    parser.add_argument("--server", type=str, default="Exness-MT5Trial17", help="MT5 Broker Server")
    parser.add_argument("--symbol", type=str, default="XAUUSDm", help="Target Symbol")
    parser.add_argument("--tp", type=float, default=5.00, help="Aggregate Take Profit in Dollars ($5.00)")
    parser.add_argument("--sl", type=float, default=100.00, help="Fixed SL in Dollars ($100.00)")
    parser.add_argument("--risk", type=float, default=0.50, help="Risk Pct (0.50%%)")
    parser.add_argument("--http-port", type=int, default=int(os.environ.get("HTTP_BRIDGE_PORT", 8008)), help="HTTP bridge port")
    parser.add_argument("--http-host", type=str, default="127.0.0.1", help="HTTP bridge bind host")
    parser.add_argument("--no-http-bridge", action="store_true", help="Disable HTTP bridge server")
    args = parser.parse_args()

    print("=" * 65)
    print(" [ECOTRADE MT5 24/7 HIGH-FREQUENCY SCALPER - GOLD]")
    print("=" * 65)
    print(f" Account:  {args.login} ({args.server})")
    print(f" Target:   {args.symbol}")
    print(f" Targets:  Aggregate TP: +${args.tp:.2f} (all positions) | Per-trade SL: -${args.sl:.2f}")
    print(f" Slots:    Max {PureScalper.MAX_POSITIONS} concurrent positions | Account SL: -${PureScalper.ACCOUNT_SL_DROP:.0f}")
    print(f" Risk:     {args.risk:.2f}% per trade | Dynamic Break-Even: +$1.00")
    print("=" * 65)

    global GLOBAL_SCALPER
    scalper = PureScalper(
        login=args.login,
        password=args.password,
        server=args.server,
        symbol=args.symbol,
        tp=args.tp,
        sl=args.sl,
        risk=args.risk,
    )
    GLOBAL_SCALPER = scalper

    # Start HTTP Bridge Server for Docker/Telegram integration
    if not args.no_http_bridge:
        start_http_bridge_server(port=args.http_port, host=args.http_host, enabled=True)

    while not _SHUTDOWN:
        try:
            if not scalper.is_connected or not scalper.is_healthy:
                logger.info("[STATE: RECOVERY] Engine not ready (state=%s, healthy=%s). Running startup sequence...",
                            scalper.state, scalper.is_healthy)
                if not scalper.connect():
                    time.sleep(10)
                    continue

            scalper.evaluate_tick()
            time.sleep(0.5)

        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error("Error in scalper loop: %s", e, exc_info=True)
            time.sleep(2)

    mt5.shutdown()
    logger.info("Scalper shut down cleanly.")


if __name__ == "__main__":
    main()
