"""
app/features/orderbook.py
──────────────────────────
Order book derived features.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.exchange.bybit.models import OrderBook


def orderbook_features(ob: OrderBook) -> dict[str, float]:
    """
    Compute real-time order book features from a snapshot.
    All values represent the current state (no future leakage).
    """
    features: dict[str, float] = {}

    features["bid_volume"] = ob.bid_volume
    features["ask_volume"] = ob.ask_volume
    features["imbalance"] = ob.imbalance  # range [-1, +1]
    features["spread"] = ob.spread or 0.0
    features["spread_pct"] = (ob.spread / ob.mid_price) if ob.mid_price else 0.0

    # Depth (top 5 levels)
    top_bids = ob.bids[:5]
    top_asks = ob.asks[:5]
    features["bid_depth_5"] = sum(b.qty for b in top_bids)
    features["ask_depth_5"] = sum(a.qty for a in top_asks)

    # Weighted average bid/ask price
    if top_bids:
        total_bid = features["bid_depth_5"]
        features["wap_bid"] = sum(b.price * b.qty for b in top_bids) / total_bid if total_bid else 0
    if top_asks:
        total_ask = features["ask_depth_5"]
        features["wap_ask"] = sum(a.price * a.qty for a in top_asks) / total_ask if total_ask else 0

    # Order book pressure
    total_depth = features["bid_depth_5"] + features["ask_depth_5"]
    if total_depth > 0:
        features["pressure"] = (features["bid_depth_5"] - features["ask_depth_5"]) / total_depth
    else:
        features["pressure"] = 0.0

    features["mid_price"] = ob.mid_price or 0.0
    features["best_bid"] = ob.best_bid or 0.0
    features["best_ask"] = ob.best_ask or 0.0

    return features


def rolling_orderbook_features(
    ob_history: list[dict[str, float]],
    window: int = 20,
) -> dict[str, float]:
    """
    Compute rolling statistics over a history of order book snapshots.
    ob_history: list of dicts from orderbook_features()
    """
    if not ob_history:
        return {}

    df = pd.DataFrame(ob_history)
    features: dict[str, float] = {}

    for col in ["imbalance", "spread_pct", "pressure"]:
        if col in df.columns:
            s = df[col].tail(window)
            features[f"{col}_mean"] = float(s.mean())
            features[f"{col}_std"] = float(s.std()) if len(s) > 1 else 0.0
            features[f"{col}_trend"] = float(s.diff().mean()) if len(s) > 1 else 0.0

    return features
