"""
app/api/ws.py
─────────────
WebSocket endpoints for real-time streaming to dashboards and UI clients.

Endpoints:
- /ws/market/{symbol} — Real-time ticker, candle, orderbook feed
- /ws/signals         — Broadcasts live generated trade signals
- /ws/models          — Broadcasts live model consensus & predictions
- /ws/system          — System health, risk events, and kill switch status
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.logging import get_logger

logger = get_logger("api")

router_ws = APIRouter(prefix="/ws", tags=["WebSockets"])


class ConnectionManager:
    """Manages active WebSocket connections by channel."""

    def __init__(self) -> None:
        self.active_connections: dict[str, list[WebSocket]] = {
            "signals": [],
            "models": [],
            "system": [],
        }
        self.market_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str) -> None:
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = []
        self.active_connections[channel].append(websocket)
        logger.info(f"WebSocket client connected to channel: {channel}")

    async def connect_market(self, websocket: WebSocket, symbol: str) -> None:
        await websocket.accept()
        sym = symbol.upper()
        if sym not in self.market_connections:
            self.market_connections[sym] = []
        self.market_connections[sym].append(websocket)
        logger.info(f"WebSocket client connected to market: {sym}")

    def disconnect(self, websocket: WebSocket, channel: str) -> None:
        if channel in self.active_connections and websocket in self.active_connections[channel]:
            self.active_connections[channel].remove(websocket)
            logger.info(f"WebSocket client disconnected from channel: {channel}")

    def disconnect_market(self, websocket: WebSocket, symbol: str) -> None:
        sym = symbol.upper()
        if sym in self.market_connections and websocket in self.market_connections[sym]:
            self.market_connections[sym].remove(websocket)
            logger.info(f"WebSocket client disconnected from market: {sym}")

    async def broadcast(self, channel: str, message: dict) -> None:
        """Broadcast payload to all clients in a general channel."""
        connections = self.active_connections.get(channel, [])
        dead_conns = []
        for connection in connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                dead_conns.append(connection)

        for dead in dead_conns:
            self.disconnect(dead, channel)

    async def broadcast_market(self, symbol: str, message: dict) -> None:
        """Broadcast payload to all clients subscribed to a specific market symbol."""
        sym = symbol.upper()
        connections = self.market_connections.get(sym, [])
        dead_conns = []
        for connection in connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                dead_conns.append(connection)

        for dead in dead_conns:
            self.disconnect_market(dead, sym)


manager = ConnectionManager()


@router_ws.websocket("/market/{symbol}")
async def ws_market(websocket: WebSocket, symbol: str):
    """Live market data stream for a specific pair."""
    await manager.connect_market(websocket, symbol)
    try:
        while True:
            # Keep connection open and accept client messages/pings
            data = await websocket.receive_text()
            # Echo heartbeat if client pings
            if data == "ping":
                await websocket.send_text(json.dumps({"op": "pong"}))
    except WebSocketDisconnect:
        manager.disconnect_market(websocket, symbol)


@router_ws.websocket("/signals")
async def ws_signals(websocket: WebSocket):
    """Live AI trade signal stream."""
    await manager.connect(websocket, "signals")
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"op": "pong"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket, "signals")


@router_ws.websocket("/models")
async def ws_models(websocket: WebSocket):
    """Live model predictions and consensus breakdown stream."""
    await manager.connect(websocket, "models")
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"op": "pong"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket, "models")


@router_ws.websocket("/system")
async def ws_system(websocket: WebSocket):
    """Live system telemetry and risk events stream."""
    await manager.connect(websocket, "system")
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"op": "pong"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket, "system")
