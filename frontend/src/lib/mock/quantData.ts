import { Candle, OrderBook, SymbolName, Ticker, Timeframe } from '../../types/market';
import { Signal } from '../../types/signal';
import { ModelInfo, DriftMetric, RegimeStatus, OptunaTrial } from '../../types/model';
import { RiskStatus } from '../../types/risk';
import { BacktestResult, BacktestTrade, MonthlyReturn, EquityPoint } from '../../types/backtest';
import { Position, JournalTrade } from '../../types/position';
import { QUANT_MODELS_ROSTER, evaluateRealSignal, runQuantBacktestOnRealCandles } from '../quant/engine';

export const QUANT_MODELS: ModelInfo[] = QUANT_MODELS_ROSTER;

export const INITIAL_TICKERS: Record<SymbolName, Ticker> = {
  BTCUSDT: {
    symbol: 'BTCUSDT',
    price: 0,
    change24h: 0,
    change24hAmount: 0,
    high24h: 0,
    low24h: 0,
    volume24hUsd: 0,
    turnover24h: 0,
    timestamp: new Date().toISOString(),
  },
  XAUUSDT: {
    symbol: 'XAUUSDT',
    price: 0,
    change24h: 0,
    change24hAmount: 0,
    high24h: 0,
    low24h: 0,
    volume24hUsd: 0,
    turnover24h: 0,
    timestamp: new Date().toISOString(),
  },
};

export const INITIAL_SIGNALS: Signal[] = [];

export const INITIAL_POSITIONS: Position[] = [];

export const INITIAL_JOURNAL: JournalTrade[] = [];

export const INITIAL_REGIME: RegimeStatus = {
  currentRegime: 'BULL_TRENDING',
  probability: 87.4,
  adx: 31.4,
  volatilityState: 'NORMAL',
  durationHours: 14,
  durationMinutes: 32,
  transitionProbabilities: {
    BULL_TRENDING: 0.78,
    BEAR_TRENDING: 0.06,
    RANGING: 0.12,
    HIGH_VOLATILITY: 0.04,
  },
  regimeHistory: [],
};

export const INITIAL_RISK: RiskStatus = {
  accountEquity: 25000.00,
  initialBalance: 25000.00,
  availableMargin: 25000.00,
  usedMargin: 0,
  marginUsagePct: 0,
  dailyLossUsd: 0,
  dailyLossLimitUsd: 750.00,
  dailyLossPct: 0,
  dailyLossLimitPct: 3.00,
  weeklyDrawdownPct: 0,
  weeklyDrawdownLimitPct: 6.00,
  maxDrawdownPct: 0,
  openPositionsCount: 0,
  maxOpenPositions: 3,
  riskPerTradePct: 1.0,
  consecutiveLosses: 0,
  maxConsecutiveLosses: 5,
  killSwitchActive: false,
  tradingPaused: false,
  circuitBreakers: [
    { id: 'cb-1', name: 'Max Daily Loss (3.0%)', condition: 'Daily Loss >= 3.0%', currentValue: '0.00%', threshold: '3.00%', status: 'SAFE' },
    { id: 'cb-2', name: 'Weekly Drawdown (6.0%)', condition: 'Weekly DD >= 6.0%', currentValue: '0.00%', threshold: '6.00%', status: 'SAFE' },
    { id: 'cb-3', name: 'Max Open Positions', condition: 'Active Count >= 3', currentValue: '0 / 3', threshold: '3', status: 'SAFE' },
    { id: 'cb-4', name: 'Consecutive Loss Limit', condition: 'Losses >= 5', currentValue: '0 / 5', threshold: '5', status: 'SAFE' },
    { id: 'cb-5', name: 'Extreme Volatility Halt', condition: 'Regime = HIGH_VOL & ATR > 4x', currentValue: 'NORMAL (1.0x)', threshold: '4.0x', status: 'SAFE' },
  ],
};

export const INITIAL_DRIFT: DriftMetric[] = [
  { featureName: 'ORDERBOOK_IMBALANCE', psi: 0.082, ksStatistic: 0.061, pValue: 0.42, status: 'NORMAL', meanBaseline: 0.04, meanCurrent: 0.06, stdBaseline: 0.28, stdCurrent: 0.29, lastUpdated: 'Real-time' },
  { featureName: 'FUNDING_RATE', psi: 0.115, ksStatistic: 0.092, pValue: 0.28, status: 'NORMAL', meanBaseline: 0.00010, meanCurrent: 0.00012, stdBaseline: 0.00008, stdCurrent: 0.00010, lastUpdated: 'Real-time' },
  { featureName: 'CVD_CHANGE_15M', psi: 0.045, ksStatistic: 0.038, pValue: 0.68, status: 'NORMAL', meanBaseline: 850000, meanCurrent: 920000, stdBaseline: 420000, stdCurrent: 450000, lastUpdated: 'Real-time' },
  { featureName: 'OPEN_INTEREST_DELTA', psi: 0.132, ksStatistic: 0.089, pValue: 0.19, status: 'NORMAL', meanBaseline: 0.012, meanCurrent: 0.018, stdBaseline: 0.022, stdCurrent: 0.025, lastUpdated: 'Real-time' },
  { featureName: 'ADX_14', psi: 0.092, ksStatistic: 0.075, pValue: 0.35, status: 'NORMAL', meanBaseline: 26.5, meanCurrent: 31.4, stdBaseline: 8.4, stdCurrent: 7.9, lastUpdated: 'Real-time' },
  { featureName: 'ATR_14', psi: 0.068, ksStatistic: 0.054, pValue: 0.52, status: 'NORMAL', meanBaseline: 340.2, meanCurrent: 362.5, stdBaseline: 75.0, stdCurrent: 82.0, lastUpdated: 'Real-time' },
];

export const INITIAL_OPTUNA_TRIALS: OptunaTrial[] = [
  { trialNumber: 42, value: 2.14, params: { max_depth: 6, lr: 0.028, n_est: 400, subsample: 0.88 }, state: 'COMPLETE', durationSeconds: 142 },
  { trialNumber: 41, value: 1.98, params: { max_depth: 5, lr: 0.035, n_est: 350, subsample: 0.82 }, state: 'COMPLETE', durationSeconds: 118 },
  { trialNumber: 40, value: 2.05, params: { max_depth: 7, lr: 0.021, n_est: 450, subsample: 0.90 }, state: 'COMPLETE', durationSeconds: 165 },
];

export function generateRealisticCandles(
  symbol: SymbolName = 'BTCUSDT',
  timeframe: Timeframe = '15m',
  count: number = 180
): Candle[] {
  return [];
}

export function generateRealisticOrderBook(symbol: SymbolName = 'BTCUSDT', price?: number): OrderBook {
  return {
    symbol,
    timestamp: new Date().toISOString(),
    bids: [],
    asks: [],
    spread: 0,
    spreadBps: 0,
    midPrice: 0,
    imbalance: 0,
  };
}

export function generateAlphaEngineBacktest(): BacktestResult {
  return runQuantBacktestOnRealCandles([], {
    symbol: 'BTCUSDT',
    timeframe: '15m',
    strategy: 'AI Ensemble',
    startDate: '2025-01-01',
    endDate: new Date().toISOString().split('T')[0],
    initialCapital: 10000,
    riskPerTrade: 0.01,
    feePct: 0.055,
    slippagePct: 0.02,
    confidenceThreshold: 0.75,
    minAgreement: 0.70,
  });
}
