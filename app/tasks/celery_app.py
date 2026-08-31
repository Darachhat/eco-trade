"""
app/tasks/celery_app.py
────────────────────────
Celery application factory with beat schedule.
"""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings


def create_celery() -> Celery:
    app = Celery(
        "ecotrade",
        broker=settings.redis_url,
        backend=settings.redis_url,
        include=[
            "app.tasks.market_data",
            "app.tasks.model_retraining",
            "app.tasks.reports",
        ],
    )

    app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        task_reject_on_worker_lost=True,
    )

    # Beat schedule
    app.conf.beat_schedule = {
        # Sync historical data daily at 00:05 UTC
        "sync-historical-daily": {
            "task": "tasks.sync_historical_candles",
            "schedule": crontab(hour=0, minute=5),
            "args": ("BTCUSDT", "1"),
            "kwargs": {"days_back": 30},
        },

        # Weekly model retraining on Sunday 02:00 UTC
        "retrain-models-weekly": {
            "task": "tasks.retrain_models",
            "schedule": crontab(hour=2, minute=0, day_of_week=0),
            "args": (),
        },

        # Daily performance report
        "daily-report": {
            "task": "tasks.send_daily_report",
            "schedule": crontab(hour=8, minute=0),
        },
    }

    return app


celery_app = create_celery()
