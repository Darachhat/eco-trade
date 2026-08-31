"""
app/exchange/bybit/websocket.py
────────────────────────────────
Robust Bybit WebSocket manager.

Features:
- Connect / authenticate / subscribe / receive
- Automatic reconnect with exponential backoff
- Heartbeat (ping every 20 seconds)
- Resubscribe on reconnect
- Publishes events to Redis Streams
- Logs all connection state transitions
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime
from typing import Any, Callable, Coroutine, Optional

import websockets
from websockets.client import WebSocketClientProtocol
from websockets.exceptions import ConnectionClosed, WebSocketException

from app.core.config import settings
from app.core.constants import BYBIT_WS_MAINNET, BYBIT_WS_TESTNET
from app.core.logging import get_logger
from app.exchange.bybit.parser import (
    parse_ws_kline,
    parse_ws_orderbook,
    parse_ws_ticker,
    parse_ws_trade,
)

logger = get_logger("market")

# Handler type: async callable receiving the parsed event
EventHandler = Callable[[str, Any], Coroutine[Any, Any, None]]


class BybitWebSocketManager:
    """
    Manages a persistent WebSocket connection to Bybit.

    Usage:
        manager = BybitWebSocketManager(symbols=["BTCUSDT"], timeframes=["1", "5", "15"])
        await manager.start(event_handler)
    """

    PING_INTERVAL = 20  # seconds
    MAX_RECONNECT_DELAY = 60  # seconds
    INITIAL_RECONNECT_DELAY = 1  # seconds

    def __init__(
        self,
        symbols: list[str],
        timeframes: list[str],
        event_handler: Optional[EventHandler] = None,
    ) -> None:
        self.symbols = symbols
        self.timeframes = timeframes
        self.event_handler = event_handler
        self._ws: Optional[WebSocketClientProtocol] = None
        self._running = False
        self._reconnect_delay = self.INITIAL_RECONNECT_DELAY
        self._connection_state = "DISCONNECTED"
        self._last_ping = 0.0
        self._subscriptions: list[str] = self._build_subscriptions()

        base_url = BYBIT_WS_TESTNET if settings.bybit_testnet else BYBIT_WS_MAINNET
        self.ws_url = f"{base_url}/{settings.bybit_category.value}"

    # ─────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────

    async def start(self) -> None:
        """Start the WebSocket manager. Runs until stop() is called."""
        self._running = True
        logger.info(
            "WebSocket manager starting",
            url=self.ws_url,
            symbols=self.symbols,
            timeframes=self.timeframes,
        )
        while self._running:
            try:
                await self._connect_and_run()
            except Exception as e:
                if not self._running:
                    break
                logger.error(
                    "WebSocket connection failed, reconnecting",
                    error=str(e),
                    delay=self._reconnect_delay,
                )
                self._set_state("RECONNECTING")
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(
                    self._reconnect_delay * 2, self.MAX_RECONNECT_DELAY
                )

    async def stop(self) -> None:
        """Gracefully stop the WebSocket manager."""
        self._running = False
        if self._ws:
            await self._ws.close()
        self._set_state("DISCONNECTED")
        logger.info("WebSocket manager stopped")

    # ─────────────────────────────────────────
    # Connection lifecycle
    # ─────────────────────────────────────────

    async def _connect_and_run(self) -> None:
        self._set_state("CONNECTING")
        async with websockets.connect(
            self.ws_url,
            ping_interval=None,  # We manage ping manually
            ping_timeout=30,
            close_timeout=10,
            max_size=10 * 1024 * 1024,  # 10 MB
        ) as ws:
            self._ws = ws
            self._reconnect_delay = self.INITIAL_RECONNECT_DELAY
            self._set_state("CONNECTED")
            logger.info("WebSocket connected", url=self.ws_url)

            await self._subscribe()
            await asyncio.gather(
                self._receive_loop(),
                self._heartbeat_loop(),
            )

    async def _subscribe(self) -> None:
        """Subscribe to all configured topics."""
        if not self._ws:
            return
        sub_msg = {
            "op": "subscribe",
            "args": self._subscriptions,
        }
        await self._ws.send(json.dumps(sub_msg))
        self._set_state("SUBSCRIBED")
        logger.info("WebSocket subscribed", topics=self._subscriptions)

    def _is_ws_open(self) -> bool:
        """Check if WebSocket connection is active across websockets v10-v17+."""
        if not self._ws:
            return False
        if hasattr(self._ws, "state"):
            from websockets.protocol import State
            return self._ws.state == State.OPEN
        if hasattr(self._ws, "closed"):
            return not self._ws.closed
        return self._ws.close_code is None

    async def _receive_loop(self) -> None:
        """Main receive loop — parses and dispatches all incoming messages."""
        if not self._ws:
            return
        try:
            async for raw_msg in self._ws:  # type: ignore[union-attr]
                try:
                    msg = json.loads(raw_msg)
                    await self._handle_message(msg)
                except json.JSONDecodeError:
                    logger.warning("Received non-JSON message", raw=raw_msg[:200])
                except Exception as e:
                    logger.error("Error handling WS message", error=str(e))
        except ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error("WebSocket receive loop encountered error", error=str(e))
            raise

    async def _heartbeat_loop(self) -> None:
        """Send periodic ping to keep connection alive."""
        while self._running and self._ws:
            await asyncio.sleep(self.PING_INTERVAL)
            if not self._is_ws_open():
                break
            try:
                await self._ws.send(json.dumps({"op": "ping"}))
                self._last_ping = time.time()
                logger.debug("WebSocket ping sent")
            except Exception as e:
                logger.warning("WebSocket ping failed", error=str(e))
                break

    # ─────────────────────────────────────────
    # Message handling
    # ─────────────────────────────────────────

    async def _handle_message(self, msg: dict) -> None:
        """Route incoming WebSocket message to appropriate parser."""
        op = msg.get("op")

        # Control messages
        if op == "pong":
            logger.debug("WebSocket pong received")
            return
        if op in ("subscribe", "auth"):
            success = msg.get("success", True)
            if not success:
                logger.error("WebSocket operation failed", op=op, msg=msg)
            return

        topic: str = msg.get("topic", "")
        if not topic:
            return

        event_type = topic.split(".")[0]
        parsed: Any = None

        if event_type == "kline":
            candles = parse_ws_kline(msg)
            for candle in candles:
                await self._dispatch("candle", candle)
            return

        elif event_type == "orderbook":
            parsed = parse_ws_orderbook(msg)
            if parsed:
                await self._dispatch("orderbook", parsed)
            return

        elif event_type == "publicTrade":
            trades = parse_ws_trade(msg)
            for trade in trades:
                await self._dispatch("trade", trade)
            return

        elif event_type == "tickers":
            parsed = parse_ws_ticker(msg)
            if parsed:
                await self._dispatch("ticker", parsed)
            return

        elif event_type == "liquidation":
            from app.exchange.bybit.parser import parse_ws_liquidation
            parsed = parse_ws_liquidation(msg)
            if parsed:
                await self._dispatch("liquidation", parsed)
            return

    async def _dispatch(self, event_type: str, data: Any) -> None:
        """Call the event handler if registered."""
        if self.event_handler:
            try:
                await self.event_handler(event_type, data)
            except Exception as e:
                logger.error(
                    "Event handler raised exception",
                    event_type=event_type,
                    error=str(e),
                )

    # ─────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────

    def _build_subscriptions(self) -> list[str]:
        """Build Bybit topic subscription strings."""
        topics: list[str] = []
        for symbol in self.symbols:
            for tf in self.timeframes:
                topics.append(f"kline.{tf}.{symbol}")
            topics.append(f"orderbook.50.{symbol}")
            topics.append(f"publicTrade.{symbol}")
            topics.append(f"tickers.{symbol}")
        return topics

    def _set_state(self, state: str) -> None:
        old = self._connection_state
        self._connection_state = state
        if old != state:
            logger.info("WebSocket state change", old=old, new=state)

    @property
    def is_connected(self) -> bool:
        return self._connection_state in ("CONNECTED", "SUBSCRIBED")

    @property
    def connection_state(self) -> str:
        return self._connection_state
