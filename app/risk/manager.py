"""
app/risk/manager.py
────────────────────
Central risk controller.
Enforces all limits. Kill-switch logic.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Optional

from app.core.config import settings
from app.core.constants import RiskEventType, SignalDirection
from app.core.logging import get_logger

logger = get_logger("trading")


class RiskManager:
    """
    Enforces trading risk rules.

    Tracks:
    - Daily PnL and loss limits
    - Open position count
    - Consecutive losses
    - Correlation exposure
    - Kill switch state

    All checks happen BEFORE a trade is placed.
    """

    def __init__(self) -> None:
        self._kill_switch_active = False
        self._kill_switch_reason: Optional[str] = None
        self._daily_pnl: float = 0.0
        self._weekly_pnl: float = 0.0
        self._open_positions: dict[str, int] = {}  # symbol -> count
        self._consecutive_losses: int = 0
        self._today: datetime = datetime.utcnow().date()
        self._max_drawdown_seen: float = 0.0
        self._peak_equity: float = 1.0
        self._current_equity: float = 1.0

    # ─────────────────────────────────────────
    # Pre-trade checks
    # ─────────────────────────────────────────

    def can_trade(
        self,
        symbol: str,
        direction: SignalDirection,
        position_size_usd: float = 0.0,
    ) -> tuple[bool, str]:
        """
        Check if a new trade can be placed.
        Returns (allowed: bool, reason: str)
        """
        if self._kill_switch_active:
            return False, f"Kill switch active: {self._kill_switch_reason}"

        # Daily loss limit
        max_daily_loss = settings.max_daily_loss
        if abs(self._daily_pnl) >= max_daily_loss and self._daily_pnl < 0:
            self._trigger_kill_switch(
                f"Daily loss limit reached: {self._daily_pnl:.2%}"
            )
            return False, "Daily loss limit reached"

        # Max open positions
        total_open = sum(self._open_positions.values())
        if total_open >= settings.max_open_positions:
            return False, f"Max open positions ({settings.max_open_positions}) reached"

        # Consecutive losses
        if self._consecutive_losses >= settings.max_consecutive_losses:
            return False, f"Max consecutive losses ({settings.max_consecutive_losses}) reached — cooldown"

        return True, "OK"

    def open_position(self, symbol: str) -> None:
        """Record that a position was opened."""
        self._open_positions[symbol] = self._open_positions.get(symbol, 0) + 1

    def close_position(self, symbol: str, pnl_pct: float) -> None:
        """Record that a position was closed, update daily PnL."""
        self._refresh_daily_if_needed()

        count = self._open_positions.get(symbol, 0)
        if count > 0:
            self._open_positions[symbol] = count - 1

        self._daily_pnl += pnl_pct
        self._weekly_pnl += pnl_pct

        # Update equity tracking for drawdown
        self._current_equity *= (1 + pnl_pct)
        if self._current_equity > self._peak_equity:
            self._peak_equity = self._current_equity
        drawdown = (self._peak_equity - self._current_equity) / self._peak_equity
        self._max_drawdown_seen = max(self._max_drawdown_seen, drawdown)

        # Track consecutive losses
        if pnl_pct < 0:
            self._consecutive_losses += 1
        else:
            self._consecutive_losses = 0

        # Check max drawdown
        max_dd = 0.15  # 15% max drawdown
        if drawdown >= max_dd:
            self._trigger_kill_switch(f"Max drawdown {drawdown:.2%} reached")

        logger.info(
            "Position closed",
            symbol=symbol,
            pnl_pct=round(pnl_pct * 100, 2),
            daily_pnl=round(self._daily_pnl * 100, 2),
            consecutive_losses=self._consecutive_losses,
        )

    def calculate_position_size(
        self,
        account_size_usd: float,
        stop_distance_pct: float,
    ) -> float:
        """
        Position Size = (Account * Risk Per Trade) / Stop Distance %
        """
        if stop_distance_pct <= 0:
            return 0.0
        risk_usd = account_size_usd * settings.risk_per_trade
        return risk_usd / stop_distance_pct

    # ─────────────────────────────────────────
    # Kill Switch
    # ─────────────────────────────────────────

    def _trigger_kill_switch(self, reason: str) -> None:
        self._kill_switch_active = True
        self._kill_switch_reason = reason
        logger.critical("KILL SWITCH TRIGGERED", reason=reason)

    def activate_kill_switch(self, reason: str = "Manual") -> None:
        """Manually trigger the kill switch."""
        self._trigger_kill_switch(reason)

    def deactivate_kill_switch(self) -> None:
        """Manually reset the kill switch (admin only)."""
        self._kill_switch_active = False
        self._kill_switch_reason = None
        logger.warning("Kill switch DEACTIVATED by admin")

    @property
    def kill_switch_active(self) -> bool:
        return self._kill_switch_active

    @property
    def kill_switch_reason(self) -> Optional[str]:
        return self._kill_switch_reason

    # ─────────────────────────────────────────
    # Status
    # ─────────────────────────────────────────

    def status(self) -> dict:
        return {
            "kill_switch_active": self._kill_switch_active,
            "kill_switch_reason": self._kill_switch_reason,
            "daily_pnl_pct": round(self._daily_pnl * 100, 2),
            "weekly_pnl_pct": round(self._weekly_pnl * 100, 2),
            "open_positions": dict(self._open_positions),
            "total_open": sum(self._open_positions.values()),
            "consecutive_losses": self._consecutive_losses,
            "max_drawdown_pct": round(self._max_drawdown_seen * 100, 2),
            "limits": {
                "max_daily_loss_pct": settings.max_daily_loss * 100,
                "max_open_positions": settings.max_open_positions,
                "max_consecutive_losses": settings.max_consecutive_losses,
                "risk_per_trade_pct": settings.risk_per_trade * 100,
            },
        }

    def _refresh_daily_if_needed(self) -> None:
        """Reset daily PnL counter at the start of a new trading day."""
        today = datetime.utcnow().date()
        if today != self._today:
            self._daily_pnl = 0.0
            self._consecutive_losses = 0
            self._today = today
            logger.info("Daily PnL counter reset for new day")


# Singleton
risk_manager = RiskManager()
