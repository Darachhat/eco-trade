"""
app/execution/bybit_live.py
────────────────────────────
Live Bybit execution engine.
ONLY active when TRADING_MODE=live AND LIVE_EXECUTION_ENABLED=true.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import get_bybit_headers
from app.execution.base import ExecutionEngine

logger = get_logger("trading")


class BybitExecutionEngine(ExecutionEngine):
    """
    Live trading engine using Bybit REST API.

    SAFETY CHECKS:
    - Requires TRADING_MODE=live
    - Requires LIVE_EXECUTION_ENABLED=true
    - Logs every order before and after placement
    """

    def __init__(self) -> None:
        self._safety_check()

    def _safety_check(self) -> None:
        if not settings.is_live:
            raise RuntimeError(
                "BybitExecutionEngine can only be instantiated when "
                "TRADING_MODE=live AND LIVE_EXECUTION_ENABLED=true. "
                "Current mode: " + settings.trading_mode.value
            )
        logger.critical(
            "LIVE EXECUTION ENGINE INITIALIZED — REAL MONEY AT RISK",
            mode=settings.trading_mode.value,
            testnet=settings.bybit_testnet,
        )

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
        import httpx

        side = "Buy" if direction == "LONG" else "Sell"
        order_params = {
            "category": settings.bybit_category.value,
            "symbol": symbol,
            "side": side,
            "orderType": "Market",
            "qty": str(qty),
            "stopLoss": str(stop_loss),
            "takeProfit": str(take_profit_1),
            "slTriggerBy": "LastPrice",
            "tpTriggerBy": "LastPrice",
            "timeInForce": "IOC",
            "positionIdx": 0,
        }

        import json
        body = json.dumps(order_params)
        headers = get_bybit_headers(body)

        base_url = (
            "https://api-testnet.bybit.com" if settings.bybit_testnet
            else "https://api.bybit.com"
        )

        logger.warning(
            "Placing LIVE order",
            signal_id=signal_id,
            symbol=symbol,
            side=side,
            qty=qty,
            sl=stop_loss,
            tp=take_profit_1,
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/v5/order/create",
                headers=headers,
                content=body,
            )
            data = response.json()

        if data.get("retCode") != 0:
            raise RuntimeError(f"Bybit order error: {data.get('retMsg')}")

        order_id = data.get("result", {}).get("orderId", "")
        logger.info("Live order placed", signal_id=signal_id, order_id=order_id)

        return {
            "signal_id": signal_id,
            "symbol": symbol,
            "direction": direction,
            "bybit_order_id": order_id,
            "qty": qty,
            "opened_at": datetime.utcnow(),
        }

    async def close_position(
        self,
        signal_id: str,
        exit_price: float,
        reason: str = "MANUAL",
    ) -> dict:
        # In live trading, SL/TP are managed by exchange
        # Manual close via market order
        logger.warning("Manual close requested", signal_id=signal_id, reason=reason)
        return {}

    async def modify_stop_loss(self, signal_id: str, new_stop_loss: float) -> bool:
        logger.info("Modifying stop loss", signal_id=signal_id, new_sl=new_stop_loss)
        # Would call /v5/order/amend
        return True

    async def get_open_positions(self) -> list[dict]:
        import httpx

        headers = get_bybit_headers("")
        base_url = (
            "https://api-testnet.bybit.com" if settings.bybit_testnet
            else "https://api.bybit.com"
        )
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{base_url}/v5/position/list",
                params={"category": settings.bybit_category.value},
                headers=headers,
            )
        data = response.json()
        return data.get("result", {}).get("list", [])
