"""
app/api/routers/__init__.py
"""
from app.api.routers.core import (
    router_backtest,
    router_health,
    router_journal,
    router_market,
    router_monitoring,
    router_performance,
    router_risk,
    router_signals,
)
from app.api.routers.mt5 import router_mt5

__all__ = [
    "router_backtest",
    "router_health",
    "router_journal",
    "router_market",
    "router_monitoring",
    "router_performance",
    "router_risk",
    "router_signals",
    "router_mt5",
]
