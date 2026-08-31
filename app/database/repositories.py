"""
app/database/repositories.py
──────────────────────────────
Repository pattern for all DB tables.
Each repository encapsulates query logic for its domain entity.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional, Sequence

from sqlalchemy import and_, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    DataDriftEvent,
    EnsembleWeight,
    Feature,
    MarketData,
    MarketRegimeRecord,
    ModelMetric,
    ModelPrediction,
    ModelVersion,
    OrderBookSnapshot,
    PaperPosition,
    Prediction,
    RiskEvent,
    Signal,
    SignalResult,
    SystemEvent,
    TradingJournal,
    TrainingRun,
)


# ─────────────────────────────────────────────
# Market Data Repository
# ─────────────────────────────────────────────

class MarketDataRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def upsert_candle(self, candle: MarketData) -> None:
        """Insert a candle, ignore if duplicate."""
        from sqlalchemy.dialects.postgresql import insert
        stmt = insert(MarketData).values(
            symbol=candle.symbol,
            timeframe=candle.timeframe,
            open_time=candle.open_time,
            close_time=candle.close_time,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            volume=candle.volume,
            turnover=candle.turnover,
            exchange_timestamp=candle.exchange_timestamp,
        ).on_conflict_do_nothing(constraint="uq_market_data")
        await self.db.execute(stmt)

    async def get_candles(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
        limit: int = 5000,
    ) -> Sequence[MarketData]:
        stmt = (
            select(MarketData)
            .where(
                and_(
                    MarketData.symbol == symbol,
                    MarketData.timeframe == timeframe,
                    MarketData.open_time >= start,
                    MarketData.open_time <= end,
                )
            )
            .order_by(MarketData.open_time)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_latest_candle(self, symbol: str, timeframe: str) -> Optional[MarketData]:
        stmt = (
            select(MarketData)
            .where(
                and_(
                    MarketData.symbol == symbol,
                    MarketData.timeframe == timeframe,
                )
            )
            .order_by(desc(MarketData.open_time))
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_missing_periods(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> list[tuple[datetime, datetime]]:
        """Detect gaps in candle data."""
        candles = await self.get_candles(symbol, timeframe, start, end, limit=100_000)
        if not candles:
            return [(start, end)]
        gaps = []
        prev_time = start
        for c in candles:
            if (c.open_time - prev_time).total_seconds() > 120:  # 2-min tolerance
                gaps.append((prev_time, c.open_time))
            prev_time = c.close_time
        if (end - prev_time).total_seconds() > 120:
            gaps.append((prev_time, end))
        return gaps


# ─────────────────────────────────────────────
# Signal Repository
# ─────────────────────────────────────────────

class SignalRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, signal: Signal) -> Signal:
        self.db.add(signal)
        await self.db.flush()
        return signal

    async def get_by_signal_id(self, signal_id: str) -> Optional[Signal]:
        stmt = select(Signal).where(Signal.signal_id == signal_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_recent(self, symbol: Optional[str] = None, limit: int = 50) -> Sequence[Signal]:
        stmt = select(Signal).order_by(desc(Signal.generated_at)).limit(limit)
        if symbol:
            stmt = stmt.where(Signal.symbol == symbol)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update_lifecycle(self, signal_id: str, lifecycle: str) -> None:
        stmt = (
            update(Signal)
            .where(Signal.signal_id == signal_id)
            .values(lifecycle=lifecycle, updated_at=datetime.utcnow())
        )
        await self.db.execute(stmt)

    async def get_next_sequence(self) -> int:
        stmt = select(func.count()).select_from(Signal)
        result = await self.db.execute(stmt)
        count = result.scalar() or 0
        return count + 1


# ─────────────────────────────────────────────
# Trading Journal Repository
# ─────────────────────────────────────────────

class JournalRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, entry: TradingJournal) -> TradingJournal:
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def get_by_signal_id(self, signal_id: str) -> Optional[TradingJournal]:
        stmt = select(TradingJournal).where(TradingJournal.signal_id == signal_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_outcome(
        self,
        signal_id: str,
        outcome: str,
        pnl_r: float,
        pnl_pct: float,
        mfe: float,
        mae: float,
        duration_minutes: int,
    ) -> None:
        stmt = (
            update(TradingJournal)
            .where(TradingJournal.signal_id == signal_id)
            .values(
                outcome=outcome,
                pnl_r=pnl_r,
                pnl_pct=pnl_pct,
                mfe=mfe,
                mae=mae,
                duration_minutes=duration_minutes,
                updated_at=datetime.utcnow(),
            )
        )
        await self.db.execute(stmt)

    async def get_recent_outcomes(
        self, days: int = 30, symbol: Optional[str] = None
    ) -> Sequence[TradingJournal]:
        since = datetime.utcnow() - timedelta(days=days)
        stmt = (
            select(TradingJournal)
            .where(
                and_(
                    TradingJournal.timestamp >= since,
                    TradingJournal.outcome.isnot(None),
                )
            )
            .order_by(desc(TradingJournal.timestamp))
        )
        if symbol:
            stmt = stmt.where(TradingJournal.symbol == symbol)
        result = await self.db.execute(stmt)
        return result.scalars().all()


# ─────────────────────────────────────────────
# Model Version Repository
# ─────────────────────────────────────────────

class ModelRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, model_version: ModelVersion) -> ModelVersion:
        self.db.add(model_version)
        await self.db.flush()
        return model_version

    async def get_champion(self, model_name: str) -> Optional[ModelVersion]:
        stmt = (
            select(ModelVersion)
            .where(
                and_(
                    ModelVersion.model_name == model_name,
                    ModelVersion.status == "CHAMPION",
                )
            )
            .order_by(desc(ModelVersion.created_at))
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_champions(self) -> Sequence[ModelVersion]:
        stmt = (
            select(ModelVersion)
            .where(ModelVersion.status == "CHAMPION")
            .order_by(ModelVersion.model_name)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update_status(self, model_version_id: int, status: str) -> None:
        stmt = (
            update(ModelVersion)
            .where(ModelVersion.id == model_version_id)
            .values(status=status, updated_at=datetime.utcnow())
        )
        await self.db.execute(stmt)

    async def get_metrics(
        self, model_version_id: int, limit: int = 100
    ) -> Sequence[ModelMetric]:
        stmt = (
            select(ModelMetric)
            .where(ModelMetric.model_version_id == model_version_id)
            .order_by(desc(ModelMetric.evaluated_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()


# ─────────────────────────────────────────────
# Feature Repository
# ─────────────────────────────────────────────

class FeatureRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def bulk_upsert(self, features: list[Feature]) -> None:
        from sqlalchemy.dialects.postgresql import insert
        if not features:
            return
        data = [
            {
                "symbol": f.symbol,
                "timeframe": f.timeframe,
                "timestamp": f.timestamp,
                "feature_name": f.feature_name,
                "feature_value": f.feature_value,
                "feature_version": f.feature_version,
            }
            for f in features
        ]
        stmt = insert(Feature).values(data).on_conflict_do_nothing(constraint="uq_feature")
        await self.db.execute(stmt)

    async def get_features(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
        version: str = "v1",
    ) -> Sequence[Feature]:
        stmt = (
            select(Feature)
            .where(
                and_(
                    Feature.symbol == symbol,
                    Feature.timeframe == timeframe,
                    Feature.timestamp >= start,
                    Feature.timestamp <= end,
                    Feature.feature_version == version,
                )
            )
            .order_by(Feature.timestamp, Feature.feature_name)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()


# ─────────────────────────────────────────────
# Paper Position Repository
# ─────────────────────────────────────────────

class PaperPositionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, pos: PaperPosition) -> PaperPosition:
        self.db.add(pos)
        await self.db.flush()
        return pos

    async def get_open_positions(self, symbol: Optional[str] = None) -> Sequence[PaperPosition]:
        stmt = select(PaperPosition).where(PaperPosition.status == "OPEN")
        if symbol:
            stmt = stmt.where(PaperPosition.symbol == symbol)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update_pnl(self, position_id: int, unrealized_pnl: float) -> None:
        stmt = (
            update(PaperPosition)
            .where(PaperPosition.id == position_id)
            .values(unrealized_pnl=unrealized_pnl, updated_at=datetime.utcnow())
        )
        await self.db.execute(stmt)

    async def close_position(
        self,
        position_id: int,
        realized_pnl: float,
        fees_paid: float,
        status: str,
    ) -> None:
        stmt = (
            update(PaperPosition)
            .where(PaperPosition.id == position_id)
            .values(
                status=status,
                realized_pnl=realized_pnl,
                fees_paid=fees_paid,
                closed_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )
        await self.db.execute(stmt)


# ─────────────────────────────────────────────
# Risk Event Repository
# ─────────────────────────────────────────────

class RiskEventRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, event: RiskEvent) -> RiskEvent:
        self.db.add(event)
        await self.db.flush()
        return event

    async def get_today_events(self) -> Sequence[RiskEvent]:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        stmt = (
            select(RiskEvent)
            .where(RiskEvent.occurred_at >= today_start)
            .order_by(desc(RiskEvent.occurred_at))
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
