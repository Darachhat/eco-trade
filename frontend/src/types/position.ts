import { SymbolName } from './market';
import { SignalDirection } from './signal';

export type PositionSide = 'LONG' | 'SHORT';
export type PositionMode = 'PAPER' | 'LIVE';

export interface Position {
  id: string;
  symbol: SymbolName;
  side: PositionSide;
  mode: PositionMode;
  entryPrice: number;
  markPrice: number;
  size: number;
  sizeUsd: number;
  leverage: number;
  marginUsd: number;
  unrealizedPnlUsd: number;
  unrealizedPnlPct: number;
  realizedPnlUsd: number;
  stopLoss: number;
  tp1: number;
  tp2: number;
  tp3: number;
  riskReward: number;
  liquidationPrice: number;
  durationFormatted: string;
  openedAt: string;
  strategy: string;
  confidenceAtEntry: number;
}

export interface JournalTrade {
  id: string;
  symbol: SymbolName;
  side: PositionSide;
  mode: PositionMode;
  entryPrice: number;
  exitPrice: number;
  size: number;
  pnlUsd: number;
  pnlPct: number;
  returnR: number;
  openedAt: string;
  closedAt: string;
  duration: string;
  strategy: string;
  regimeAtEntry: string;
  modelAgreementAtEntry: number;
  exitReason: string;
  tags: string[];
  notes: string;
}
