"""
app/api/routers/mt5.py
──────────────────────
FastAPI routes for MetaTrader 5 (Exness Demo & Real) operations & Autonomous Scalper Engine.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.mt5_service import mt5_service
from app.services.mt5_scalper import mt5_scalper, ScalperConfig

router_mt5 = APIRouter(prefix="/api/mt5", tags=["MetaTrader 5"])


class MT5ConnectRequest(BaseModel):
    login: int = Field(default=463894594, description="Exness MT5 account number")
    password: str = Field(default="cHhat#2023", description="Exness MT5 trading password")
    server: str = Field(default="Exness-MT5Trial17", description="Exness MT5 server name")
    path: Optional[str] = Field(default=None, description="Custom MT5 terminal path")


class MT5OrderRequest(BaseModel):
    symbol: str = Field(description="Symbol name e.g. XAUUSDT or BTCUSDT")
    side: str = Field(description="BUY, SELL, LONG, or SHORT")
    volume: float = Field(default=0.01, description="Lot size e.g. 0.01 or 0.1")
    sl: Optional[float] = Field(default=None, description="Stop Loss price")
    tp: Optional[float] = Field(default=None, description="Take Profit price")
    comment: Optional[str] = Field(default="EcoTrade AI Follower", description="Order comment")


class MT5CloseRequest(BaseModel):
    ticket: int = Field(description="MT5 position ticket ID to close")


# ─── Standard MT5 Gateway Routes ──────────────────────────────────────────

@router_mt5.post("/connect")
async def connect_mt5(payload: MT5ConnectRequest):
    """Authenticate and connect to Exness MT5 terminal."""
    res = mt5_service.initialize_and_login(
        login=payload.login,
        password=payload.password,
        server=payload.server,
        path=payload.path,
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Connection failed"))
    return res


@router_mt5.get("/status")
async def get_mt5_status():
    """Retrieve active MT5 account balance, equity, and connectivity."""
    return mt5_service.get_account_status()


@router_mt5.get("/positions")
async def get_mt5_positions():
    """Retrieve open MT5 positions."""
    return {"positions": mt5_service.get_open_positions()}


@router_mt5.post("/order")
async def send_mt5_order(payload: MT5OrderRequest):
    """Execute a 1-click trade to Exness MT5 with SL and TP."""
    res = mt5_service.execute_order(
        symbol=payload.symbol,
        side=payload.side,
        volume=payload.volume,
        sl=payload.sl,
        tp=payload.tp,
        comment=payload.comment or "EcoTrade AI Follower",
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Order execution failed"))
    return res


@router_mt5.post("/close")
async def close_mt5_position(payload: MT5CloseRequest):
    """Close an open position on MT5 by ticket ID."""
    res = mt5_service.close_position(ticket=payload.ticket)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Position close failed"))
    return res


# ─── Autonomous Scalper Engine Routes ─────────────────────────────────────

@router_mt5.get("/scalper/status")
async def get_scalper_status():
    """Retrieve real-time telemetry, filter states, signal, and active trailing trades."""
    return {
        "telemetry": mt5_scalper.telemetry.model_dump(),
        "config": mt5_scalper.config.model_dump(),
    }


@router_mt5.post("/scalper/start")
async def start_scalper():
    """Start the autonomous MT5 Scalper engine."""
    res = mt5_scalper.start()
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to start scalper"))
    return res


@router_mt5.post("/scalper/stop")
async def stop_scalper():
    """Stop the autonomous MT5 Scalper engine."""
    return mt5_scalper.stop()


@router_mt5.post("/scalper/config")
async def update_scalper_config(payload: Dict[str, Any]):
    """Update live scalper parameters dynamically."""
    updated = mt5_scalper.update_config(payload)
    return {"success": True, "config": updated.model_dump()}
