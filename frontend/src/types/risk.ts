export interface CircuitBreakerRule {
  id: string;
  name: string;
  condition: string;
  currentValue: string;
  threshold: string;
  status: 'SAFE' | 'WARNING' | 'BREACHED';
}

export interface RiskStatus {
  accountEquity: number;
  initialBalance: number;
  availableMargin: number;
  usedMargin: number;
  marginUsagePct: number;
  dailyLossUsd: number;
  dailyLossLimitUsd: number;
  dailyLossPct: number;
  dailyLossLimitPct: number;
  weeklyDrawdownPct: number;
  weeklyDrawdownLimitPct: number;
  maxDrawdownPct: number;
  openPositionsCount: number;
  maxOpenPositions: number;
  riskPerTradePct: number;
  consecutiveLosses: number;
  maxConsecutiveLosses: number;
  killSwitchActive: boolean;
  killSwitchReason?: string;
  tradingPaused: boolean;
  circuitBreakers: CircuitBreakerRule[];
}
