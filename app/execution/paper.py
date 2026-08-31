"""
app/execution/paper.py
───────────────────────
Paper trading execution engine.
Simulates fills with fees, spread, and slippage.
Tracks positions in PostgreSQL.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.execution.base import ExecutionEngine
from app.risk.manager import risk_manager

logger = get_logger("trading")

# Bybit linear futures fee rates
TAKER_FEE = 0.00055   # 0.055%
MAKER_FEE = 0.0002    # 0.020%
SLIPPAGE_PCT = 0.0002  # 0.02% simulated slippage


class PaperExecutionEngine(ExecutionEngine):
    """
    Paper trading engine — simulates real execution.

    All positions are stored in memory and persisted to DB.
    Fees, slippage, and spread are modeled realistically.
    """

    def __init__(self) -> None:
        self._positions: dict[str, dict] = {}  # signal_id -> position

    async def open_position(
        self,
        signal_id: str,
        symbol: str,
        direction: str,
        entry_price: float,
        qty: float,
        stop_loss: float,
        take_profit_1: float,
        take_profit_2: Optional[float] = None,
        take_profit_3: Optional[float] = None,
    ) -> dict:
        """Simulate opening a position with taker fee + slippage."""
        # Apply slippage
        if direction == "LONG":
            fill_price = entry_price * (1 + SLIPPAGE_PCT)
        else:
            fill_price = entry_price * (1 - SLIPPAGE_PCT)

        fee = fill_price * qty * TAKER_FEE
        notional = fill_price * qty

        position = {
            "signal_id": signal_id,
            "symbol": symbol,
            "direction": direction,
            "entry_price": round(fill_price, 4),
            "qty": qty,
            "stop_loss": stop_loss,
            "take_profit_1": take_profit_1,
            "take_profit_2": take_profit_2,
            "take_profit_3": take_profit_3,
            "fee_paid": fee,
            "notional": notional,
            "opened_at": datetime.utcnow(),
            "status": "OPEN",
        }

        self._positions[signal_id] = position
        risk_manager.open_position(symbol)

        logger.info(
            "Paper position opened",
            signal_id=signal_id,
            symbol=symbol,
            direction=direction,
            fill_price=fill_price,
            qty=qty,
            fee=round(fee, 4),
        )

        return position

    async def close_position(
        self,
        signal_id: str,
        exit_price: float,
        reason: str = "MANUAL",
    ) -> dict:
        """Simulate closing a position."""
        pos = self._positions.get(signal_id)
        if not pos:
            logger.warning("Position not found", signal_id=signal_id)
            return {}

        direction = pos["direction"]
        entry_price = pos["entry_price"]
        qty = pos["qty"]

        # Apply slippage on exit
        if direction == "LONG":
            fill_exit = exit_price * (1 - SLIPPAGE_PCT)
            raw_pnl = (fill_exit - entry_price) * qty
        else:
            fill_exit = exit_price * (1 + SLIPPAGE_PCT)
            raw_pnl = (entry_price - fill_exit) * qty

        exit_fee = fill_exit * qty * TAKER_FEE
        net_pnl = raw_pnl - exit_fee - pos.get("fee_paid", 0)
        pnl_pct = net_pnl / pos["notional"]

        pos.update({
            "status": reason,
            "exit_price": round(fill_exit, 4),
            "realized_pnl": round(net_pnl, 4),
            "pnl_pct": round(pnl_pct, 6),
            "closed_at": datetime.utcnow(),
        })

        risk_manager.close_position(pos["symbol"], pnl_pct)

        logger.info(
            "Paper position closed",
            signal_id=signal_id,
            symbol=pos["symbol"],
            direction=direction,
            pnl_usd=round(net_pnl, 2),
            pnl_pct=round(pnl_pct * 100, 2),
            reason=reason,
        )

        return pos

    async def modify_stop_loss(self, signal_id: str, new_stop_loss: float) -> bool:
        pos = self._positions.get(signal_id)
        if not pos:
            return False
        pos["stop_loss"] = new_stop_loss
        logger.info("Stop loss modified", signal_id=signal_id, new_sl=new_stop_loss)
        return True

    async def get_open_positions(self) -> list[dict]:
        return [p for p in self._positions.values() if p.get("status") == "OPEN"]

    async def update_mark_price(self, symbol: str, mark_price: float) -> None:
        """
        Update unrealized PnL for all positions on this symbol.
        Call this on every price tick.
        Automatically closes positions that hit SL/TP.
        """
        for sig_id, pos in list(self._positions.items()):
            if pos.get("symbol") != symbol or pos.get("status") != "OPEN":
                continue

            direction = pos["direction"]
            sl = pos["stop_loss"]
            tp1 = pos["take_profit_1"]
            tp2 = pos.get("take_profit_2")
            tp3 = pos.get("take_profit_3")

            # Check SL/TP
            if direction == "LONG":
                if mark_price <= sl:
                    await self.close_position(sig_id, mark_price, "STOPPED_OUT")
                elif tp3 and mark_price >= tp3:
                    await self.close_position(sig_id, mark_price, "TP3")
                elif tp2 and mark_price >= tp2:
                    await self.close_position(sig_id, mark_price, "TP2")
                elif mark_price >= tp1:
                    await self.close_position(sig_id, mark_price, "TP1")
            else:
                if mark_price >= sl:
                    await self.close_position(sig_id, mark_price, "STOPPED_OUT")
                elif tp3 and mark_price <= tp3:
                    await self.close_position(sig_id, mark_price, "TP3")
                elif tp2 and mark_price <= tp2:
                    await self.close_position(sig_id, mark_price, "TP2")
                elif mark_price <= tp1:
                    await self.close_position(sig_id, mark_price, "TP1")


# Singleton
paper_engine = PaperExecutionEngine()
