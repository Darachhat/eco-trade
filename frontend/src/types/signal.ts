import { SymbolName, Timeframe } from './market';

export type SignalDirection = 'LONG' | 'SHORT' | 'NEUTRAL';
export type SignalStatus = 'VALID' | 'WATCH' | 'INVALIDATED' | 'EXECUTED' | 'CLOSED';
export type MarketRegimeType = 'BULL_TRENDING' | 'BEAR_TRENDING' | 'RANGING' | 'HIGH_VOLATILITY';

export interface ModelVote {
  name: string;
  category: 'ML' | 'Deep Learning' | 'Statistical' | 'Baseline';
  direction: SignalDirection;
  probability: number;
  weight: number;
  accuracy: number;
  status: 'CHAMPION' | 'CANDIDATE' | 'BENCHMARK';
}

export interface SHAPFeatureContribution {
  feature: string;
  description: string;
  value: number; // raw feature value
  shapValue: number; // positive = pushes long, negative = pushes short
  impact: 'positive' | 'negative';
}

export interface KeyDriver {
  text: string;
  type: 'positive' | 'negative';
  strength: 'high' | 'medium' | 'low';
}

export interface Signal {
  id: string;
  symbol: SymbolName;
  timeframe: Timeframe;
  direction: SignalDirection;
  status: SignalStatus;
  confidence: number;
  agreement: number;
  regime: MarketRegimeType;
  entryZoneMin: number;
  entryZoneMax: number;
  currentPrice: number;
  stopLoss: number;
  tp1: number;
  tp2: number;
  tp3: number;
  riskRewardRatio: number;
  mtfConfirmation: boolean;
  generatedAt: string;
  ageMinutes: number;
  models: ModelVote[];
  shapContributions: SHAPFeatureContribution[];
  keyDrivers: KeyDriver[];
  notes?: string;
}
