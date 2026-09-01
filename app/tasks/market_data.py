"""
app/tasks/market_data.py
─────────────────────────
Celery tasks for market data ingestion, continuous quantitative scanning,
and automated Telegram signal broadcasting.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta

from celery import shared_task

from app.core.config import settings
from app.core.constants import SignalDirection
from app.core.logging import get_logger

logger = get_logger("market")

# Memory cache for signal cooldowns
_RECENT_SIGNALS: dict[str, datetime] = {}


@shared_task(name="tasks.sync_historical_candles", bind=True, max_retries=3)
def sync_historical_candles(self, symbol: str = "BTCUSDT", timeframe: str = "1", days_back: int = 30):
    """
    Celery task: Download and persist historical candles from Bybit.
    Runs on startup and daily for data refresh.
    """
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
    logger.info("Computing features", symbol=symbol, timeframe=timeframe)
    return {"status": "ok", "symbol": symbol, "timeframe": timeframe}


@shared_task(name="tasks.scan_and_generate_signals")
def scan_and_generate_signals():
    """
    Celery periodic task: Scan all configured symbols, run the full AI ensemble pipeline,
    and automatically broadcast signals when a valid entry is detected.
    """
    symbols = settings.symbols_list
    logger.info("Running automated market scan for signals", symbols=symbols)
    results = {}

    for sym in symbols:
        try:
            res = generate_signal_task(symbol=sym, timeframe="15")
            results[sym] = res
        except Exception as e:
            logger.error("Automated scan failed for symbol", symbol=sym, error=str(e))
            results[sym] = {"status": "ERROR", "error": str(e)}

    return results


@shared_task(name="tasks.generate_signal", bind=True, max_retries=2)
def generate_signal_task(self=None, symbol: str = "BTCUSDT", timeframe: str = "15"):
    """
    Celery task: Run full AI prediction pipeline for a symbol.
    If a high-probability LONG/SHORT setup is detected, send alert to Telegram
    and open a paper trading position.
    """
    from app.database.models import Signal as SignalModel
    from app.database.repositories import SignalRepository
    from app.database.session import AsyncSessionLocal
    from app.ensemble.engine import EnsembleEngine
    from app.exchange.bybit.client import BybitClient
    from app.execution.paper import paper_engine
    from app.features.pipeline import FeaturePipeline, candles_to_dataframe
    from app.models.base import BaseMLModel
    from app.models.technical import TechnicalModel
    from app.regime.detector import MarketRegimeDetector
    from app.risk.manager import risk_manager
    from app.strategy.signal_engine import SignalEngine
    from app.telegram.bot import telegram_bot
    from app.telegram.formatter import format_signal

    logger.info("Evaluating AI signal pipeline", symbol=symbol, timeframe=timeframe)

    async def run():
        client = BybitClient()
        candles = await client.get_candles(symbol, timeframe, limit=200)
        if not candles or len(candles) < 30:
            logger.warning("Insufficient candles for signal evaluation", symbol=symbol, count=len(candles) if candles else 0)
            return {"status": "SKIPPED", "reason": "Insufficient candles"}

        ticker = await client.get_ticker(symbol)
        curr_price = ticker.last_price if ticker else float(candles[-1].close)

        df = candles_to_dataframe(candles)
        pipeline = FeaturePipeline()
        df_feat = pipeline.compute(df)

        detector = MarketRegimeDetector()
        regime_res = detector.detect(df_feat, symbol, timeframe)

        models: dict[str, BaseMLModel] = {
            "Technical": TechnicalModel(),
        }

        try:
            from app.models.xgboost_model import XGBoostModel
            xgb = XGBoostModel()
            if xgb.is_trained:
                models["XGBoost"] = xgb
        except Exception:
            pass

        try:
            from app.models.lightgbm_model import LightGBMModel
            lgb = LightGBMModel()
            if lgb.is_trained:
                models["LightGBM"] = lgb
        except Exception:
            pass

        ensemble = EnsembleEngine(models=models)
        ens_result = ensemble.predict(
            X=df_feat,
            symbol=symbol,
            timeframe=timeframe,
            regime=regime_res.regime.value if regime_res else None,
        )

        direction = ens_result.get("direction", SignalDirection.NO_TRADE)
        risk_allowed, _ = risk_manager.can_trade(symbol=symbol, direction=direction)

        signal_engine = SignalEngine()
        trade_signal = signal_engine.generate(
            ensemble_result=ens_result,
            df=df_feat,
            symbol=symbol,
            timeframe=timeframe,
            regime=regime_res,
            current_price=curr_price,
            risk_ok=risk_allowed,
        )

        # If a valid LONG or SHORT signal is detected
        if trade_signal.direction in (SignalDirection.LONG, SignalDirection.SHORT):
            key = f"{symbol}_{trade_signal.direction.value}"
            now = datetime.utcnow()

            # Cooldown: 15 minutes between duplicate alerts
            last_sent = _RECENT_SIGNALS.get(key)
            if last_sent and (now - last_sent).total_seconds() < 900:
                logger.info("Signal in cooldown window", symbol=symbol, direction=trade_signal.direction.value)
                return {"status": "COOLDOWN", "symbol": symbol, "direction": trade_signal.direction.value}

            _RECENT_SIGNALS[key] = now
            signal_id = f"SIG-{uuid.uuid4().hex[:8].upper()}"

            # 1. Open Position in Paper Engine
            try:
                entry_low = trade_signal.entry_zone.price_low if trade_signal.entry_zone else curr_price
                entry_high = trade_signal.entry_zone.price_high if trade_signal.entry_zone else curr_price
                avg_entry = (entry_low + entry_high) / 2 if (entry_low and entry_high) else curr_price
                sl_price = trade_signal.stop_loss.price if trade_signal.stop_loss else (curr_price * 0.98 if trade_signal.direction == SignalDirection.LONG else curr_price * 1.02)
                tp1 = trade_signal.take_profit.tp1 if trade_signal.take_profit else (curr_price * 1.03 if trade_signal.direction == SignalDirection.LONG else curr_price * 0.97)

                await paper_engine.open_position(
                    signal_id=signal_id,
                    symbol=symbol,
                    direction=trade_signal.direction.value,
                    entry_price=avg_entry,
                    qty=0.01,
                    stop_loss=sl_price,
                    take_profit_1=tp1,
                )
            except Exception as e:
                logger.error("Failed to open paper position for signal", error=str(e))

            # 2. Persist Signal to DB
            try:
                async with AsyncSessionLocal() as db:
                    repo = SignalRepository(db)
                    db_sig = SignalModel(
                        signal_id=signal_id,
                        symbol=symbol,
                        timeframe=timeframe,
                        generated_at=now,
                        direction=trade_signal.direction.value,
                        entry_low=trade_signal.entry_zone.price_low if trade_signal.entry_zone else curr_price,
                        entry_high=trade_signal.entry_zone.price_high if trade_signal.entry_zone else curr_price,
                        entry_type="ZONE",
                        stop_loss=sl_price,
                        take_profit_1=tp1,
                        risk_reward=trade_signal.take_profit.risk_reward_tp1 if trade_signal.take_profit else 2.0,
                        confidence=trade_signal.confidence,
                        model_agreement=trade_signal.model_agreement,
                        signal_quality=trade_signal.quality_score.total if trade_signal.quality_score else 70.0,
                        regime=trade_signal.regime,
                        lifecycle="ACTIVE",
                        trading_mode=settings.trading_mode.value,
                    )
                    await repo.create(db_sig)
                    await db.commit()
            except Exception as e:
                logger.error("Failed to persist signal to database", error=str(e))

            # 3. Broadcast Alert to Telegram
            mode_label = f"{settings.trading_mode.value.upper()} TRADING"
            formatted_msg = format_signal(trade_signal, signal_id=signal_id, mode=mode_label)
            await telegram_bot.send_signal_alert(formatted_msg)
            logger.info(
                "Automatic AI signal broadcasted to Telegram",
                signal_id=signal_id,
                symbol=symbol,
                direction=trade_signal.direction.value,
                confidence=trade_signal.confidence,
            )

            return {
                "status": "SIGNAL_BROADCASTED",
                "signal_id": signal_id,
                "symbol": symbol,
                "direction": trade_signal.direction.value,
                "confidence": trade_signal.confidence,
            }

        return {
            "status": "NO_TRADE",
            "symbol": symbol,
            "reason": trade_signal.no_trade_reason,
        }

    return asyncio.run(run())
