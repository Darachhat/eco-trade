"""
tests/conftest.py
──────────────────
Pytest configuration and shared fixtures for unit and integration tests.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import pytest

from app.exchange.bybit.models import Candle, OrderBook, OrderBookLevel, Ticker


@pytest.fixture
def synthetic_candles_df() -> pd.DataFrame:
    """Generate 500 bars of realistic synthetic OHLCV time-series data."""
    np.random.seed(42)
    n = 500
    start_time = datetime(2026, 1, 1, 0, 0)
    times = [start_time + timedelta(minutes=15 * i) for i in range(n)]

    # Geometric Brownian Motion for realistic price series
    returns = np.random.normal(loc=0.0002, scale=0.008, size=n)
    price = 50000.0 * np.exp(np.cumsum(returns))

    high = price * (1 + np.abs(np.random.normal(0, 0.003, n)))
    low = price * (1 - np.abs(np.random.normal(0, 0.003, n)))
    open_p = low + (high - low) * np.random.uniform(0.1, 0.9, n)
    close_p = low + (high - low) * np.random.uniform(0.1, 0.9, n)
    volume = np.random.uniform(10.0, 500.0, n)

    df = pd.DataFrame({
        "open_time": times,
        "close_time": [t + timedelta(minutes=15) for t in times],
        "open": open_p,
        "high": high,
        "low": low,
        "close": close_p,
        "volume": volume,
        "turnover": volume * close_p,
        "funding_rate": np.random.normal(0.0001, 0.00005, n),
        "open_interest": 1000000.0 + np.cumsum(np.random.normal(100, 1000, n)),
    })
    return df


@pytest.fixture
def sample_candle() -> Candle:
    return Candle(
        symbol="BTCUSDT",
        timeframe="15",
        open_time=datetime(2026, 1, 1, 12, 0),
        close_time=datetime(2026, 1, 1, 12, 15),
        open=50000.0,
        high=50500.0,
        low=49800.0,
        close=50200.0,
        volume=125.5,
        turnover=6275000.0,
        is_closed=True,
    )


@pytest.fixture
def sample_orderbook() -> OrderBook:
    return OrderBook(
        symbol="BTCUSDT",
        timestamp=datetime.utcnow(),
        bids=[
            OrderBookLevel(price=50000.0, qty=2.5),
            OrderBookLevel(price=49990.0, qty=5.0),
            OrderBookLevel(price=49980.0, qty=10.0),
        ],
        asks=[
            OrderBookLevel(price=50010.0, qty=1.5),
            OrderBookLevel(price=50020.0, qty=3.0),
            OrderBookLevel(price=50030.0, qty=8.0),
        ],
    )
