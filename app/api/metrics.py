"""
app/api/metrics.py
──────────────────
Prometheus telemetry metrics exporter.
Exposes /metrics endpoint for Grafana dashboards and Prometheus scraping.
"""

from __future__ import annotations

from fastapi import APIRouter, Response

from app.risk.manager import risk_manager

router_metrics = APIRouter(tags=["Metrics"])


@router_metrics.get("/metrics")
async def prometheus_metrics():
    """Export platform metrics in standard Prometheus exposition format."""
    status = risk_manager.status()

    kill_active = 1 if status.get("kill_switch_active") else 0
    daily_pnl = status.get("daily_pnl_pct", 0.0)
    weekly_pnl = status.get("weekly_pnl_pct", 0.0)
    max_dd = status.get("max_drawdown_pct", 0.0)
    open_pos = status.get("total_open", 0)
    consec_losses = status.get("consecutive_losses", 0)

    lines = [
        "# HELP ecotrade_kill_switch_active Status of trading circuit breaker (1=Halted, 0=Active)",
        "# TYPE ecotrade_kill_switch_active gauge",
        f"ecotrade_kill_switch_active {kill_active}",
        "",
        "# HELP ecotrade_daily_pnl_percent Current daily PnL percentage",
        "# TYPE ecotrade_daily_pnl_percent gauge",
        f"ecotrade_daily_pnl_percent {daily_pnl}",
        "",
        "# HELP ecotrade_weekly_pnl_percent Current weekly PnL percentage",
        "# TYPE ecotrade_weekly_pnl_percent gauge",
        f"ecotrade_weekly_pnl_percent {weekly_pnl}",
        "",
        "# HELP ecotrade_max_drawdown_percent Maximum drawdown percentage",
        "# TYPE ecotrade_max_drawdown_percent gauge",
        f"ecotrade_max_drawdown_percent {max_dd}",
        "",
        "# HELP ecotrade_open_positions Number of currently open positions",
        "# TYPE ecotrade_open_positions gauge",
        f"ecotrade_open_positions {open_pos}",
        "",
        "# HELP ecotrade_consecutive_losses Number of consecutive loss trades",
        "# TYPE ecotrade_consecutive_losses gauge",
        f"ecotrade_consecutive_losses {consec_losses}",
    ]

    payload = "\n".join(lines) + "\n"
    return Response(content=payload, media_type="text/plain; version=0.0.4")
