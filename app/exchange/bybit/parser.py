"""
app/exchange/bybit/parser.py
─────────────────────────────
Parses raw Bybit REST and WebSocket responses into normalized models.
Handles both v5 REST API and v5 WebSocket message formats.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from app.core.logging import get_logger
from app.exchange.bybit.models import (
    Candle,
    FundingRate,
    LiquidationEvent,
    OpenInterest,
    OrderBook,
    OrderBookLevel,
    Ticker,
    Trade,
)

logger = get_logger("market")


def _ms_to_dt(ms: int | str) -> datetime:
    """Convert millisecond timestamp to UTC datetime."""
    return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).replace(tzinfo=None)


def _s_to_dt(s: int | str) -> datetime:
    """Convert second timestamp to UTC datetime."""
    return datetime.fromtimestamp(int(s), tz=timezone.utc).replace(tzinfo=None)


# ─────────────────────────────────────────────
# REST Parsers
# ─────────────────────────────────────────────

def parse_rest_candle(raw: list, symbol: str, timeframe: str) -> Optional[Candle]:
    """
    Parse a single kline from Bybit REST response.
    REST v5 kline format: [startTime, openPrice, highPrice, lowPrice, closePrice, volume, turnover]
    """
    try:
        start_ms = int(raw[0])
        # Bybit timeframe in minutes for close_time calculation
        _tf_minutes = {
            "1": 1, "3": 3, "5": 5, "15": 15, "30": 30,
            "60": 60, "120": 120, "240": 240, "360": 360,
            "720": 720, "D": 1440, "W": 10080, "M": 43200,
        }
        tf_mins = _tf_minutes.get(timeframe, 1)
        open_time = _ms_to_dt(start_ms)
        close_time = datetime.fromtimestamp(
            (start_ms + tf_mins * 60_000 - 1) / 1000, tz=timezone.utc
        ).replace(tzinfo=None)

        return Candle(
            symbol=symbol,
            timeframe=timeframe,
            open_time=open_time,
            close_time=close_time,
            open=float(raw[1]),
            high=float(raw[2]),
            low=float(raw[3]),
            close=float(raw[4]),
            volume=float(raw[5]),
            turnover=float(raw[6]) if len(raw) > 6 else None,
            exchange_timestamp=start_ms,
        )
    except (IndexError, ValueError, TypeError) as e:
        logger.warning("Failed to parse REST candle", error=str(e), raw=raw)
        return None


def parse_rest_candles(data: list[list], symbol: str, timeframe: str) -> list[Candle]:
    """Parse a list of REST klines, filtering out None results."""
    candles = [parse_rest_candle(row, symbol, timeframe) for row in data]
    return [c for c in candles if c is not None]


def parse_rest_ticker(raw: dict, symbol: str) -> Optional[Ticker]:
    """Parse Bybit v5 REST ticker response."""
    try:
        ts_raw = raw.get("time") or raw.get("ts")
        ts = _ms_to_dt(ts_raw) if ts_raw else datetime.utcnow()

        next_funding_raw = raw.get("nextFundingTime")
        return Ticker(
            symbol=symbol,
            timestamp=ts,
            last_price=float(raw["lastPrice"]),
            bid_price=float(raw["bid1Price"]) if raw.get("bid1Price") else None,
            ask_price=float(raw["ask1Price"]) if raw.get("ask1Price") else None,
            volume_24h=float(raw["volume24h"]) if raw.get("volume24h") else None,
            turnover_24h=float(raw["turnover24h"]) if raw.get("turnover24h") else None,
            price_change_24h=float(raw["price24hPcnt"]) if raw.get("price24hPcnt") else None,
            high_24h=float(raw["highPrice24h"]) if raw.get("highPrice24h") else None,
            low_24h=float(raw["lowPrice24h"]) if raw.get("lowPrice24h") else None,
            mark_price=float(raw["markPrice"]) if raw.get("markPrice") else None,
            index_price=float(raw["indexPrice"]) if raw.get("indexPrice") else None,
            open_interest=float(raw["openInterest"]) if raw.get("openInterest") else None,
            funding_rate=float(raw["fundingRate"]) if raw.get("fundingRate") else None,
            next_funding_time=_ms_to_dt(next_funding_raw) if next_funding_raw else None,
        )
    except (KeyError, ValueError, TypeError) as e:
        logger.warning("Failed to parse REST ticker", error=str(e))
        return None


def parse_rest_orderbook(raw: dict, symbol: str) -> Optional[OrderBook]:
    """Parse Bybit v5 REST order book."""
    try:
        ts = _ms_to_dt(raw.get("ts", 0)) if raw.get("ts") else datetime.utcnow()
        bids = [OrderBookLevel(price=float(b[0]), qty=float(b[1])) for b in raw.get("b", [])]
        asks = [OrderBookLevel(price=float(a[0]), qty=float(a[1])) for a in raw.get("a", [])]
        return OrderBook(symbol=symbol, timestamp=ts, bids=bids, asks=asks)
    except (KeyError, ValueError, TypeError) as e:
        logger.warning("Failed to parse REST orderbook", error=str(e))
        return None


def parse_rest_funding_rate(raw: dict) -> Optional[FundingRate]:
    """Parse funding rate from v5 REST."""
    try:
        return FundingRate(
            symbol=raw["symbol"],
            funding_rate=float(raw["fundingRate"]),
            funding_rate_timestamp=_ms_to_dt(raw["fundingRateTimestamp"]),
        )
    except (KeyError, ValueError) as e:
        logger.warning("Failed to parse funding rate", error=str(e))
        return None


def parse_rest_open_interest(raw: dict) -> Optional[OpenInterest]:
    """Parse open interest from v5 REST."""
    try:
        return OpenInterest(
            symbol=raw["symbol"],
            open_interest=float(raw["openInterest"]),
            timestamp=_ms_to_dt(raw["timestamp"]),
        )
    except (KeyError, ValueError) as e:
        logger.warning("Failed to parse open interest", error=str(e))
        return None


# ─────────────────────────────────────────────
# WebSocket Parsers
# ─────────────────────────────────────────────

def parse_ws_kline(msg: dict) -> list[Candle]:
    """
    Parse Bybit WebSocket kline message.
    Topic: kline.{interval}.{symbol}
    """
    candles = []
    try:
        topic: str = msg.get("topic", "")
        parts = topic.split(".")
        if len(parts) < 3:
            return candles
        timeframe = parts[1]
        symbol = parts[2]
        data_list = msg.get("data", [])
        for item in data_list:
            start_ms = int(item["start"])
            tf_minutes = {
                "1": 1, "3": 3, "5": 5, "15": 15, "30": 30,
                "60": 60, "120": 120, "240": 240, "360": 360,
                "720": 720, "D": 1440,
            }.get(timeframe, 1)
            open_time = _ms_to_dt(start_ms)
            close_time = datetime.fromtimestamp(
                (start_ms + tf_minutes * 60_000 - 1) / 1000, tz=timezone.utc
            ).replace(tzinfo=None)

            candle = Candle(
                symbol=symbol,
                timeframe=timeframe,
                open_time=open_time,
                close_time=close_time,
                open=float(item["open"]),
                high=float(item["high"]),
                low=float(item["low"]),
                close=float(item["close"]),
                volume=float(item["volume"]),
                turnover=float(item["turnover"]) if item.get("turnover") else None,
                exchange_timestamp=start_ms,
                is_closed=item.get("confirm", False),
            )
            candles.append(candle)
    except (KeyError, ValueError, TypeError) as e:
        logger.warning("Failed to parse WS kline", error=str(e))
    return candles


def parse_ws_orderbook(msg: dict) -> Optional[OrderBook]:
    """Parse Bybit WebSocket order book message."""
    try:
        data = msg.get("data", {})
        symbol = data.get("s") or msg.get("topic", "").split(".")[-1]
        ts = _ms_to_dt(msg.get("ts", 0))
        bids = [OrderBookLevel(price=float(b[0]), qty=float(b[1])) for b in data.get("b", [])]
        asks = [OrderBookLevel(price=float(a[0]), qty=float(a[1])) for a in data.get("a", [])]
        return OrderBook(symbol=symbol, timestamp=ts, bids=bids, asks=asks)
    except (KeyError, ValueError, TypeError) as e:
        logger.warning("Failed to parse WS orderbook", error=str(e))
        return None


def parse_ws_trade(msg: dict) -> list[Trade]:
    """Parse Bybit WebSocket public trade message."""
    trades = []
    try:
        data_list = msg.get("data", [])
        for item in data_list:
            trade = Trade(
                symbol=item.get("s", ""),
                trade_id=item.get("i", ""),
                trade_time=_ms_to_dt(item.get("T", 0)),
                price=float(item.get("p", 0)),
                qty=float(item.get("v", 0)),
                side=item.get("S", "Buy"),
                is_buyer_maker=item.get("BT", False),
            )
            trades.append(trade)
    except (KeyError, ValueError, TypeError) as e:
        logger.warning("Failed to parse WS trade", error=str(e))
    return trades


def parse_ws_ticker(msg: dict) -> Optional[Ticker]:
    """Parse Bybit WebSocket ticker message."""
    try:
        data = msg.get("data", {})
        topic = msg.get("topic", "")
        symbol = data.get("symbol") or topic.split(".")[-1]
        ts = _ms_to_dt(msg.get("ts", 0))
        return Ticker(
            symbol=symbol,
            timestamp=ts,
            last_price=float(data["lastPrice"]) if data.get("lastPrice") else 0.0,
            bid_price=float(data["bid1Price"]) if data.get("bid1Price") else None,
            ask_price=float(data["ask1Price"]) if data.get("ask1Price") else None,
            mark_price=float(data["markPrice"]) if data.get("markPrice") else None,
            index_price=float(data["indexPrice"]) if data.get("indexPrice") else None,
            open_interest=float(data["openInterest"]) if data.get("openInterest") else None,
            funding_rate=float(data["fundingRate"]) if data.get("fundingRate") else None,
        )
    except (KeyError, ValueError, TypeError) as e:
        logger.warning("Failed to parse WS ticker", error=str(e))
        return None


def parse_ws_liquidation(msg: dict) -> Optional[LiquidationEvent]:
    """Parse Bybit WebSocket liquidation event."""
    try:
        data = msg.get("data", {})
        return LiquidationEvent(
            symbol=data.get("symbol", ""),
            side=data.get("side", ""),
            size=float(data.get("size", 0)),
            price=float(data.get("price", 0)),
            timestamp=_ms_to_dt(data.get("updatedTime", 0)),
        )
    except (KeyError, ValueError, TypeError) as e:
        logger.warning("Failed to parse WS liquidation", error=str(e))
        return None
