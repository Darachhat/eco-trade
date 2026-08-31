"""
app/tasks/model_retraining.py
──────────────────────────────
Celery background tasks for scheduled and event-driven model retraining.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from celery import shared_task

from app.core.config import settings
from app.core.constants import ModelName
from app.core.logging import get_logger

logger = get_logger("model")


@shared_task(name="tasks.retrain_models", bind=True, max_retries=2)
def retrain_models(self, symbol: str = "BTCUSDT", timeframe: str = "15", days_back: int = 180):
    """
    Celery task: Run automated retraining for active model families.
    Fetches historical data, executes feature pipeline, tunes hyperparams, and updates champions.
    """
    logger.info("Triggered scheduled model retraining task", symbol=symbol, timeframe=timeframe)

    try:
        from app.exchange.bybit.client import BybitClient
        from app.features.pipeline import candles_to_dataframe
        from app.models.retrainer import ModelRetrainer

        # 1. Fetch training data from Bybit
        start_date = datetime.utcnow() - timedelta(days=days_back)

        async def fetch():
            client = BybitClient()
            return await client.get_historical_candles(symbol, timeframe, start_date)

        candles = asyncio.run(fetch())
        if len(candles) < 500:
            logger.warning("Not enough candles fetched for retraining", count=len(candles))
            return {"status": "SKIPPED", "reason": "Insufficient candles"}

        df = candles_to_dataframe(candles)

        # 2. Retrain key tabular ML models
        retrainer = ModelRetrainer()
        results = {}

        for model_name in [ModelName.XGBOOST, ModelName.LIGHTGBM, ModelName.RANDOM_FOREST]:
            try:
                res = retrainer.retrain_model(
                    model_name=model_name,
                    df_candles=df,
                    optimize_hyperparams=True,
                    n_trials=10,
                )
                results[model_name] = res
            except Exception as e:
                logger.error(f"Retraining failed for {model_name}", error=str(e))
                results[model_name] = {"error": str(e)}

        logger.info("Model retraining task complete", results=results)
        return {"status": "SUCCESS", "results": results}

    except Exception as exc:
        logger.error("Model retraining task failed", error=str(exc))
        raise self.retry(exc=exc, countdown=300)


@shared_task(name="tasks.check_drift_and_retrain", bind=True)
def check_drift_and_retrain(self, symbol: str = "BTCUSDT", timeframe: str = "15"):
    """
    Celery task: Evaluate feature & performance drift.
    If drift threshold is exceeded, automatically queues a model retraining task.
    """
    logger.info("Executing periodic drift check", symbol=symbol, timeframe=timeframe)
    try:
        from app.exchange.bybit.client import BybitClient
        from app.features.pipeline import FeaturePipeline, candles_to_dataframe
        from app.monitoring.drift import DriftDetector

        # Fetch baseline (older 60 days) and current (recent 15 days) data
        async def fetch():
            client = BybitClient()
            ref_start = datetime.utcnow() - timedelta(days=60)
            return await client.get_historical_candles(symbol, timeframe, ref_start)

        candles = asyncio.run(fetch())
        if len(candles) < 300:
            return {"status": "SKIPPED", "reason": "Insufficient candles"}

        df = candles_to_dataframe(candles)
        pipeline = FeaturePipeline()
        df_feat = pipeline.compute(df)

        split_idx = int(len(df_feat) * 0.75)
        ref_df = df_feat.iloc[:split_idx]
        cur_df = df_feat.iloc[split_idx:]

        detector = DriftDetector()
        summary = detector.evaluate_drift(
            reference_features=ref_df,
            current_features=cur_df,
            historical_preds=[],
            recent_preds=[],
        )

        if summary.requires_retraining:
            logger.warning("Drift detected! Queuing automatic model retraining task.")
            retrain_models.delay(symbol, timeframe)

        return {
            "status": "COMPLETED",
            "requires_retraining": summary.requires_retraining,
            "drifted_features_count": len(summary.drifted_features),
        }

    except Exception as e:
        logger.error("Drift check failed", error=str(e))
        return {"status": "ERROR", "error": str(e)}
