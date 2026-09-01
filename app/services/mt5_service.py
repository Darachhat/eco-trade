"""
app/services/mt5_service.py
───────────────────────────
MetaTrader 5 Service Bridge for Exness (Demo & Real) Execution.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from datetime import datetime

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False

from app.core.logging import get_logger

logger = get_logger("mt5_service")

# Common Exness symbol mappings
SYMBOL_MAP = {
    "BTCUSDT": ["BTCUSDm", "BTCUSDTm", "BTCUSD"],
    "XAUUSDT": ["XAUUSDm", "XAUUSD", "XAUUSD247m"],
    "BTCUSD": ["BTCUSDm", "BTCUSDTm", "BTCUSD"],
    "XAUUSD": ["XAUUSDm", "XAUUSD", "XAUUSD247m"],
}

DEFAULT_TERMINAL_PATH = r"C:\Program Files\MetaTrader 5\terminal64.exe"


class MT5BridgeService:
    def __init__(self) -> None:
        self.is_connected = False
        self.active_login: Optional[int] = None
        self.active_server: Optional[str] = None
        self.terminal_path = DEFAULT_TERMINAL_PATH

    def initialize_and_login(
        self,
        login: int = 463894594,
        password: str = "cHhat#2023",
        server: str = "Exness-MT5Trial17",
        path: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not MT5_AVAILABLE:
            return {"success": False, "error": "MetaTrader5 Python library is not installed"}

        target_path = path or self.terminal_path
        if not os.path.exists(target_path):
            # Fallback path search
            for alt in [
                r"C:\Program Files\MetaTrader 5\terminal64.exe",
                r"C:\Program Files\Investizo MT5 Terminal\terminal64.exe",
            ]:
                if os.path.exists(alt):
                    target_path = alt
                    break

        self.terminal_path = target_path

        try:
            # Shutdown previous instance if open
            mt5.shutdown()

            initialized = mt5.initialize(
                path=target_path,
                login=int(login),
                password=str(password),
                server=str(server),
                timeout=15000,
            )

            if not initialized:
                err = mt5.last_error()
                logger.error("MT5 initialization failed", error=err)
                self.is_connected = False
                return {"success": False, "error": f"MT5 Init Error: {err}"}

            acc = mt5.account_info()
            if acc is None:
                err = mt5.last_error()
                self.is_connected = False
                return {"success": False, "error": f"Failed to retrieve account info: {err}"}

            self.is_connected = True
            self.active_login = login
            self.active_server = server

            logger.info("Connected to MT5 Exness", login=login, server=server, balance=acc.balance)

            return {
                "success": True,
                "account": {
                    "login": acc.login,
                    "server": acc.server,
                    "company": acc.company,
                    "currency": acc.currency,
                    "balance": float(acc.balance),
                    "equity": float(acc.equity),
                    "margin": float(acc.margin),
                    "free_margin": float(acc.margin_free),
                    "leverage": int(acc.leverage),
                    "trade_allowed": bool(acc.trade_allowed),
                    "profit": float(acc.profit),
                },
            }
        except Exception as e:
            logger.exception("MT5 connection exception", error=str(e))
            self.is_connected = False
            return {"success": False, "error": str(e)}

    def get_account_status(self) -> Dict[str, Any]:
        if not MT5_AVAILABLE or not self.is_connected:
            return {"connected": False}

        acc = mt5.account_info()
        if acc is None:
            return {"connected": False}

        return {
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
        }

    def _resolve_symbol(self, generic_symbol: str) -> Optional[str]:
        """Resolves EcoTrade symbol (e.g. XAUUSDT or BTCUSDT) to active Exness symbol (e.g. XAUUSDm)."""
        candidates = SYMBOL_MAP.get(generic_symbol, [generic_symbol])

        # Test which symbol exists and is selectable in MT5 MarketWatch
        for cand in candidates:
            info = mt5.symbol_info(cand)
            if info is not None:
                if not info.visible:
                    mt5.symbol_select(cand, True)
                return cand

        # Try generic search
        all_syms = mt5.symbols_get()
        if all_syms:
            for s in all_syms:
                if generic_symbol.replace("USDT", "") in s.name:
                    mt5.symbol_select(s.name, True)
                    return s.name

        return None

    def get_open_positions(self) -> List[Dict[str, Any]]:
        if not MT5_AVAILABLE or not self.is_connected:
            return []

        positions = mt5.positions_get()
        if positions is None:
            return []

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
                "swap": float(p.swap),
                "time": datetime.fromtimestamp(p.time).isoformat(),
                "comment": p.comment,
            })
        return pos_list

    def execute_order(
        self,
        symbol: str,
        side: str,  # "BUY" / "SELL" or "LONG" / "SHORT"
        volume: float = 0.01,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        comment: str = "EcoTrade AI Signal",
    ) -> Dict[str, Any]:
        if not MT5_AVAILABLE or not self.is_connected:
            return {"success": False, "error": "MT5 is not connected"}

        mt5_symbol = self._resolve_symbol(symbol)
        if not mt5_symbol:
            return {"success": False, "error": f"Symbol {symbol} not found on Exness MT5"}

        tick = mt5.symbol_info_tick(mt5_symbol)
        if tick is None:
            return {"success": False, "error": f"Could not fetch tick for {mt5_symbol}"}

        is_buy = side.upper() in ["BUY", "LONG"]
        order_type = mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL
        price = tick.ask if is_buy else tick.bid

        # Determine filling mode supported by broker
        sym_info = mt5.symbol_info(mt5_symbol)
        filling_mode = mt5.ORDER_FILLING_IOC
        if sym_info and sym_info.filling_mode == 1:
            filling_mode = mt5.ORDER_FILLING_FOK
        elif sym_info and sym_info.filling_mode == 2:
            filling_mode = mt5.ORDER_FILLING_IOC

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": mt5_symbol,
            "volume": float(volume),
            "type": order_type,
            "price": float(price),
            "sl": float(sl) if sl else 0.0,
            "tp": float(tp) if tp else 0.0,
            "deviation": 20,
            "magic": 234000,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_mode,
        }

        logger.info("Sending MT5 Order request", request=request)
        result = mt5.order_send(request)

        if result is None:
            err = mt5.last_error()
            return {"success": False, "error": f"Order Send Failed: {err}"}

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return {
                "success": False,
                "retcode": result.retcode,
                "comment": result.comment,
                "error": f"Trade rejected by Exness MT5: {result.comment} (code {result.retcode})",
            }

        return {
            "success": True,
            "ticket": result.order,
            "deal": result.deal,
            "volume": result.volume,
            "price": result.price,
            "symbol": mt5_symbol,
            "comment": result.comment,
        }

    def close_position(self, ticket: int) -> Dict[str, Any]:
        if not MT5_AVAILABLE or not self.is_connected:
            return {"success": False, "error": "MT5 is not connected"}

        positions = mt5.positions_get(ticket=ticket)
        if not positions or len(positions) == 0:
            return {"success": False, "error": f"Position ticket {ticket} not found"}

        pos = positions[0]
        is_buy = pos.type == mt5.ORDER_TYPE_BUY
        close_type = mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY

        tick = mt5.symbol_info_tick(pos.symbol)
        if tick is None:
            return {"success": False, "error": f"Could not fetch tick for {pos.symbol}"}

        close_price = tick.bid if is_buy else tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": ticket,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": close_type,
            "price": close_price,
            "deviation": 20,
            "magic": 234000,
            "comment": "EcoTrade Close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            err = result.comment if result else str(mt5.last_error())
            return {"success": False, "error": f"Close position failed: {err}"}

        return {"success": True, "ticket": ticket, "deal": result.deal, "price": result.price}


# Global singleton instance
mt5_service = MT5BridgeService()
