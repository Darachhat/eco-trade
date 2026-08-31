"""
app/exchange/bybit/rest.py
───────────────────────────
Async Bybit REST API v5 client.
Supports: historical candles, ticker, order book, funding rate, open interest.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any, Optional
from urllib.parse import urlencode

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.core.constants import MAX_CANDLES_PER_REQUEST, BYBIT_REST_MAINNET, BYBIT_REST_TESTNET
from app.core.logging import get_logger
from app.core.security import get_bybit_headers
from app.exchange.bybit.models import (
    Candle,
    FundingRate,
    OpenInterest,
    OrderBook,
    Ticker,
)
from app.exchange.bybit.parser import (
    parse_rest_candles,
    parse_rest_funding_rate,
    parse_rest_open_interest,
    parse_rest_orderbook,
    parse_rest_ticker,
)

logger = get_logger("market")


class BybitRESTClient:
    """
    Async Bybit v5 REST API client.

    Handles rate limiting, retries with exponential backoff,
    and pagination for historical data downloads.
    """

    def __init__(self) -> None:
        self.base_url = BYBIT_REST_TESTNET if settings.bybit_testnet else BYBIT_REST_MAINNET
        self.category = settings.bybit_category.value
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limit_delay = 0.1  # 100ms between requests

    async def __aenter__(self) -> "BybitRESTClient":
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
            headers={"Content-Type": "application/json"},
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("BybitRESTClient must be used as async context manager")
        return self._client

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        stop=stop_after_attempt(5),
    )
    async def _get(self, path: str, params: dict[str, Any]) -> dict:
        """Raw GET with retry and rate-limit delay."""
        await asyncio.sleep(self._rate_limit_delay)
        response = await self.client.get(path, params=params)
        response.raise_for_status()
        data = response.json()
        if data.get("retCode") != 0:
            raise RuntimeError(
                f"Bybit API error {data.get('retCode')}: {data.get('retMsg')}"
            )
        return data

    async def get_klines(
        self,
        symbol: str,
        interval: str,
        start_ms: Optional[int] = None,
        end_ms: Optional[int] = None,
        limit: int = MAX_CANDLES_PER_REQUEST,
    ) -> list[Candle]:
        """Fetch klines from Bybit v5 REST API."""
        params: dict[str, Any] = {
            "category": self.category,
            "symbol": symbol,
            "interval": interval,
            "limit": min(limit, MAX_CANDLES_PER_REQUEST),
        }
        if start_ms:
            params["start"] = start_ms
        if end_ms:
            params["end"] = end_ms

        data = await self._get("/v5/market/kline", params)
        raw_list = data.get("result", {}).get("list", [])
        # Bybit returns newest first — reverse to chronological order
        raw_list = list(reversed(raw_list))
        return parse_rest_candles(raw_list, symbol, interval)

    async def download_historical_candles(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: Optional[datetime] = None,
    ) -> list[Candle]:
        """
        Download all historical candles from start to end.
        Handles pagination automatically.
        No future data is included.
        """
        if end is None:
            end = datetime.utcnow()

        all_candles: list[Candle] = []
        current_start = int(start.timestamp() * 1000)
        end_ms = int(end.timestamp() * 1000)

        logger.info(
            "Downloading historical candles",
            symbol=symbol,
            interval=interval,
            start=start.isoformat(),
            end=end.isoformat(),
        )

        while current_start < end_ms:
            candles = await self.get_klines(
                symbol=symbol,
                interval=interval,
                start_ms=current_start,
                end_ms=min(current_start + MAX_CANDLES_PER_REQUEST * _interval_ms(interval), end_ms),
                limit=MAX_CANDLES_PER_REQUEST,
            )
            if not candles:
                break

            # Filter: only closed candles before end
            candles = [c for c in candles if c.open_time.timestamp() * 1000 < end_ms]
            all_candles.extend(candles)

            last_time_ms = int(candles[-1].open_time.timestamp() * 1000)
            if last_time_ms <= current_start:
                break
            current_start = last_time_ms + _interval_ms(interval)

            logger.debug(
                "Fetched candle batch",
                symbol=symbol,
                interval=interval,
                count=len(candles),
                total=len(all_candles),
            )

        # Deduplicate by open_time
        seen: set[datetime] = set()
        unique: list[Candle] = []
        for c in all_candles:
            if c.open_time not in seen:
                seen.add(c.open_time)
                unique.append(c)

        logger.info(
            "Historical download complete",
            symbol=symbol,
            interval=interval,
            total_candles=len(unique),
        )
        return unique

    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Get current ticker for a symbol."""
        try:
            data = await self._get(
                "/v5/market/tickers",
                {"category": self.category, "symbol": symbol},
            )
            items = data.get("result", {}).get("list", [])
            if not items:
                return None
            return parse_rest_ticker(items[0], symbol)
        except Exception as e:
            logger.error("Failed to get ticker", symbol=symbol, error=str(e))
            return None

    async def get_orderbook(self, symbol: str, depth: int = 25) -> Optional[OrderBook]:
        """Get current order book."""
        try:
            data = await self._get(
                "/v5/market/orderbook",
                {"category": self.category, "symbol": symbol, "limit": depth},
            )
            return parse_rest_orderbook(data.get("result", {}), symbol)
        except Exception as e:
            logger.error("Failed to get orderbook", symbol=symbol, error=str(e))
            return None

    async def get_funding_rate(self, symbol: str) -> Optional[FundingRate]:
        """Get latest funding rate."""
        try:
            data = await self._get(
                "/v5/market/funding/history",
                {"category": self.category, "symbol": symbol, "limit": 1},
            )
            items = data.get("result", {}).get("list", [])
            if not items:
                return None
            return parse_rest_funding_rate(items[0])
        except Exception as e:
            logger.error("Failed to get funding rate", symbol=symbol, error=str(e))
            return None

    async def get_open_interest(self, symbol: str, interval: str = "1h") -> Optional[OpenInterest]:
        """Get latest open interest."""
        try:
            data = await self._get(
                "/v5/market/open-interest",
                {"category": self.category, "symbol": symbol, "intervalTime": interval, "limit": 1},
            )
            items = data.get("result", {}).get("list", [])
            if not items:
                return None
            item = items[0]
            item["symbol"] = symbol
            return parse_rest_open_interest(item)
        except Exception as e:
            logger.error("Failed to get open interest", symbol=symbol, error=str(e))
            return None

    async def get_server_time(self) -> int:
        """Get Bybit server timestamp in milliseconds."""
        data = await self._get("/v5/market/time", {})
        return int(data.get("result", {}).get("timeNano", 0)) // 1_000_000


def _interval_ms(interval: str) -> int:
    """Convert Bybit interval string to milliseconds."""
    _map = {
        "1": 60_000,
        "3": 180_000,
        "5": 300_000,
        "15": 900_000,
        "30": 1_800_000,
        "60": 3_600_000,
        "120": 7_200_000,
        "240": 14_400_000,
        "360": 21_600_000,
        "720": 43_200_000,
        "D": 86_400_000,
        "W": 604_800_000,
    }
    return _map.get(interval, 60_000)
