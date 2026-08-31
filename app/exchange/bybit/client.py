"""
app/exchange/bybit/client.py
─────────────────────────────
Unified Bybit client facade — wires REST + WebSocket into a single interface.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Coroutine, Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.exchange.bybit.models import (
    Candle,
    FundingRate,
    OpenInterest,
    OrderBook,
    Ticker,
)
from app.exchange.bybit.rest import BybitRESTClient
from app.exchange.bybit.websocket import BybitWebSocketManager

logger = get_logger("market")

EventHandler = Callable[[str, Any], Coroutine[Any, Any, None]]


class BybitClient:
    """
    Facade combining Bybit REST and WebSocket clients.

    The exchange layer is isolated here so:
    - The rest of the system never imports Bybit-specific code directly.
    - A new exchange can be plugged in by replacing this class.
    """

    def __init__(self) -> None:
        self._rest = BybitRESTClient()
        self._ws_manager: Optional[BybitWebSocketManager] = None

    # ─────────────────────────────────────────
    # Historical Data (REST)
    # ─────────────────────────────────────────

    async def get_historical_candles(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: Optional[datetime] = None,
    ) -> list[Candle]:
        async with self._rest as rest:
            return await rest.download_historical_candles(symbol, timeframe, start, end)

    async def get_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 200,
        start_ms: Optional[int] = None,
        end_ms: Optional[int] = None,
    ) -> list[Candle]:
        async with self._rest as rest:
            return await rest.get_klines(symbol, timeframe, start_ms, end_ms, limit)

    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        async with self._rest as rest:
            return await rest.get_ticker(symbol)

    async def get_orderbook(self, symbol: str, depth: int = 25) -> Optional[OrderBook]:
        async with self._rest as rest:
            return await rest.get_orderbook(symbol, depth)

    async def get_funding_rate(self, symbol: str) -> Optional[FundingRate]:
        async with self._rest as rest:
            return await rest.get_funding_rate(symbol)

    async def get_open_interest(self, symbol: str) -> Optional[OpenInterest]:
        async with self._rest as rest:
            return await rest.get_open_interest(symbol)

    async def get_server_time(self) -> int:
        async with self._rest as rest:
            return await rest.get_server_time()

    # ─────────────────────────────────────────
    # Real-Time Data (WebSocket)
    # ─────────────────────────────────────────

    def create_ws_manager(
        self,
        symbols: Optional[list[str]] = None,
        timeframes: Optional[list[str]] = None,
        event_handler: Optional[EventHandler] = None,
    ) -> BybitWebSocketManager:
        """Create a WebSocket manager for the given symbols and timeframes."""
        syms = symbols or settings.symbols_list
        tfs = timeframes or ["1", "5", "15", "60", "240"]
        self._ws_manager = BybitWebSocketManager(
            symbols=syms,
            timeframes=tfs,
            event_handler=event_handler,
        )
        return self._ws_manager

    @property
    def ws_manager(self) -> Optional[BybitWebSocketManager]:
        return self._ws_manager

    @property
    def is_testnet(self) -> bool:
        return settings.bybit_testnet


# Singleton for use across the application
bybit_client = BybitClient()
