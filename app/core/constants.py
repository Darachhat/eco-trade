"""
app/core/constants.py
─────────────────────
All project-wide enumerations and constants.
No secrets, no config values — purely structural.
"""

from enum import Enum, StrEnum


# ─────────────────────────────────────────────
# Trading Mode
# ─────────────────────────────────────────────

class TradingMode(StrEnum):
    BACKTEST = "backtest"
    PAPER = "paper"
    LIVE = "live"


# ─────────────────────────────────────────────
# Market Category (Bybit)
# ─────────────────────────────────────────────

class MarketCategory(StrEnum):
    LINEAR = "linear"
    INVERSE = "inverse"
    SPOT = "spot"
    OPTION = "option"


# ─────────────────────────────────────────────
# Timeframes
# ─────────────────────────────────────────────

class Timeframe(StrEnum):
    M1 = "1"       # Bybit uses numeric strings for REST
    M5 = "5"
    M15 = "15"
    M30 = "30"
    H1 = "60"
    H4 = "240"
    D1 = "D"

    @property
    def display(self) -> str:
        _map = {
            "1": "1m", "5": "5m", "15": "15m", "30": "30m",
            "60": "1h", "240": "4h", "D": "1d",
        }
        return _map[self.value]

    @property
    def minutes(self) -> int:
        _map = {"1": 1, "5": 5, "15": 15, "30": 30, "60": 60, "240": 240, "D": 1440}
        return _map[self.value]


PREDICTION_TIMEFRAMES: list[Timeframe] = [
    Timeframe.M5,
    Timeframe.M15,
    Timeframe.H1,
    Timeframe.H4,
]

ALL_TIMEFRAMES: list[Timeframe] = [
    Timeframe.M1,
    Timeframe.M5,
    Timeframe.M15,
    Timeframe.M30,
    Timeframe.H1,
    Timeframe.H4,
    Timeframe.D1,
]


# ─────────────────────────────────────────────
# Signal Direction
# ─────────────────────────────────────────────

class SignalDirection(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"
    NO_TRADE = "NO_TRADE"
    WAIT = "WAIT"


# ─────────────────────────────────────────────
# Signal Lifecycle
# ─────────────────────────────────────────────

class SignalLifecycle(StrEnum):
    GENERATED = "GENERATED"
    ENTRY_PENDING = "ENTRY_PENDING"
    ENTERED = "ENTERED"
    TP1 = "TP1"
    TP2 = "TP2"
    TP3 = "TP3"
    CLOSED = "CLOSED"
    STOPPED_OUT = "STOPPED_OUT"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


# ─────────────────────────────────────────────
# Market Regime
# ─────────────────────────────────────────────

class MarketRegime(StrEnum):
    STRONG_BULL = "STRONG_BULL"
    BULL = "BULL"
    RANGE = "RANGE"
    BEAR = "BEAR"
    STRONG_BEAR = "STRONG_BEAR"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"
    UNCERTAIN = "UNCERTAIN"


# ─────────────────────────────────────────────
# Model Status (Registry)
# ─────────────────────────────────────────────

class ModelStatus(StrEnum):
    TRAINING = "TRAINING"
    CANDIDATE = "CANDIDATE"
    CHAMPION = "CHAMPION"
    RETIRED = "RETIRED"
    FAILED = "FAILED"


# ─────────────────────────────────────────────
# Model Names
# ─────────────────────────────────────────────

class ModelName(StrEnum):
    LOGISTIC = "logistic"
    RANDOM_FOREST = "random_forest"
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"
    LSTM = "lstm"
    GRU = "gru"
    TRANSFORMER = "transformer"
    ARIMA = "arima"
    GARCH = "garch"
    TECHNICAL = "technical"


# ─────────────────────────────────────────────
# Prediction Labels
# ─────────────────────────────────────────────

class PredictionLabel(StrEnum):
    LONG_SUCCESS = "LONG_SUCCESS"
    SHORT_SUCCESS = "SHORT_SUCCESS"
    NO_TRADE = "NO_TRADE"


# ─────────────────────────────────────────────
# Entry Types
# ─────────────────────────────────────────────

class EntryType(StrEnum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    BREAKOUT = "BREAKOUT"
    PULLBACK = "PULLBACK"


# ─────────────────────────────────────────────
# WebSocket Channels (Bybit)
# ─────────────────────────────────────────────

class BybitWSChannel(StrEnum):
    KLINE = "kline"
    ORDERBOOK = "orderbook"
    TRADE = "publicTrade"
    TICKER = "tickers"
    LIQUIDATION = "liquidation"


# ─────────────────────────────────────────────
# Celery Queues
# ─────────────────────────────────────────────

class CeleryQueue(StrEnum):
    MARKET = "market"
    PREDICTION = "prediction"
    TRAINING = "training"
    BACKTEST = "backtest"
    NOTIFICATION = "notification"
    MAINTENANCE = "maintenance"


# ─────────────────────────────────────────────
# Risk Event Types
# ─────────────────────────────────────────────

class RiskEventType(StrEnum):
    DAILY_LOSS_LIMIT = "DAILY_LOSS_LIMIT"
    WEEKLY_LOSS_LIMIT = "WEEKLY_LOSS_LIMIT"
    MAX_DRAWDOWN = "MAX_DRAWDOWN"
    CONSECUTIVE_LOSSES = "CONSECUTIVE_LOSSES"
    MAX_POSITIONS = "MAX_POSITIONS"
    CORRELATION_LIMIT = "CORRELATION_LIMIT"
    KILL_SWITCH = "KILL_SWITCH"


# ─────────────────────────────────────────────
# Misc
# ─────────────────────────────────────────────

BYBIT_REST_MAINNET = "https://api.bybit.com"
BYBIT_REST_TESTNET = "https://api-testnet.bybit.com"
BYBIT_WS_MAINNET = "wss://stream.bybit.com/v5/public"
BYBIT_WS_TESTNET = "wss://stream-testnet.bybit.com/v5/public"
BYBIT_WS_PRIVATE_MAINNET = "wss://stream.bybit.com/v5/private"
BYBIT_WS_PRIVATE_TESTNET = "wss://stream-testnet.bybit.com/v5/private"

FEATURE_VERSION = "v1"

MAX_CANDLES_PER_REQUEST = 200  # Bybit limit per REST call

LOOKBACK_SEQUENCE = 60  # Candles for LSTM/GRU/Transformer input
