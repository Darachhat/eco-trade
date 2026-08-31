"""
app/strategy/entry.py — Entry zone calculation
app/strategy/stop_loss.py — Stop loss calculation
app/strategy/take_profit.py — Take profit calculation
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional

from app.core.constants import EntryType, SignalDirection


@dataclass
class EntryZone:
    price_low: float
    price_high: float
    entry_type: EntryType
    center: float = 0.0

    def __post_init__(self) -> None:
        self.center = (self.price_low + self.price_high) / 2


@dataclass
class StopLoss:
    price: float
    distance: float  # absolute distance from entry
    distance_pct: float


@dataclass
class TakeProfit:
    tp1: float
    tp2: Optional[float]
    tp3: Optional[float]
    risk_reward_tp1: float
    risk_reward_tp2: Optional[float]
    risk_reward_tp3: Optional[float]
    expected_value: float


def calculate_entry_zone(
    df: pd.DataFrame,
    direction: SignalDirection,
    current_price: float,
) -> EntryZone:
    """
    Calculate a realistic entry zone using:
    ATR, support/resistance, VWAP, market structure.
    """
    latest = df.iloc[-1] if not df.empty else pd.Series()

    atr = float(latest.get("atr_14", current_price * 0.005))

    # Entry zone centered on current price, ±0.25 ATR
    if direction == SignalDirection.LONG:
        # For longs: prefer buying slightly below current price on a pullback
        vwap = float(latest.get("vwap", current_price))
        center = min(current_price, vwap + atr * 0.1)
        entry_low = center - atr * 0.25
        entry_high = current_price + atr * 0.1  # don't chase more than 10% ATR above
        entry_type = EntryType.LIMIT if center < current_price else EntryType.MARKET
    else:
        # For shorts: prefer selling slightly above current price
        vwap = float(latest.get("vwap", current_price))
        center = max(current_price, vwap - atr * 0.1)
        entry_high = center + atr * 0.25
        entry_low = current_price - atr * 0.1
        entry_type = EntryType.LIMIT if center > current_price else EntryType.MARKET

    entry_low = max(entry_low, current_price * 0.999)
    entry_high = max(entry_high, entry_low + atr * 0.1)

    return EntryZone(
        price_low=round(entry_low, 4),
        price_high=round(entry_high, 4),
        entry_type=entry_type,
    )


def calculate_stop_loss(
    df: pd.DataFrame,
    direction: SignalDirection,
    entry_price: float,
) -> StopLoss:
    """
    Calculate stop loss using ATR + swing structure.
    SL represents a meaningful invalidation level.
    """
    latest = df.iloc[-1] if not df.empty else pd.Series()
    atr = float(latest.get("atr_14", entry_price * 0.005))

    # Use 1.5 ATR as default SL distance
    sl_distance = atr * 1.5

    # Check for swing levels
    if direction == SignalDirection.LONG:
        # SL below swing low or ATR-based
        swing_low = df["low"].rolling(10).min().iloc[-1] if "low" in df.columns else 0
        structure_sl = min(swing_low - atr * 0.2, entry_price - sl_distance)
        sl_price = max(structure_sl, entry_price - sl_distance * 1.5)
    else:
        swing_high = df["high"].rolling(10).max().iloc[-1] if "high" in df.columns else float("inf")
        structure_sl = max(swing_high + atr * 0.2, entry_price + sl_distance)
        sl_price = min(structure_sl, entry_price + sl_distance * 1.5)

    distance = abs(entry_price - sl_price)
    distance_pct = distance / entry_price

    return StopLoss(
        price=round(sl_price, 4),
        distance=round(distance, 4),
        distance_pct=round(distance_pct, 6),
    )


def calculate_take_profits(
    df: pd.DataFrame,
    direction: SignalDirection,
    entry_price: float,
    sl_distance: float,
) -> TakeProfit:
    """
    Calculate TP1, TP2, TP3 using ATR + resistance levels.
    Minimum 1:2 R:R on TP1.
    """
    latest = df.iloc[-1] if not df.empty else pd.Series()
    atr = float(latest.get("atr_14", entry_price * 0.005))

    # Default: 2R, 3.5R, 5R
    multipliers = [2.0, 3.5, 5.0]

    if direction == SignalDirection.LONG:
        tp1 = entry_price + sl_distance * multipliers[0]
        tp2 = entry_price + sl_distance * multipliers[1]
        tp3 = entry_price + sl_distance * multipliers[2]

        # Adjust for Bollinger band / Donchian resistance
        if "bb_upper" in latest and not pd.isna(latest["bb_upper"]):
            bb = float(latest["bb_upper"])
            if bb > entry_price and bb < tp2:
                tp1 = min(tp1, bb - atr * 0.1)
        if "don_upper" in latest and not pd.isna(latest["don_upper"]):
            don = float(latest["don_upper"])
            if don > entry_price and don < tp3:
                tp2 = min(tp2, don - atr * 0.1)
    else:
        tp1 = entry_price - sl_distance * multipliers[0]
        tp2 = entry_price - sl_distance * multipliers[1]
        tp3 = entry_price - sl_distance * multipliers[2]

        if "bb_lower" in latest and not pd.isna(latest["bb_lower"]):
            bb = float(latest["bb_lower"])
            if bb < entry_price and bb > tp2:
                tp1 = max(tp1, bb + atr * 0.1)

    rr1 = sl_distance * 2.0 / sl_distance if sl_distance else 2.0
    rr2 = sl_distance * 3.5 / sl_distance if sl_distance else 3.5
    rr3 = sl_distance * 5.0 / sl_distance if sl_distance else 5.0

    # Expected value: assuming 50% TP1 hit rate
    ev = 0.5 * (rr1) - 0.5 * 1.0  # EV in R units

    return TakeProfit(
        tp1=round(tp1, 4),
        tp2=round(tp2, 4),
        tp3=round(tp3, 4),
        risk_reward_tp1=round(rr1, 2),
        risk_reward_tp2=round(rr2, 2),
        risk_reward_tp3=round(rr3, 2),
        expected_value=round(ev, 4),
    )
