import { SymbolName, Timeframe } from './market';

export interface BacktestConfig {
  symbol: SymbolName;
  timeframe: Timeframe;
  strategy: 'AI Ensemble' | 'Transformer Alpha' | 'XGBoost Momentum' | 'Multi-Model Regime Adaptive';
  startDate: string;
  endDate: string;
  initialCapital: number;
  riskPerTrade: number;
  feePct: number;
  slippagePct: number;
  confidenceThreshold: number;
  minAgreement: number;
}

export interface BacktestTrade {
  id: string;
  symbol: SymbolName;
  side: 'LONG' | 'SHORT';
  entryTime: string;
  exitTime: string;
  entryPrice: number;
  exitPrice: number;
  size: number;
  pnlUsd: number;
  pnlPct: number;
  returnR: number;
  exitReason: 'TP1' | 'TP2' | 'TP3' | 'SL' | 'TIME_EXIT' | 'REGIME_CHANGE';
  durationBars: number;
}

export interface EquityPoint {
  time: string;
  equity: number;
  drawdown: number;
  benchmarkEquity: number;
}

export interface MonthlyReturn {
  year: number;
  months: (number | null)[]; // Jan to Dec returns in %
  totalYear: number;
}

export interface RollingMetricPoint {
  time: string;
  sharpe: number;
  sortino: number;
  calmar: number;
}

export interface MonteCarloPath {
  id: number;
  points: number[];
}

export interface MonteCarloResult {
  simulationsCount: number;
  medianFinalEquity: number;
  percentile5th: number;
  percentile25th: number;
  percentile75th: number;
  percentile95th: number;
  probabilityOfRuin: number; // % chance of losing > 25%
  maxDrawdownMedian: number;
  maxDrawdown95th: number;
  samplePaths: { time: number; p5: number; p25: number; median: number; p75: number; p95: number }[];
}

export interface WalkForwardWindow {
  windowIndex: number;
  trainRange: string;
  valRange: string;
  testRange: string;
  inSampleSharpe: number;
  outOfSampleSharpe: number;
  wfeRatio: number; // Walk-Forward Efficiency (OOS Sharpe / IS Sharpe)
  stabilityScore: number;
  parameterShift: string;
}

export interface OptimizationParamResult {
  paramA: number; // e.g. Confidence Threshold
  paramB: number; // e.g. Risk/Reward Multiple
  sharpe: number;
  winRate: number;
  drawdown: number;
  profitFactor: number;
}

export interface BacktestMetrics {
  totalReturnPct: number;
  cagr: number;
  winRate: number;
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  sharpeRatio: number;
  sortinoRatio: number;
  calmarRatio: number;
  profitFactor: number;
  maxDrawdownPct: number;
  maxDrawdownDurationDays: number;
  avgWinR: number;
  avgLossR: number;
  expectancyR: number;
  longWinRate: number;
  shortWinRate: number;
  longCount: number;
  shortCount: number;
}

export interface BacktestResult {
  id: string;
  config: BacktestConfig;
  executedAt: string;
  metrics: BacktestMetrics;
  equityCurve: EquityPoint[];
  trades: BacktestTrade[];
  monthlyReturns: MonthlyReturn[];
  rollingMetrics: RollingMetricPoint[];
  monteCarlo: MonteCarloResult;
  walkForward: WalkForwardWindow[];
  optimizationSurface: OptimizationParamResult[];
}
