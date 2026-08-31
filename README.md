# EcoTrade — AI Crypto Trading Intelligence Platform

A production-grade, self-evaluating quantitative crypto trading intelligence platform using **Bybit** as the exclusive market-data and trading provider.

---

## 🏛️ System Architecture

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

## 🚀 Key Features

- **Exchange Layer (Bybit v5)**: REST API & WebSocket managers with automatic reconnection, heartbeats, exponential backoff, rate limiting, and historical data pagination.
- **Feature Engineering Pipeline**: 5 specialized feature layers (Technical Indicators, Statistical Properties, Derivatives/Funding/OI, Order Book dynamics) with zero lookahead bias guarantees.
- **Multi-Signal Market Regime Detection**: ADX, EMA structure, rolling volatility, momentum, and Gaussian Mixture Models (GMM) to identify Bull, Bear, Range, and High-Volatility regimes.
- **10 Machine Learning & Statistical Models**:
  - **Tree Models**: XGBoost (with SHAP values), LightGBM, Random Forest
  - **Deep Learning**: LSTM, GRU, Transformer with temporal multi-head attention
  - **Statistical / Volatility**: ARIMA, GARCH(1,1), Logistic Regression
  - **Benchmark**: Rule-based Technical baseline
- **Self-Learning & Continuous Improvement**:
  - Automated hyperparameter optimization via **Optuna**
  - Chronological **Walk-Forward Validation** (expanding and rolling windows)
  - **Champion vs. Challenger** model promotion gate
  - **Data & Model Drift Detection** using Population Stability Index (PSI) and Kolmogorov-Smirnov (KS) tests
- **Risk Management & Execution**:
  - Hard Kill-Switch & Circuit Breakers
  - Daily/Weekly loss limits and max drawdown guards
  - ATR-based dynamic position sizing
  - Paper trading simulation with realistic Taker/Maker fees (0.055%/0.02%) and slippage (0.02%)
  - Safe Live Trading guard requiring double confirmation (`TRADING_MODE=live` + `LIVE_EXECUTION_ENABLED=true`)
- **Telegram Interface**: 13 interactive commands (`/status`, `/signal`, `/models`, `/journal`, `/risk`, `/pause`, `/resume`, etc.) with rich HTML signal formatting.

---

## 📂 Project Structure

```text
ecotrade/
├── app/
│   ├── api/             # FastAPI routers & endpoints
│   ├── backtest/        # Event-driven backtester & walk-forward optimizer
│   ├── core/            # Config, security, logging, constants
│   ├── database/        # 20 SQLAlchemy models, session, repositories
│   ├── ensemble/        # Dynamic weighting, MTF consensus, ensemble engine
│   ├── exchange/bybit/  # Bybit v5 REST client, WebSocket manager, parser
│   ├── execution/       # Paper & Live execution engines
│   ├── features/        # Technical, statistical, derivatives, orderbook features
│   ├── models/          # 10 ML/statistical models + retrainer
│   ├── monitoring/      # PSI & KS-test data/model drift detector
│   ├── prediction/      # Multi-horizon labeling & simulation
│   ├── regime/          # Multi-signal market regime detector
│   ├── risk/            # Central risk controller & kill switch
│   ├── strategy/        # Entry zones, SL, TP, signal engine
│   ├── tasks/           # Celery background tasks & beat schedules
│   ├── telegram/        # Telegram bot, command handlers, formatters
│   └── main.py          # FastAPI application factory & lifespan
├── alembic/             # Database migration scripts
├── tests/               # Unit, integration, and backtest test suites
├── docker-compose.yml   # Full container stack (TimescaleDB, Redis, API, Workers, Flower)
├── Dockerfile           # Production container definition
├── pyproject.toml       # Python package specification
└── requirements.txt     # Locked production dependencies
```

---

## 🛠️ Quickstart & Setup

### 1. Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Bybit API Key (Testnet or Mainnet)
- Telegram Bot Token & Chat ID

### 2. Configure Environment
Copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```

### 3. Run with Docker Compose
Start the complete cluster (API, Database, Redis, Celery Workers, Celery Beat, Flower):
```bash
docker compose up -d --build
```

Access services:
- **FastAPI Interactive Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Celery Flower Dashboard**: [http://localhost:5555](http://localhost:5555)

---

## 🧪 Testing

Run the test suite:
```bash
pytest tests/ -v
```

---

## ⚠️ Risk Disclaimer

*This software is for educational, research, and algorithmic quantitative decision-support purposes only. Cryptocurrency trading involves substantial risk of loss. Past performance or backtested results are not indicative of future returns.*
