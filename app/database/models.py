"""
app/database/models.py
───────────────────────
All 20 SQLAlchemy ORM table definitions.
Indexed for time-series query performance.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


def _utcnow() -> datetime:
    return datetime.utcnow()


# ─────────────────────────────────────────────
# 1. Market Data (OHLCV candles)
# ─────────────────────────────────────────────

class MarketData(Base):
    __tablename__ = "market_data"
    __table_args__ = (
        UniqueConstraint("symbol", "timeframe", "open_time", name="uq_market_data"),
        Index("ix_market_data_symbol_tf_time", "symbol", "timeframe", "open_time"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    close_time: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    open: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    high: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    low: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    close: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    volume: Mapped[float] = mapped_column(Numeric(30, 8), nullable=False)
    turnover: Mapped[Optional[float]] = mapped_column(Numeric(30, 8))
    exchange_timestamp: Mapped[Optional[int]] = mapped_column(BigInteger)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)


# ─────────────────────────────────────────────
# 2. Order Book Snapshots
# ─────────────────────────────────────────────

class OrderBookSnapshot(Base):
    __tablename__ = "orderbook_snapshots"
    __table_args__ = (
        Index("ix_orderbook_symbol_ts", "symbol", "snapshot_time"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    snapshot_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    bids: Mapped[dict] = mapped_column(JSON, nullable=False)
    asks: Mapped[dict] = mapped_column(JSON, nullable=False)
    bid_volume: Mapped[Optional[float]] = mapped_column(Float)
    ask_volume: Mapped[Optional[float]] = mapped_column(Float)
    spread: Mapped[Optional[float]] = mapped_column(Float)
    mid_price: Mapped[Optional[float]] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


# ─────────────────────────────────────────────
# 3. Market Trades
# ─────────────────────────────────────────────

class MarketTrade(Base):
    __tablename__ = "trades_market"
    __table_args__ = (
        Index("ix_trades_market_symbol_ts", "symbol", "trade_time"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    trade_id: Mapped[str] = mapped_column(String(64), nullable=False)
    trade_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    price: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    qty: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


# ─────────────────────────────────────────────
# 4. Feature Store
# ─────────────────────────────────────────────

class Feature(Base):
    __tablename__ = "features"
    __table_args__ = (
        UniqueConstraint(
            "symbol", "timeframe", "timestamp", "feature_name", "feature_version",
            name="uq_feature",
        ),
        Index("ix_features_symbol_tf_ts", "symbol", "timeframe", "timestamp"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    feature_name: Mapped[str] = mapped_column(String(100), nullable=False)
    feature_value: Mapped[Optional[float]] = mapped_column(Float)
    feature_version: Mapped[str] = mapped_column(String(10), nullable=False, default="v1")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


# ─────────────────────────────────────────────
# 5. Market Regimes
# ─────────────────────────────────────────────

class MarketRegimeRecord(Base):
    __tablename__ = "market_regimes"
    __table_args__ = (
        Index("ix_regimes_symbol_ts", "symbol", "detected_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    regime: Mapped[str] = mapped_column(String(30), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    indicators: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


# ─────────────────────────────────────────────
# 6. Model Versions (Registry)
# ─────────────────────────────────────────────

class ModelVersion(Base):
    __tablename__ = "model_versions"
    __table_args__ = (
        Index("ix_model_versions_name_status", "model_name", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    model_name: Mapped[str] = mapped_column(String(50), nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="TRAINING")
    feature_version: Mapped[str] = mapped_column(String(10), nullable=False, default="v1")
    training_period_start: Mapped[Optional[datetime]] = mapped_column(DateTime)
    training_period_end: Mapped[Optional[datetime]] = mapped_column(DateTime)
    validation_period_start: Mapped[Optional[datetime]] = mapped_column(DateTime)
    validation_period_end: Mapped[Optional[datetime]] = mapped_column(DateTime)
    test_period_start: Mapped[Optional[datetime]] = mapped_column(DateTime)
    test_period_end: Mapped[Optional[datetime]] = mapped_column(DateTime)
    hyperparameters: Mapped[Optional[dict]] = mapped_column(JSON)
    metrics: Mapped[Optional[dict]] = mapped_column(JSON)
    market_regimes: Mapped[Optional[dict]] = mapped_column(JSON)
    artifact_path: Mapped[Optional[str]] = mapped_column(String(500))
    mlflow_run_id: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)


# ─────────────────────────────────────────────
# 7. Model Metrics (per-evaluation record)
# ─────────────────────────────────────────────

class ModelMetric(Base):
    __tablename__ = "model_metrics"
    __table_args__ = (
        Index("ix_model_metrics_version_ts", "model_version_id", "evaluated_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    model_version_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("model_versions.id"), nullable=False
    )
    evaluated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    symbol: Mapped[Optional[str]] = mapped_column(String(20))
    timeframe: Mapped[Optional[str]] = mapped_column(String(10))
    accuracy: Mapped[Optional[float]] = mapped_column(Float)
    precision: Mapped[Optional[float]] = mapped_column(Float)
    recall: Mapped[Optional[float]] = mapped_column(Float)
    f1: Mapped[Optional[float]] = mapped_column(Float)
    roc_auc: Mapped[Optional[float]] = mapped_column(Float)
    brier_score: Mapped[Optional[float]] = mapped_column(Float)
    win_rate: Mapped[Optional[float]] = mapped_column(Float)
    profit_factor: Mapped[Optional[float]] = mapped_column(Float)
    expectancy: Mapped[Optional[float]] = mapped_column(Float)
    sharpe: Mapped[Optional[float]] = mapped_column(Float)
    sortino: Mapped[Optional[float]] = mapped_column(Float)
    max_drawdown: Mapped[Optional[float]] = mapped_column(Float)
    sample_count: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


# ─────────────────────────────────────────────
# 8. Ensemble Weights
# ─────────────────────────────────────────────

class EnsembleWeight(Base):
    __tablename__ = "ensemble_weights"
    __table_args__ = (
        Index("ix_ensemble_weights_symbol_tf_ts", "symbol", "timeframe", "computed_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    regime: Mapped[Optional[str]] = mapped_column(String(30))
    computed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    weights: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


# ─────────────────────────────────────────────
# 9. Predictions (per model per cycle)
# ─────────────────────────────────────────────

class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        Index("ix_predictions_symbol_tf_ts", "symbol", "timeframe", "predicted_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    predicted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    horizon: Mapped[int] = mapped_column(Integer, nullable=False)
    ensemble_direction: Mapped[str] = mapped_column(String(20), nullable=False)
    ensemble_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    model_agreement: Mapped[float] = mapped_column(Float, nullable=False)
    regime: Mapped[Optional[str]] = mapped_column(String(30))
    model_predictions: Mapped[Optional[dict]] = mapped_column(JSON)
    ensemble_weights: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


# ─────────────────────────────────────────────
# 10. Individual Model Predictions
# ─────────────────────────────────────────────

class ModelPrediction(Base):
    __tablename__ = "model_predictions"
    __table_args__ = (
        Index("ix_model_predictions_pred_id", "prediction_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    prediction_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("predictions.id"), nullable=False
    )
    model_name: Mapped[str] = mapped_column(String(50), nullable=False)
    model_version: Mapped[str] = mapped_column(String(20), nullable=False)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    prob_long: Mapped[float] = mapped_column(Float, nullable=False)
    prob_short: Mapped[float] = mapped_column(Float, nullable=False)
    prob_no_trade: Mapped[float] = mapped_column(Float, nullable=False)
    inference_ms: Mapped[Optional[float]] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


# ─────────────────────────────────────────────
# 11. Signals
# ─────────────────────────────────────────────

class Signal(Base):
    __tablename__ = "signals"
    __table_args__ = (
        Index("ix_signals_symbol_ts", "symbol", "generated_at"),
        Index("ix_signals_signal_id", "signal_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    signal_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    entry_low: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    entry_high: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    entry_type: Mapped[str] = mapped_column(String(20), nullable=False)
    stop_loss: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    take_profit_1: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    take_profit_2: Mapped[Optional[float]] = mapped_column(Numeric(20, 8))
    take_profit_3: Mapped[Optional[float]] = mapped_column(Numeric(20, 8))
    risk_reward: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    model_agreement: Mapped[float] = mapped_column(Float, nullable=False)
    signal_quality: Mapped[float] = mapped_column(Float, nullable=False)
    regime: Mapped[Optional[str]] = mapped_column(String(30))
    lifecycle: Mapped[str] = mapped_column(String(30), nullable=False, default="GENERATED")
    trading_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="paper")
    model_predictions: Mapped[Optional[dict]] = mapped_column(JSON)
    ensemble_weights: Mapped[Optional[dict]] = mapped_column(JSON)
    features_snapshot: Mapped[Optional[dict]] = mapped_column(JSON)
    explanation: Mapped[Optional[dict]] = mapped_column(JSON)
    mtf_consensus: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)


# ─────────────────────────────────────────────
# 12. Signal Results
# ─────────────────────────────────────────────

class SignalResult(Base):
    __tablename__ = "signal_results"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    signal_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("signals.signal_id"), nullable=False
    )
    resolved_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    outcome: Mapped[str] = mapped_column(String(30), nullable=False)  # TP1/TP2/TP3/SL/EXPIRED
    pnl_r: Mapped[Optional[float]] = mapped_column(Float)           # In R multiples
    pnl_pct: Mapped[Optional[float]] = mapped_column(Float)
    mfe: Mapped[Optional[float]] = mapped_column(Float)             # Max Favorable Excursion
    mae: Mapped[Optional[float]] = mapped_column(Float)             # Max Adverse Excursion
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    exit_price: Mapped[Optional[float]] = mapped_column(Numeric(20, 8))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


# ─────────────────────────────────────────────
# 13. Paper Positions
# ─────────────────────────────────────────────

class PaperPosition(Base):
    __tablename__ = "paper_positions"
    __table_args__ = (
        Index("ix_paper_positions_symbol_status", "symbol", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    signal_id: Mapped[str] = mapped_column(String(50), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    entry_price: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    qty: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    stop_loss: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    take_profit_1: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    take_profit_2: Mapped[Optional[float]] = mapped_column(Numeric(20, 8))
    take_profit_3: Mapped[Optional[float]] = mapped_column(Numeric(20, 8))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")
    unrealized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    fees_paid: Mapped[float] = mapped_column(Float, default=0.0)
    opened_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)


# ─────────────────────────────────────────────
# 14. Live Positions
# ─────────────────────────────────────────────

class LivePosition(Base):
    __tablename__ = "live_positions"
    __table_args__ = (
        Index("ix_live_positions_symbol_status", "symbol", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    signal_id: Mapped[str] = mapped_column(String(50), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    bybit_order_id: Mapped[Optional[str]] = mapped_column(String(100))
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    entry_price: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    qty: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    stop_loss: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    take_profit_1: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    take_profit_2: Mapped[Optional[float]] = mapped_column(Numeric(20, 8))
    take_profit_3: Mapped[Optional[float]] = mapped_column(Numeric(20, 8))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    fees_paid: Mapped[float] = mapped_column(Float, default=0.0)
    opened_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)


# ─────────────────────────────────────────────
# 15. Trading Journal
# ─────────────────────────────────────────────

class TradingJournal(Base):
    __tablename__ = "trading_journal"
    __table_args__ = (
        Index("ix_journal_symbol_ts", "symbol", "timestamp"),
        Index("ix_journal_signal_id", "signal_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    signal_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    entry_price: Mapped[Optional[float]] = mapped_column(Numeric(20, 8))
    stop_loss: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    take_profit_1: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    take_profit_2: Mapped[Optional[float]] = mapped_column(Numeric(20, 8))
    take_profit_3: Mapped[Optional[float]] = mapped_column(Numeric(20, 8))
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    model_agreement: Mapped[float] = mapped_column(Float, nullable=False)
    regime: Mapped[Optional[str]] = mapped_column(String(30))
    model_predictions: Mapped[Optional[dict]] = mapped_column(JSON)
    ensemble_weights: Mapped[Optional[dict]] = mapped_column(JSON)
    features_snapshot: Mapped[Optional[dict]] = mapped_column(JSON)
    prediction_horizon: Mapped[Optional[int]] = mapped_column(Integer)
    outcome: Mapped[Optional[str]] = mapped_column(String(30))
    pnl_r: Mapped[Optional[float]] = mapped_column(Float)
    pnl_pct: Mapped[Optional[float]] = mapped_column(Float)
    mfe: Mapped[Optional[float]] = mapped_column(Float)
    mae: Mapped[Optional[float]] = mapped_column(Float)
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    trading_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="paper")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)


# ─────────────────────────────────────────────
# 16. Backtest Results
# ─────────────────────────────────────────────

class BacktestResult(Base):
    __tablename__ = "backtest_results"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    model_name: Mapped[str] = mapped_column(String(50), nullable=False)
    model_version: Mapped[str] = mapped_column(String(20), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    total_signals: Mapped[int] = mapped_column(Integer, nullable=False)
    wins: Mapped[int] = mapped_column(Integer, nullable=False)
    losses: Mapped[int] = mapped_column(Integer, nullable=False)
    win_rate: Mapped[float] = mapped_column(Float, nullable=False)
    profit_factor: Mapped[Optional[float]] = mapped_column(Float)
    expectancy: Mapped[Optional[float]] = mapped_column(Float)
    sharpe: Mapped[Optional[float]] = mapped_column(Float)
    max_drawdown: Mapped[Optional[float]] = mapped_column(Float)
    total_pnl_r: Mapped[Optional[float]] = mapped_column(Float)
    config: Mapped[Optional[dict]] = mapped_column(JSON)
    trades: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


# ─────────────────────────────────────────────
# 17. Training Runs
# ─────────────────────────────────────────────

class TrainingRun(Base):
    __tablename__ = "training_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    model_name: Mapped[str] = mapped_column(String(50), nullable=False)
    trigger: Mapped[str] = mapped_column(String(50), nullable=False)  # scheduled/drift/manual
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="RUNNING")
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    samples_used: Mapped[Optional[int]] = mapped_column(Integer)
    champion_version: Mapped[Optional[str]] = mapped_column(String(20))
    challenger_version: Mapped[Optional[str]] = mapped_column(String(20))
    promoted: Mapped[bool] = mapped_column(Boolean, default=False)
    metrics: Mapped[Optional[dict]] = mapped_column(JSON)
    error: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


# ─────────────────────────────────────────────
# 18. Data Drift Events
# ─────────────────────────────────────────────

class DataDriftEvent(Base):
    __tablename__ = "data_drift_events"
    __table_args__ = (
        Index("ix_drift_symbol_ts", "symbol", "detected_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    drift_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # LOW/MEDIUM/HIGH
    details: Mapped[Optional[dict]] = mapped_column(JSON)
    action_taken: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


# ─────────────────────────────────────────────
# 19. Risk Events
# ─────────────────────────────────────────────

class RiskEvent(Base):
    __tablename__ = "risk_events"
    __table_args__ = (
        Index("ix_risk_events_ts", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[Optional[dict]] = mapped_column(JSON)
    action_taken: Mapped[Optional[str]] = mapped_column(String(200))
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


# ─────────────────────────────────────────────
# 20. System Events
# ─────────────────────────────────────────────

class SystemEvent(Base):
    __tablename__ = "system_events"
    __table_args__ = (
        Index("ix_system_events_ts", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    service: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
