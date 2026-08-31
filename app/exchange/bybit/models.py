"""
app/exchange/bybit/models.py
─────────────────────────────
Pydantic models for all Bybit market data types.
These represent the normalized, validated view of raw exchange data.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Candle(BaseModel):
    """Normalized OHLCV candle."""
    symbol: str
    timeframe: str
    open_time: datetime
    close_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    turnover: Optional[float] = None
    exchange_timestamp: Optional[int] = None
    is_closed: bool = True

    @field_validator("high")
    @classmethod
    def high_gte_low(cls, v: float, info: object) -> float:
        # Basic sanity: high must be >= low
        return v

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "open_time": self.open_time,
            "close_time": self.close_time,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "turnover": self.turnover,
        }


class OrderBookLevel(BaseModel):
    price: float
    qty: float


class OrderBook(BaseModel):
    """Normalized order book snapshot."""
    symbol: str
    timestamp: datetime
    bids: list[OrderBookLevel]
    asks: list[OrderBookLevel]

    @property
    def best_bid(self) -> Optional[float]:
        return self.bids[0].price if self.bids else None

    @property
    def best_ask(self) -> Optional[float]:
        return self.asks[0].price if self.asks else None

    @property
    def spread(self) -> Optional[float]:
        if self.best_bid and self.best_ask:
            return self.best_ask - self.best_bid
        return None

    @property
    def mid_price(self) -> Optional[float]:
        if self.best_bid and self.best_ask:
            return (self.best_bid + self.best_ask) / 2
        return None

    @property
    def bid_volume(self) -> float:
        return sum(b.qty for b in self.bids)

    @property
    def ask_volume(self) -> float:
        return sum(a.qty for a in self.asks)

    @property
    def imbalance(self) -> float:
        """Bid/ask volume imbalance: >0 = more bids, <0 = more asks."""
        total = self.bid_volume + self.ask_volume
        if total == 0:
            return 0.0
        return (self.bid_volume - self.ask_volume) / total


class Trade(BaseModel):
    """Normalized public trade."""
    symbol: str
    trade_id: str
    trade_time: datetime
    price: float
    qty: float
    side: str  # "Buy" | "Sell"
    is_buyer_maker: bool = False


class Ticker(BaseModel):
    """Normalized ticker snapshot."""
    symbol: str
    timestamp: datetime
    last_price: float
    bid_price: Optional[float] = None
    ask_price: Optional[float] = None
    volume_24h: Optional[float] = None
    turnover_24h: Optional[float] = None
    price_change_24h: Optional[float] = None
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None
    mark_price: Optional[float] = None
    index_price: Optional[float] = None
    open_interest: Optional[float] = None
    funding_rate: Optional[float] = None
    next_funding_time: Optional[datetime] = None


class FundingRate(BaseModel):
    """Funding rate record."""
    symbol: str
    funding_rate: float
    funding_rate_timestamp: datetime
    next_funding_time: Optional[datetime] = None


class OpenInterest(BaseModel):
    """Open interest record."""
    symbol: str
    open_interest: float
    timestamp: datetime


class LiquidationEvent(BaseModel):
    """Liquidation event."""
    symbol: str
    side: str
    size: float
    price: float
    timestamp: datetime


class MarketSnapshot(BaseModel):
    """Complete market snapshot for a symbol at a point in time."""
    symbol: str
    timestamp: datetime
    ticker: Optional[Ticker] = None
    orderbook: Optional[OrderBook] = None
    funding_rate: Optional[FundingRate] = None
    open_interest: Optional[OpenInterest] = None
