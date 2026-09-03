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


def start_http_bridge_server(port: int = 8008):
    try:
        server = HTTPServer(("0.0.0.0", port), ScalperBridgeHTTPHandler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        logger.info("[HTTP BRIDGE] Listening on 0.0.0.0:%d (Docker bridge ready)", port)
    except Exception as e:
        logger.warning("Could not bind HTTP Bridge on port %d: %s", port, e)


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
        self.last_trade_time = 0.0
        self.last_closed_time = 0.0
        self.consecutive_losses = 0
        self.session_start_balance: Optional[float] = None  # Set after first connect

    def connect(self) -> bool:
        mt5.shutdown()
        import subprocess

        # Scan candidate paths
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

        init_ok = False
        if valid_path:
            logger.info("Found MT5 terminal binary: %s", valid_path)
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

            try:
                # First try attaching to the already-running terminal directly
                init_ok = mt5.initialize(
                    login=int(self.login),
                    password=str(self.password),
                    server=str(self.server),
                    timeout=15000,
                )
            except Exception:
                pass

            if not init_ok:
                try:
                    # If not running, launch with path
                    init_ok = mt5.initialize(
                        path=valid_path,
                        login=int(self.login),
                        password=str(self.password),
                        server=str(self.server),
                        portable=True,
                        timeout=60000,
                    )
                except Exception:
                    pass

        if not init_ok:
            err = mt5.last_error()
            logger.error("MT5 Init failed: %s", err)
            self.is_connected = False
            return False

        acc = mt5.account_info()
        if not acc:
            logger.error("Failed to read account info: %s", mt5.last_error())
            self.is_connected = False
            return False

        # Select symbol
        mt5.symbol_select(self.symbol, True)
        self.is_connected = True
        if self.session_start_balance is None:
            self.session_start_balance = float(acc.balance)
            logger.info("Session start balance anchored at $%.2f (Account SL triggers at $%.2f)",
                        self.session_start_balance, self.session_start_balance - self.ACCOUNT_SL_DROP)
        logger.info("Connected to Exness MT5! Account: %d (%s) | Balance: $%.2f | Leverage: 1:%d", acc.login, acc.server, acc.balance, acc.leverage)
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
        sym_info = mt5.symbol_info(self.symbol)
        if not sym_info or not sym_info.visible:
            mt5.symbol_select(self.symbol, True)
            sym_info = mt5.symbol_info(self.symbol)

        tick = mt5.symbol_info_tick(self.symbol)
        if not tick or tick.bid <= 0:
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
    start_http_bridge_server(8008)

    while not _SHUTDOWN:
        try:
            if not scalper.is_connected:
                logger.info("Connecting to Exness MT5 broker...")
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
