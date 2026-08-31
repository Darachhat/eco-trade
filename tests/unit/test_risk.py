"""
tests/unit/test_risk.py
────────────────────────
Unit tests for Risk Management, limits enforcement, kill switch, and position sizing.
"""

from __future__ import annotations

import pytest

from app.core.constants import SignalDirection
from app.risk.manager import RiskManager


def test_kill_switch_activation():
    risk = RiskManager()
    allowed, msg = risk.can_trade("BTCUSDT", SignalDirection.LONG)
    assert allowed

    # Activate kill switch
    risk.activate_kill_switch("Manual Test")
    assert risk.kill_switch_active
    allowed, msg = risk.can_trade("BTCUSDT", SignalDirection.LONG)
    assert not allowed
    assert "Kill switch active" in msg

    # Reset
    risk.deactivate_kill_switch()
    assert not risk.kill_switch_active
    allowed, _ = risk.can_trade("BTCUSDT", SignalDirection.LONG)
    assert allowed


def test_daily_loss_limit():
    risk = RiskManager()
    # Simulate a series of losing trades exceeding daily limit (3%)
    risk.close_position("BTCUSDT", -0.015)
    risk.close_position("ETHUSDT", -0.020)  # Total -3.5%

    allowed, msg = risk.can_trade("SOLUSDT", SignalDirection.LONG)
    assert not allowed
    assert risk.kill_switch_active


def test_position_sizing_formula():
    risk = RiskManager()
    account_size = 10000.0  # $10,000
    stop_distance_pct = 0.02  # 2% stop distance
    # With 1% risk per trade = $100 risk
    # Position size should be $100 / 0.02 = $5,000
    size = risk.calculate_position_size(account_size, stop_distance_pct)
    assert size == 5000.0
