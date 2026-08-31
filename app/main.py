"""
app/main.py
────────────
FastAPI application factory, lifespan management, and WebSocket streaming.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.metrics import router_metrics
from app.api.routers import (
    router_backtest,
    router_health,
    router_journal,
    router_market,
    router_performance,
    router_risk,
    router_signals,
)
from app.api.ws import manager as ws_manager, router_ws
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown events."""
    logger.info(
        "EcoTrade starting up",
        mode=settings.trading_mode.value,
        symbols=settings.symbols_list,
        timeframes=settings.timeframes_list,
        testnet=settings.bybit_testnet,
    )

    # Initialize database tables on startup (if not already managed via Alembic)
    try:
        from app.database.session import async_engine
        from app.database import models
        async with async_engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.create_all)
        logger.info("Database tables verified")
    except Exception as e:
        logger.warning("Database init check (handled by Alembic in prod)", error=str(e))

    # Start WebSocket feed for Bybit market data (non-blocking background task)
    ws_task = None
    if settings.symbols_list:
        from app.exchange.bybit.client import bybit_client
        from app.execution.paper import paper_engine

        async def on_ws_event(event_type: str, data: object) -> None:
            """Route WebSocket events to paper engine and broadcast to UI clients."""
            if event_type == "ticker":
                ticker = data
                # Update paper engine mark price
                await paper_engine.update_mark_price(ticker.symbol, ticker.last_price)
                # Broadcast live ticker to WebSocket clients
                await ws_manager.broadcast_market(ticker.symbol, {
                    "type": "ticker",
                    "symbol": ticker.symbol,
                    "price": ticker.last_price,
                    "timestamp": ticker.timestamp.isoformat(),
                })
            elif event_type == "orderbook":
                ob = data
                await ws_manager.broadcast_market(ob.symbol, {
                    "type": "orderbook",
                    "symbol": ob.symbol,
                    "best_bid": ob.best_bid,
                    "best_ask": ob.best_ask,
                    "spread": ob.spread,
                    "imbalance": ob.imbalance,
                })

        client_ws = bybit_client.create_ws_manager(
            symbols=settings.symbols_list,
            timeframes=settings.timeframes_list,
            event_handler=on_ws_event,
        )
        ws_task = asyncio.create_task(client_ws.start())
        logger.info("WebSocket feed started", symbols=settings.symbols_list)

    logger.info("EcoTrade startup complete")

    yield  # Application running

    # Shutdown
    logger.info("EcoTrade shutting down")
    if ws_task:
        ws_task.cancel()
        try:
            await ws_task
        except asyncio.CancelledError:
            pass

    try:
        from app.database.session import async_engine
        await async_engine.dispose()
    except Exception:
        pass

    logger.info("EcoTrade shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="EcoTrade — AI Crypto Trading Intelligence",
        description="Production AI-powered probabilistic crypto trading signal system using Bybit",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Security & CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Adjust for specific frontend origins in prod
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # REST Routers
    app.include_router(router_health)
    app.include_router(router_market)
    app.include_router(router_signals)
    app.include_router(router_performance)
    app.include_router(router_risk)
    app.include_router(router_journal)
    app.include_router(router_backtest)
    app.include_router(router_metrics)

    # WebSocket Routers
    app.include_router(router_ws)

    logger.info("FastAPI application initialized with all REST and WebSocket routes")
    return app


app = create_app()
