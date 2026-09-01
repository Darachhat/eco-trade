import { MarketRegimeType } from './signal';

export interface ModelMetric {
  accuracy: number;
  winRate: number;
  sharpe: number;
  sortino: number;
  profitFactor: number;
  maxDrawdown: number;
  totalTrades: number;
  expectedValue: number;
}

export interface ModelInfo {
  id: string;
  name: string;
  type: 'Gradient Boosting' | 'Transformer' | 'Recurrent Neural Net' | 'Statistical' | 'Linear' | 'Rule-based';
  version: string;
  champion: boolean;
  status: 'CHAMPION' | 'CHALLENGER' | 'BENCHMARK' | 'RETIRED';
  weight: number; // Ensemble weighting % (e.g. 0.20)
  lastTrained: string;
  metrics: ModelMetric;
  regimePerformance: Record<MarketRegimeType, { winRate: number; profitFactor: number }>;
  hyperparameters: Record<string, string | number | boolean>;
  trainingHistory: {
    epochOrIter: number;
    trainLoss: number;
    valLoss: number;
    valAccuracy: number;
  }[];
}

export interface OptunaTrial {
  trialNumber: number;
  value: number; // Optimization objective e.g. Sharpe
  params: Record<string, any>;
  state: 'COMPLETE' | 'PRUNED' | 'FAIL';
  durationSeconds: number;
}

export interface DriftMetric {
  featureName: string;
  psi: number; // Population Stability Index
  ksStatistic: number; // Kolmogorov-Smirnov statistic
  pValue: number;
  status: 'NORMAL' | 'WARNING' | 'CRITICAL';
  meanBaseline: number;
  meanCurrent: number;
  stdBaseline: number;
  stdCurrent: number;
  lastUpdated: string;
}

export interface RegimeStatus {
  currentRegime: MarketRegimeType;
  probability: number;
  adx: number;
  volatilityState: 'LOW' | 'NORMAL' | 'ELEVATED' | 'EXTREME';
  durationHours: number;
  durationMinutes: number;
  transitionProbabilities: Record<MarketRegimeType, number>;
  regimeHistory: {
    regime: MarketRegimeType;
    startTime: string;
    endTime: string;
    durationMinutes: number;
  }[];
}
