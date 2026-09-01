"""
app/tasks/market_data.py
─────────────────────────
Celery tasks for market data ingestion.
"""

from __future__ import annotations

from celery import shared_task

from app.core.logging import get_logger

logger = get_logger("market")


@shared_task(name="tasks.sync_historical_candles", bind=True, max_retries=3)
def sync_historical_candles(self, symbol: str = "BTCUSDT", timeframe: str = "1", days_back: int = 30):
    """
    Celery task: Download and persist historical candles from Bybit.
    Runs on startup and daily for data refresh.
    """
    import asyncio
    from datetime import datetime, timedelta

    from app.database.models import MarketData
    from app.database.repositories import MarketDataRepository
    from app.database.session import AsyncSessionLocal
    from app.exchange.bybit.client import BybitClient

    logger.info("Syncing historical candles", symbol=symbol, timeframe=timeframe, days_back=days_back)
    try:
        start = datetime.utcnow() - timedelta(days=days_back)

        async def run():
            client = BybitClient()
            candles = await client.get_historical_candles(symbol, timeframe, start)
            logger.info("Downloaded candles", symbol=symbol, timeframe=timeframe, count=len(candles))

            if candles:
                async with AsyncSessionLocal() as db:
                    repo = MarketDataRepository(db)
                    for c in candles:
                        candle_obj = MarketData(
                            symbol=c.symbol,
                            timeframe=c.timeframe,
                            open_time=c.open_time,
                            close_time=c.close_time,
                            open=c.open,
                            high=c.high,
                            low=c.low,
                            close=c.close,
                            volume=c.volume,
                            turnover=c.turnover,
                            exchange_timestamp=c.exchange_timestamp,
                        )
                        await repo.upsert_candle(candle_obj)
                    await db.commit()
            return candles

        candles = asyncio.run(run())
        logger.info("Historical sync complete", symbol=symbol, timeframe=timeframe)
        return {"symbol": symbol, "timeframe": timeframe, "count": len(candles)}

    except Exception as exc:
        logger.error("Historical sync failed", symbol=symbol, error=str(exc))
        raise self.retry(exc=exc, countdown=60)


@shared_task(name="tasks.compute_features", bind=True)
def compute_features(self, symbol: str, timeframe: str):
    """Celery task: Compute features for a symbol/timeframe."""
    import asyncio
    from app.features.pipeline import FeaturePipeline
    logger.info("Computing features", symbol=symbol, timeframe=timeframe)
    # Implementation hooks into DB-stored candles
    return {"status": "ok", "symbol": symbol, "timeframe": timeframe}


@shared_task(name="tasks.generate_signal", bind=True, max_retries=2)
def generate_signal_task(self, symbol: str, timeframe: str):
    """Celery task: Run full prediction pipeline for a symbol."""
    import asyncio
    logger.info("Generating signal", symbol=symbol, timeframe=timeframe)
    # Full pipeline called from here
    return {"status": "ok", "symbol": symbol, "timeframe": timeframe}
