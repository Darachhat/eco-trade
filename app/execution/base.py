"""
app/execution/base.py — Abstract ExecutionEngine
app/execution/paper.py — Paper trading execution
app/execution/bybit_live.py — Live Bybit execution
"""

from __future__ import annotations

import abc
from datetime import datetime
from typing import Optional


class ExecutionEngine(abc.ABC):
    """
    Abstract execution engine interface.

    Both paper and live engines implement the same methods.
    Strategy code never needs to know which engine is active.
    """

    @abc.abstractmethod
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
        """Open a new position."""
        ...

    @abc.abstractmethod
    async def close_position(
        self,
        signal_id: str,
        exit_price: float,
        reason: str = "MANUAL",
    ) -> dict:
        """Close an existing position."""
        ...

    @abc.abstractmethod
    async def modify_stop_loss(
        self,
        signal_id: str,
        new_stop_loss: float,
    ) -> bool:
        """Modify the stop loss of an open position."""
        ...

    @abc.abstractmethod
    async def get_open_positions(self) -> list[dict]:
        """Return all open positions."""
        ...
