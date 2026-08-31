# Build a Production-Grade AI Crypto Trader — Bybit + Multi-Model Prediction + Self-Learning + Telegram

Act as a **Senior Quantitative Developer, Algorithmic Trader, Data Scientist, Machine Learning Engineer, Backend Engineer, MLOps Engineer, and Software Architect**.

I want to build a production-grade **AI Crypto Trading Intelligence Platform** using **Bybit as the ONLY market-data and trading exchange**.

The system must consume real-time Bybit market data, analyze multiple timeframes, compare multiple machine-learning and statistical models, generate probabilistic LONG/SHORT/NO-TRADE decisions, calculate entry/SL/TP, send signals to Telegram, track every prediction, evaluate model performance, and continuously improve through validated retraining.

Do NOT build a simple indicator bot.

Build a **self-evaluating quantitative decision-support system**.

---

# 1. Primary Objective

Build this pipeline:

```text
                         BYBIT
                           │
             ┌─────────────┴─────────────┐
             │                           │
        REST API                    WebSocket
             │                           │
      Historical Data             Real-Time Data
             │                           │
             └─────────────┬─────────────┘
                           ↓
                    Data Processing
                           ↓
                    Feature Engine
                           ↓
                 Market Regime Engine
                           ↓
                 Multi-Timeframe Engine
                           ↓
        ┌──────────────────┼──────────────────┐
        ↓                  ↓                  ↓
     XGBoost              LSTM          Transformer
        ↓                  ↓                  ↓
   Random Forest       Statistical      Technical
        └──────────────────┼──────────────────┘
                           ↓
                    Model Comparison
                           ↓
                    Ensemble Engine
                           ↓
                    Confidence Score
                           ↓
                     Risk Engine
                           ↓
              LONG / SHORT / NO TRADE
                           ↓
                    Signal Generator
                           ↓
                       Telegram
                           ↓
                   Trading Journal
                           ↓
                  Outcome Evaluation
                           ↓
                Model Performance Store
                           ↓
                 Retraining / Champion
                     vs Challenger
```

---

# 2. Exchange — ONLY Bybit

Do NOT use:

* Binance
* TwelveData
* Alpha Vantage
* Polygon
* MT5
* Other exchanges

Bybit is the only external market-data and trading provider.

Use the Bybit API architecture in a modular way so the system can later support additional providers without rewriting the core system.

Use:

```text
Bybit REST API
Bybit WebSocket API
```

Support:

* Historical candles
* Real-time candles
* Trades
* Ticker
* Bid/Ask
* Order book
* Funding rate
* Open interest
* Mark price
* Index price
* Liquidation information where available

Prioritize WebSocket for real-time processing.

---

# 3. Initial Trading Markets

Start with:

```text
BTCUSDT
ETHUSDT
SOLUSDT
XRPUSDT
```

Make symbols configurable.

Example:

```env
BYBIT_SYMBOLS=BTCUSDT,ETHUSDT,SOLUSDT,XRPUSDT
```

The architecture must support adding symbols without changing application code.

---

# 4. Market Type

Initially use:

```env
BYBIT_CATEGORY=linear
```

Design the code so category can later support:

```text
spot
linear
inverse
option
```

Do not mix different market types accidentally.

---

# 5. Trading Mode

Implement three modes:

```text
BACKTEST
PAPER
LIVE
```

Default:

```env
TRADING_MODE=paper
```

The system must NOT execute real trades unless:

```env
TRADING_MODE=live
```

and an explicit execution configuration is enabled.

Separate:

```text
Market Data
Signal Generation
Paper Trading
Live Execution
```

so live execution cannot accidentally occur during testing.

---

# 6. Environment Variables

Create a `.env.example`.

Required variables:

```env
# =========================
# APPLICATION
# =========================

APP_NAME=ai_crypto_trader
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO

APP_SECRET_KEY=

# =========================
# BYBIT
# =========================

BYBIT_API_KEY=
BYBIT_API_SECRET=

BYBIT_TESTNET=true
BYBIT_CATEGORY=linear

BYBIT_SYMBOLS=BTCUSDT,ETHUSDT,SOLUSDT,XRPUSDT

# =========================
# TELEGRAM
# =========================

TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
TELEGRAM_ADMIN_CHAT_ID=

# =========================
# DATABASE
# =========================

POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=ai_trader
POSTGRES_USER=
POSTGRES_PASSWORD=
DATABASE_URL=

# =========================
# REDIS
# =========================

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

REDIS_URL=

# =========================
# CELERY
# =========================

CELERY_BROKER_URL=
CELERY_RESULT_BACKEND=

# =========================
# ML
# =========================

ML_MODEL_PATH=/models
ML_ARTIFACT_PATH=/artifacts
MLFLOW_TRACKING_URI=

# =========================
# PREDICTION
# =========================

PREDICTION_HORIZONS=5,10,20,50

MIN_CONFIDENCE=0.75
MIN_MODEL_AGREEMENT=0.70
MIN_RISK_REWARD=2.0

# =========================
# RISK
# =========================

RISK_PER_TRADE=0.01
MAX_DAILY_LOSS=0.03
MAX_OPEN_POSITIONS=3
MAX_CONSECUTIVE_LOSSES=5

# =========================
# SELF LEARNING
# =========================

RETRAIN_ENABLED=true
RETRAIN_INTERVAL_HOURS=24

MIN_TRAINING_SAMPLES=10000

MODEL_PERFORMANCE_WINDOW=100

CHALLENGER_ENABLED=true
```

Never hard-code secrets.

Never commit `.env`.

Create:

```text
.env
.env.example
.gitignore
```

---

# 7. Real-Time Bybit Data Engine

Build a robust WebSocket manager.

Responsibilities:

```text
Connect
Authenticate
Subscribe
Receive
Validate
Normalize
Store
Reconnect
Resubscribe
Heartbeat
Handle errors
```

Implement automatic reconnect.

If connection is lost:

```text
Disconnect
    ↓
Backoff
    ↓
Reconnect
    ↓
Re-authenticate
    ↓
Resubscribe
    ↓
Continue
```

Do not silently lose data.

Log connection state.

---

# 8. Data Pipeline

Build:

```text
Bybit WebSocket
        ↓
Raw Event
        ↓
Validator
        ↓
Normalizer
        ↓
Redis Stream
        ↓
Feature Processor
        ↓
ML Pipeline
```

Use Redis for low-latency communication.

PostgreSQL should be the persistent source of truth.

---

# 9. Historical Data

Build a historical data downloader.

Requirements:

* Download candles
* Store raw data
* Detect missing periods
* Prevent duplicates
* Support incremental updates
* Validate timestamps
* Store exchange timestamps
* Store ingestion timestamps

Example:

```text
2024
2025
2026
```

Do not train using incomplete or corrupted datasets.

---

# 10. Timeframes

Support:

```text
1m
5m
15m
30m
1h
4h
1d
```

Primary prediction timeframes:

```text
5m
15m
1h
4h
```

Use higher timeframes to determine context and lower timeframes to determine entry.

Example:

```text
4H → Market Regime
1H → Trend
15M → Setup
5M → Entry
```

---

# 11. Feature Engineering

Build a reusable feature-engineering framework.

Technical indicators:

```text
EMA
SMA
RSI
MACD
ATR
ADX
Bollinger Bands
Stochastic
VWAP
Ichimoku
Donchian Channels
ROC
Momentum
OBV
Volume
```

Price-action features:

```text
Returns
Log returns
Candle body
Upper wick
Lower wick
Candle range
High/low distance
Breakout
Breakdown
Swing highs
Swing lows
Support
Resistance
Market structure
```

Volatility features:

```text
ATR
Realized volatility
Rolling standard deviation
Volatility percentile
Volatility regime
```

Statistical features:

```text
Rolling mean
Rolling median
Z-score
Autocorrelation
Skewness
Kurtosis
Return distribution
Momentum persistence
Mean-reversion score
```

Order-book features:

```text
Bid volume
Ask volume
Bid/ask imbalance
Spread
Depth
Order-book pressure
```

Derivatives features:

```text
Funding rate
Open interest
Open-interest change
Price/OI relationship
Funding/price relationship
```

All features must be timestamp-safe.

No future information may enter a feature.

---

# 12. Feature Store

Create a feature storage layer.

Example:

```text
features
```

Columns:

```text
id
symbol
timeframe
timestamp
feature_name
feature_value
feature_version
created_at
```

Alternatively use a wide feature table if more efficient.

Version the feature pipeline.

Example:

```text
feature_version = v1
feature_version = v2
```

---

# 13. Market Regime Detection

Create a Market Regime Engine.

Possible regimes:

```text
STRONG_BULL
BULL
RANGE
BEAR
STRONG_BEAR
HIGH_VOLATILITY
LOW_VOLATILITY
UNCERTAIN
```

Use:

```text
ADX
EMA structure
volatility
returns
HMM
clustering
GMM
```

Do not depend on one indicator.

The regime engine should produce:

```json
{
  "regime": "BULL",
  "confidence": 0.84
}
```

---

# 14. Prediction Target

Do NOT train the AI only to predict:

```text
next candle UP/DOWN
```

Instead define trading-oriented labels.

Example:

```text
LONG_SUCCESS
SHORT_SUCCESS
NO_TRADE
```

For a hypothetical setup:

```text
Entry
Stop Loss
Take Profit
Prediction Horizon
```

Label whether:

```text
TP reached before SL
SL reached before TP
Neither reached
```

Create multiple prediction horizons:

```text
5 candles
10 candles
20 candles
50 candles
```

This should make the model optimize for useful trading outcomes rather than meaningless candle-direction accuracy.

---

# 15. Machine Learning Models

Implement multiple independent models.

## Model 1 — Logistic Regression

Baseline model.

Purpose:

```text
Simple interpretable baseline
```

---

## Model 2 — Random Forest

Use structured technical and market features.

Output:

```text
LONG probability
SHORT probability
NO TRADE probability
```

---

## Model 3 — XGBoost

Primary tabular ML model.

Use:

```text
Technical
Statistical
Volatility
Order-book
Derivatives
Market-regime
Multi-timeframe
```

---

## Model 4 — LightGBM

Use as an additional gradient boosting challenger.

---

## Model 5 — LSTM

Use sequences of historical feature vectors.

Example:

```text
last 60 candles
→ LSTM
→ future outcome probability
```

---

## Model 6 — GRU

Alternative sequential model.

---

## Model 7 — Transformer

Use temporal attention to capture longer relationships.

---

## Model 8 — Statistical Models

Implement:

```text
ARIMA
GARCH
Kalman Filter
```

These are supporting models, not automatically superior to ML models.

---

## Model 9 — Rule-Based Baseline

Create a transparent baseline strategy.

Example:

```text
EMA trend
+
RSI
+
MACD
+
ADX
+
support/resistance
```

Use it as a benchmark against AI models.

---

# 16. Model Output

Every model must return a standardized structure.

Example:

```json
{
  "model": "xgboost",
  "version": "v12",
  "symbol": "BTCUSDT",
  "timeframe": "15m",
  "prediction": "LONG",
  "probability_long": 0.81,
  "probability_short": 0.12,
  "probability_no_trade": 0.07,
  "timestamp": "..."
}
```

All models must use the same interface.

---

# 17. Model Comparison Engine

At every prediction cycle:

```text
XGBoost
Random Forest
LightGBM
LSTM
GRU
Transformer
ARIMA
GARCH
Technical Strategy
```

Run predictions independently.

Create:

```text
Model
Prediction
Probability
Historical Accuracy
Historical Win Rate
Profit Factor
Current Regime Performance
Current Timeframe Performance
```

Example:

```text
XGBoost       LONG   81%
LightGBM      LONG   79%
Transformer   LONG   84%
LSTM          LONG   76%
GRU           SHORT  54%
ARIMA         LONG   62%
Technical     LONG   78%
```

---

# 18. Dynamic Ensemble

Do not simply average all models.

Calculate dynamic weights.

Weight models based on:

```text
Recent performance
Long-term performance
Current market regime
Current timeframe
Asset-specific performance
Calibration
Drawdown
```

Example:

```text
XGBoost       25%
Transformer   25%
LightGBM      15%
LSTM          12%
RandomForest  10%
Statistical    8%
Technical      5%
```

Normalize weights so:

```text
sum(weights) = 1
```

---

# 19. Model Disagreement

Calculate disagreement.

Example:

```text
8 models

6 LONG
1 SHORT
1 NO TRADE
```

Agreement:

```text
75%
```

If disagreement is high:

```text
NO TRADE
```

Do not force a prediction.

---

# 20. Multi-Timeframe Consensus

Example:

```text
4H → LONG
1H → LONG
15M → LONG
5M → LONG
```

Strong confirmation.

But:

```text
4H → LONG
1H → LONG
15M → SHORT
5M → SHORT
```

should reduce confidence or produce:

```text
WAIT
```

Create a configurable consensus engine.

---

# 21. Signal Engine

Possible outputs:

```text
LONG
SHORT
NO TRADE
WAIT
```

Example conditions for LONG:

```text
Ensemble probability >= 75%

AND

Model agreement >= 70%

AND

Higher timeframe trend supports LONG

AND

Market regime is suitable

AND

Risk/Reward >= 1:2

AND

Spread is acceptable

AND

No abnormal volatility

AND

No risk-limit violation
```

Otherwise:

```text
NO TRADE
```

---

# 22. Entry Zone

Do not blindly use current price.

Calculate an entry zone using:

```text
Current price
ATR
Support
Resistance
VWAP
Market structure
Liquidity
Breakout level
Pullback level
Volatility
```

Possible entry types:

```text
MARKET
LIMIT
BREAKOUT
PULLBACK
```

Example:

```text
Entry Zone:
BTC 112,400 – 112,650
```

---

# 23. Stop Loss

Calculate SL using:

```text
ATR
Market structure
Swing low/high
Volatility
```

Example:

```text
LONG

Entry: 112,500

SL: 111,800
```

SL must represent a meaningful invalidation level.

---

# 24. Take Profit

Generate:

```text
TP1
TP2
TP3
```

Use:

```text
Resistance
Liquidity
ATR
Market structure
Expected volatility
```

Example:

```text
TP1: 113,200
TP2: 114,000
TP3: 115,500
```

Calculate:

```text
Risk/Reward
Expected Value
Probability of TP
Probability of SL
```

---

# 25. Risk Management

Implement strict risk controls.

Default:

```env
RISK_PER_TRADE=0.01
MAX_DAILY_LOSS=0.03
MAX_OPEN_POSITIONS=3
MAX_CONSECUTIVE_LOSSES=5
MIN_RISK_REWARD=2.0
```

Position size:

```text
Position Size =
Account Risk / Stop Distance
```

Never increase risk merely because confidence is high.

Implement:

```text
Daily loss limit
Weekly loss limit
Maximum drawdown
Maximum correlated exposure
Maximum position size
Cooldown after losses
```

---

# 26. Correlation Risk

If signals are:

```text
BTC LONG
ETH LONG
SOL LONG
XRP LONG
```

do not treat them as four completely independent trades.

Calculate correlation.

Control total portfolio exposure.

---

# 27. Telegram Integration

Send every qualified signal to Telegram.

Format:

```text
🚨 AI CRYPTO SIGNAL

━━━━━━━━━━━━━━━━━━
ASSET
BTCUSDT

DIRECTION
🟢 LONG

ENTRY
112,400 – 112,650

STOP LOSS
111,800

TAKE PROFIT
TP1 113,200
TP2 114,000
TP3 115,500

RISK / REWARD
1 : 2.8

AI CONFIDENCE
84%

MODEL AGREEMENT
78%

MARKET REGIME
BULL

MULTI-TIMEFRAME
4H  🟢 LONG
1H   🟢 LONG
15M  🟢 LONG
5M   🟢 LONG

━━━━━━━━━━━━━━━━━━

MODEL CONSENSUS

XGBoost       LONG 81%
LightGBM      LONG 79%
Transformer   LONG 84%
LSTM          LONG 76%
GRU           LONG 73%
RandomForest  LONG 80%
ARIMA         LONG 62%

━━━━━━━━━━━━━━━━━━

REASON

Strong higher-timeframe trend,
positive momentum,
bullish market structure,
model consensus,
acceptable volatility,
and favorable risk/reward.

SIGNAL ID
AI-20260830-BTC-000001

MODE
PAPER TRADING

⚠️ Probabilistic decision-support signal.
Not guaranteed financial performance.
```

---

# 28. Telegram Commands

Implement:

```text
/start
/help
/status
/market
/signal
/models
/performance
/journal
/risk
/positions
/backtest
/pause
/resume
```

Example:

```text
/models
```

returns:

```text
AI MODEL PERFORMANCE

XGBoost
Accuracy: 64.2%
Win Rate: 61.4%
Profit Factor: 1.58

Transformer
Accuracy: 67.1%
Win Rate: 64.8%
Profit Factor: 1.73

LSTM
Accuracy: 60.1%
Win Rate: 58.9%
Profit Factor: 1.31

CURRENT CHAMPION

Transformer v18
```

---

# 29. Signal Lifecycle

Every signal receives a unique ID.

Example:

```text
AI-20260830-BTCUSDT-000001
```

Lifecycle:

```text
GENERATED
     ↓
ENTRY_PENDING
     ↓
ENTERED
     ↓
TP1
     ↓
TP2
     ↓
TP3
     ↓
CLOSED
```

or:

```text
GENERATED
     ↓
STOPPED_OUT
```

or:

```text
GENERATED
     ↓
EXPIRED
```

---

# 30. Trading Journal

Store every signal.

Required fields:

```text
signal_id
symbol
timeframe
timestamp
direction
entry
stop_loss
take_profit
confidence
model_agreement
market_regime
model_predictions
ensemble_weights
features_snapshot
prediction_horizon
outcome
PnL
MFE
MAE
duration
```

Do not delete losing trades.

Losses are important training information.

---

# 31. Prediction Evaluation

For every prediction:

```text
Prediction
     ↓
Wait
     ↓
Observe Future Market
     ↓
Determine Actual Outcome
     ↓
Compare Prediction vs Reality
```

Calculate:

```text
Prediction Error
Accuracy
Precision
Recall
F1
ROC-AUC
Brier Score
Calibration
```

For trading:

```text
Win Rate
Profit Factor
Expectancy
Sharpe
Sortino
Maximum Drawdown
Average Win
Average Loss
MFE
MAE
```

---

# 32. Self-Learning

The system must learn from historical outcomes.

Use:

```text
Prediction
    ↓
Outcome
    ↓
Performance
    ↓
Model Evaluation
    ↓
Weight Adjustment
    ↓
Candidate Retraining
    ↓
Walk-Forward Validation
    ↓
Champion/Challenger
```

Do not automatically change the live model after one bad trade.

---

# 33. Champion vs Challenger

Maintain:

```text
CHAMPION
CHALLENGER
```

Example:

```text
Champion:
XGBoost v12

Challenger:
XGBoost v13
```

A challenger can replace the champion only if it passes:

```text
Out-of-sample testing
Walk-forward testing
Performance threshold
Drawdown threshold
Statistical validation
Calibration validation
```

Never promote based solely on training accuracy.

---

# 34. Retraining

Retraining should be scheduled.

Example:

```text
Every 24 hours
```

but only promote a new model if validation proves it is better.

Trigger retraining when:

```text
Performance degradation
New data threshold reached
Market regime change
Feature distribution drift
Prediction calibration drift
```

---

# 35. Data Drift

Implement drift detection.

Monitor:

```text
Feature distribution
Prediction distribution
Market volatility
Market regime
Model confidence
Error rate
```

If significant drift occurs:

```text
FLAG MODEL
```

Do not blindly trust stale models.

---

# 36. Backtesting

Build a realistic event-driven backtesting engine.

Include:

```text
Fees
Spread
Slippage
Latency
Position sizing
Partial exits
TP
SL
Funding
```

Avoid:

```text
Look-ahead bias
Data leakage
Overfitting
Survivorship bias
```

---

# 37. Walk-Forward Validation

Use chronological validation.

Example:

```text
TRAIN
2022 → 2023

VALIDATION
2024 Q1

TEST
2024 Q2

MOVE WINDOW

TRAIN
2022 → 2024 Q1

VALIDATION
2024 Q2

TEST
2024 Q3
```

Never randomly shuffle time-series data when that introduces future information into training.

---

# 38. Hyperparameter Optimization

Use:

```text
Optuna
```

Optimize:

```text
Model parameters
Feature selection
Prediction thresholds
Ensemble weights
```

But ensure optimization occurs only on training/validation data.

Never optimize directly on the final test set.

---

# 39. Model Registry

Use MLflow or an equivalent model registry.

Store:

```text
model_name
model_version
training_dataset
feature_version
training_period
validation_period
test_period
hyperparameters
metrics
market_regimes
created_at
status
```

Statuses:

```text
TRAINING
CANDIDATE
CHAMPION
RETIRED
FAILED
```

---

# 40. Database

Use PostgreSQL.

Create tables:

```text
market_data
orderbook_snapshots
trades_market
features
market_regimes
predictions
model_predictions
model_versions
model_metrics
ensemble_weights
signals
signal_results
paper_positions
live_positions
trading_journal
backtest_results
training_runs
data_drift_events
risk_events
system_events
```

Use proper indexes.

Time-series queries must be optimized.

---

# 41. Redis

Use Redis for:

```text
Real-time market events
Pub/Sub
Streams
Caching
Celery broker
Temporary state
Rate limiting
```

Do not use Redis as the permanent source of truth.

---

# 42. Celery

Use Celery for background tasks.

Examples:

```text
historical_data_sync
feature_generation
model_prediction
signal_evaluation
journal_update
model_evaluation
model_retraining
backtest
daily_report
telegram_notification
```

Separate queues:

```text
market
prediction
training
backtest
notification
maintenance
```

---

# 43. FastAPI

Create APIs:

```text
GET /health

GET /market/{symbol}

GET /market/{symbol}/orderbook

GET /prediction/{symbol}

GET /signal/{symbol}

GET /signals

GET /models

GET /models/performance

GET /models/{model_name}

GET /portfolio

GET /positions

GET /journal

GET /backtest

POST /backtest/run

POST /models/retrain

POST /trading/pause

POST /trading/resume
```

---

# 44. WebSocket API

Create:

```text
/ws/market/{symbol}

/ws/signals

/ws/models

/ws/system
```

Real-time dashboard updates should use WebSocket.

---

# 45. Project Structure

Use clean architecture.

```text
ai_crypto_trader/
│
├── app/
│   ├── main.py
│   │
│   ├── api/
│   │   ├── routes_market.py
│   │   ├── routes_signal.py
│   │   ├── routes_models.py
│   │   ├── routes_backtest.py
│   │   └── routes_system.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── logging.py
│   │   ├── security.py
│   │   └── constants.py
│   │
│   ├── exchange/
│   │   └── bybit/
│   │       ├── client.py
│   │       ├── rest.py
│   │       ├── websocket.py
│   │       ├── parser.py
│   │       └── models.py
│   │
│   ├── market/
│   │   ├── collector.py
│   │   ├── processor.py
│   │   ├── validator.py
│   │   └── aggregator.py
│   │
│   ├── features/
│   │   ├── technical.py
│   │   ├── statistical.py
│   │   ├── orderbook.py
│   │   ├── derivatives.py
│   │   └── pipeline.py
│   │
│   ├── regime/
│   │   ├── detector.py
│   │   └── models.py
│   │
│   ├── models/
│   │   ├── base.py
│   │   ├── logistic.py
│   │   ├── random_forest.py
│   │   ├── xgboost_model.py
│   │   ├── lightgbm_model.py
│   │   ├── lstm.py
│   │   ├── gru.py
│   │   ├── transformer.py
│   │   ├── arima.py
│   │   ├── garch.py
│   │   └── technical.py
│   │
│   ├── ensemble/
│   │   ├── engine.py
│   │   ├── weighting.py
│   │   └── consensus.py
│   │
│   ├── prediction/
│   │   ├── predictor.py
│   │   ├── labels.py
│   │   └── horizons.py
│   │
│   ├── strategy/
│   │   ├── signal_engine.py
│   │   ├── entry.py
│   │   ├── stop_loss.py
│   │   └── take_profit.py
│   │
│   ├── risk/
│   │   ├── manager.py
│   │   ├── position_sizing.py
│   │   ├── exposure.py
│   │   └── limits.py
│   │
│   ├── backtest/
│   │   ├── engine.py
│   │   ├── execution.py
│   │   ├── metrics.py
│   │   └── walk_forward.py
│   │
│   ├── learning/
│   │   ├── evaluator.py
│   │   ├── retrainer.py
│   │   ├── drift.py
│   │   ├── champion.py
│   │   └── challenger.py
│   │
│   ├── telegram/
│   │   ├── bot.py
│   │   ├── commands.py
│   │   └── formatter.py
│   │
│   ├── database/
│   │   ├── models.py
│   │   ├── repositories.py
│   │   └── session.py
│   │
│   ├── tasks/
│   │   ├── market_tasks.py
│   │   ├── prediction_tasks.py
│   │   ├── training_tasks.py
│   │   ├── backtest_tasks.py
│   │   └── notification_tasks.py
│   │
│   └── schemas/
│       ├── market.py
│       ├── prediction.py
│       ├── signal.py
│       └── model.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── backtest/
│   └── ml/
│
├── models/
├── artifacts/
├── notebooks/
├── migrations/
│
├── docker/
│
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── pyproject.toml
├── .env.example
├── .gitignore
└── README.md
```

---

# 46. Technology Stack

Backend:

```text
Python
FastAPI
Pydantic
SQLAlchemy
Alembic
```

Database:

```text
PostgreSQL
```

Real-time:

```text
WebSocket
Redis Streams
```

Background processing:

```text
Celery
Redis
```

Machine Learning:

```text
NumPy
Pandas
Polars
Scikit-learn
XGBoost
LightGBM
PyTorch
Statsmodels
Optuna
MLflow
```

Infrastructure:

```text
Docker
Docker Compose
Linux
GitLab CI/CD
```

Monitoring:

```text
Prometheus
Grafana
Structured Logging
```

Notifications:

```text
Telegram Bot API
```

---

# 47. Docker Architecture

Create services:

```text
api
worker
scheduler
postgres
redis
telegram_bot
```

Optional:

```text
mlflow
prometheus
grafana
```

Example:

```text
                    Docker Network
                         │
        ┌────────────────┼─────────────────┐
        ↓                ↓                 ↓
       API             Worker            Bot
        │                │                 │
        └────────────┬───┴─────────────────┘
                     ↓
                   Redis
                     │
                     ↓
                 PostgreSQL
```

---

# 48. Logging

Use structured JSON logs.

Example:

```json
{
  "timestamp": "...",
  "service": "prediction_worker",
  "symbol": "BTCUSDT",
  "timeframe": "15m",
  "signal_id": "AI-20260830-BTC-001",
  "model": "xgboost",
  "prediction": "LONG",
  "confidence": 0.81
}
```

Separate logs:

```text
app.log
market.log
worker.log
model.log
trading.log
telegram.log
error.log
```

Implement log rotation.

---

# 49. Monitoring

Monitor:

```text
WebSocket connection
Market data latency
Data gaps
Prediction latency
Model inference latency
Telegram delivery
Redis health
PostgreSQL health
CPU
RAM
GPU
Disk
Model drift
Prediction accuracy
Signal frequency
```

Create alerts for:

```text
Bybit connection failure
Database failure
Redis failure
Model failure
Data gap
Unexpected signal spike
Risk limit
```

---

# 50. Testing

Write unit tests for:

```text
Feature calculations
Label generation
Model interface
Ensemble weighting
Confidence calculation
Entry calculation
SL calculation
TP calculation
Position sizing
Risk management
Signal generation
```

Integration tests:

```text
Bybit mock
PostgreSQL
Redis
Celery
Telegram mock
```

Backtest tests:

```text
No look-ahead
Correct SL/TP
Correct fees
Correct position sizing
Correct PnL
```

---

# 51. No Look-Ahead Bias

This is extremely important.

At timestamp:

```text
T
```

the model may only use information available at:

```text
T
```

It must NEVER use:

```text
T + 1
T + 2
...
```

when generating the prediction.

Validate this automatically in tests.

---

# 52. No Data Leakage

Ensure:

```text
Scaler
Feature Selector
PCA
Model
```

are fitted only on training data.

Do not fit preprocessing on the entire dataset before splitting.

---

# 53. Confidence Calibration

Model probability should be calibrated.

Use:

```text
Platt Scaling
Isotonic Regression
```

where appropriate.

If a model says:

```text
80% confidence
```

its historical outcomes should approximately justify that probability.

Track calibration using:

```text
Brier Score
Reliability Curve
Expected Calibration Error
```

---

# 54. AI Explainability

Every signal should explain:

```text
Why LONG?
Why SHORT?
Why NO TRADE?
```

Provide top contributing factors.

For XGBoost:

```text
Feature Importance
SHAP
```

Example:

```text
TOP FACTORS

+ Strong 1H momentum
+ Positive order-book imbalance
+ Rising open interest
+ Bullish market structure
+ Price above VWAP

Negative:

- High short-term volatility
```

Do not generate explanations that contradict the actual model.

---

# 55. Signal Quality Score

Create:

```text
Signal Quality Score
```

Example:

```text
Model Agreement      18/20
Probability          19/20
MTF Alignment        18/20
Risk/Reward          10/10
Market Regime         8/10
Liquidity              8/10

TOTAL
81/100
```

Only generate signals above a configurable threshold.

---

# 56. NO-TRADE Is a Valid Prediction

The system must be comfortable saying:

```text
NO TRADE
```

Examples:

```text
Low model agreement
High volatility
Bad R:R
Conflicting timeframes
Uncertain regime
Wide spread
Insufficient liquidity
Model drift
Risk limit reached
```

Do not force signals.

---

# 57. Paper Trading

Before live trading:

```text
Bybit Real-Time Data
        ↓
AI Signal
        ↓
Paper Position
        ↓
Track Entry
        ↓
Track SL/TP
        ↓
Calculate PnL
```

Paper trading must behave like real execution as closely as possible.

Include:

```text
Fees
Spread
Slippage
Latency
Funding
Partial TP
```

---

# 58. Live Trading

Live execution must be isolated.

Create:

```text
ExecutionEngine
```

with:

```text
PaperExecutionEngine
BybitExecutionEngine
```

Both implement the same interface.

Example:

```python
class ExecutionEngine:
    async def open_position(...):
        ...

    async def close_position(...):
        ...

    async def modify_stop_loss(...):
        ...
```

This allows paper and live systems to use the same strategy code.

---

# 59. Kill Switch

Implement a global kill switch.

If:

```text
Maximum daily loss
Maximum drawdown
Unexpected volatility
Exchange API problem
Model failure
Data corruption
```

then:

```text
STOP NEW SIGNALS
STOP LIVE EXECUTION
```

Send Telegram alert:

```text
🚨 TRADING SYSTEM HALTED

Reason:
Risk limit exceeded.

Action:
New positions disabled.

Manual review required.
```

---

# 60. Daily AI Report

Send a daily Telegram report.

Example:

```text
📊 DAILY AI TRADING REPORT

Date:
2026-08-30

Signals:
18

Wins:
11

Losses:
7

Win Rate:
61.1%

Profit Factor:
1.72

Expected Value:
+0.34R

Maximum Drawdown:
-2.1%

Best Model:
Transformer

Worst Model:
ARIMA

Current Regime:
BULL

Model Drift:
NORMAL

Champion:
Transformer v18
```

---

# 61. Weekly Model Report

Show:

```text
Model
Accuracy
Precision
Recall
F1
Win Rate
Profit Factor
Sharpe
Drawdown
Calibration
```

Compare:

```text
This Week
Last Week
Last Month
All Time
```

---

# 62. Self-Learning Loop

Implement:

```text
                  ┌───────────────┐
                  │ Real-Time Data│
                  └───────┬───────┘
                          ↓
                     Prediction
                          ↓
                       Signal
                          ↓
                    Paper Trade
                          ↓
                       Outcome
                          ↓
                  Performance Store
                          ↓
                  Model Evaluation
                          ↓
              ┌───────────┴───────────┐
              ↓                       ↓
         Model still good        Model degraded
              ↓                       ↓
          Keep model              Retrain
                                      ↓
                                Challenger
                                      ↓
                             Walk-Forward Test
                                      ↓
                             Better than Champion?
                               /             \
                             YES              NO
                              ↓                ↓
                         Promote           Reject
```

---

# 63. Important Principle

Do NOT describe the system as:

```text
AI that predicts the future.
```

Instead describe it as:

```text
A probabilistic market prediction and risk-management system
that continuously evaluates its own predictions.
```

Financial markets are stochastic and non-stationary.

The system must explicitly model uncertainty.

---

# 64. Final Deliverables

Build the project in phases.

## Phase 1

Implement:

```text
Bybit REST
Bybit WebSocket
Historical candles
Real-time candles
PostgreSQL
Redis
```

## Phase 2

Implement:

```text
Technical indicators
Feature pipeline
Market regime
Multi-timeframe processing
```

## Phase 3

Implement:

```text
Logistic Regression
Random Forest
XGBoost
LightGBM
Technical baseline
```

## Phase 4

Implement:

```text
LSTM
GRU
Transformer
ARIMA
GARCH
```

## Phase 5

Implement:

```text
Model comparison
Dynamic ensemble
Confidence
Signal engine
Entry
SL
TP
Risk
```

## Phase 6

Implement:

```text
Telegram
Paper trading
Trading journal
Signal lifecycle
```

## Phase 7

Implement:

```text
Backtesting
Walk-forward validation
Model registry
MLflow
```

## Phase 8

Implement:

```text
Self-learning
Model drift
Retraining
Champion/Challenger
```

## Phase 9

Implement:

```text
Monitoring
Prometheus
Grafana
Alerts
CI/CD
Production deployment
```

## Phase 10

Only after extensive paper trading and validation:

```text
Bybit Testnet
        ↓
Validation
        ↓
Small Live Deployment
```

Never enable live trading by default.

---

# 65. Development Rules

Follow these rules throughout the implementation:

1. Use type hints.
2. Use async I/O where appropriate.
3. Use Pydantic settings.
4. Use SQLAlchemy.
5. Use Alembic migrations.
6. Use dependency injection in FastAPI.
7. Use repository/service patterns where useful.
8. Keep exchange-specific code isolated.
9. Keep ML models behind a common interface.
10. Keep strategy independent from execution.
11. Keep paper trading independent from live trading.
12. Write tests before complex optimization.
13. Use UTC internally.
14. Store exchange timestamps.
15. Make all prediction decisions reproducible.
16. Version datasets.
17. Version features.
18. Version models.
19. Version strategies.
20. Never hard-code API credentials.
21. Never claim guaranteed profit.
22. Never use future data.
23. Never optimize directly against the final test set.
24. Prefer NO TRADE over weak signals.
25. Optimize for risk-adjusted performance rather than prediction accuracy alone.

---

# 66. First Implementation Task

Do NOT immediately implement every ML model.

Start with a working MVP:

```text
Bybit
  ↓
WebSocket
  ↓
BTCUSDT
  ↓
1m / 5m / 15m / 1h / 4h
  ↓
PostgreSQL
  ↓
Redis
  ↓
Feature Engine
  ↓
XGBoost
  ↓
Technical Baseline
  ↓
Ensemble
  ↓
Risk Engine
  ↓
Paper Signal
  ↓
Telegram
  ↓
Trading Journal
```

Then verify the entire pipeline works correctly.

After the MVP is stable, add:

```text
Random Forest
LightGBM
LSTM
GRU
Transformer
ARIMA
GARCH
```

Do not introduce unnecessary complexity before the data pipeline, labeling, backtesting and evaluation system are reliable.

---

# 67. Expected Final System

The final system should be able to answer in real time:

```text
What is BTC doing?

What is the current market regime?

What are the 5M / 15M / 1H / 4H trends?

What does each AI model predict?

Which model is currently performing best?

How much do the models agree?

What is the probability of LONG?

What is the probability of SHORT?

Is the prediction calibrated?

Where is the entry?

Where is the invalidation?

Where are TP1 / TP2 / TP3?

What is the risk/reward?

How much capital should be allocated?

How did similar historical setups perform?

Should we trade?

If not, why NO TRADE?

How accurate has this model been recently?

Is the model drifting?

Should the model be retrained?

Is the challenger better than the champion?
```

The final objective is **not to maximize the number of trades**.

The objective is to build a system that makes **fewer, higher-quality, statistically validated decisions while continuously measuring whether its predictions actually work**.

Start with the MVP and provide the implementation step-by-step, including code, database migrations, configuration, Docker setup, tests, and explanations for every major architectural decision.
