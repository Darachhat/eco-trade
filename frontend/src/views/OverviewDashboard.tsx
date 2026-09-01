import React, { useState } from 'react';
import { useMarketStore } from '../stores/useMarketStore';
import { useSignalStore } from '../stores/useSignalStore';
import { useRiskStore } from '../stores/useRiskStore';
import { usePositionStore } from '../stores/usePositionStore';
import { useModelStore } from '../stores/useModelStore';
import { MetricCard } from '../components/common/MetricCard';
import { StatusBadge } from '../components/common/StatusBadge';
import { TradingViewChart } from '../components/charts/TradingViewChart';
import { OrderBook } from '../components/trading/OrderBook';
import { SignalCard } from '../components/signals/SignalCard';
import { ConsensusTable } from '../components/signals/ConsensusTable';
import { SignalExplainDrawer } from '../components/signals/SignalExplainDrawer';
import { TradeExecutionModal } from '../components/trading/TradeExecutionModal';
import { RiskGauge } from '../components/common/RiskGauge';
import { formatCurrency, formatPercent, formatPrice } from '../lib/formatters/formatters';
import {
  TrendingUp,
  ShieldCheck,
  Zap,
  Activity,
  Layers,
  DollarSign,
  PieChart,
  Cpu,
} from 'lucide-react';
import { Signal } from '../types/signal';

export const OverviewDashboard: React.FC = () => {
  const activeSymbol = useMarketStore((s) => s.activeSymbol);
  const tickers = useMarketStore((s) => s.tickers);
  const signals = useSignalStore((s) => s.signals);
  const selectedSignalId = useSignalStore((s) => s.selectedSignalId);
  const setSelectedSignalId = useSignalStore((s) => s.setSelectedSignalId);
  const isExplainModalOpen = useSignalStore((s) => s.isExplainModalOpen);
  const setIsExplainModalOpen = useSignalStore((s) => s.setIsExplainModalOpen);

  const riskStatus = useRiskStore((s) => s.riskStatus);
  const positions = usePositionStore((s) => s.positions);
  const models = useModelStore((s) => s.models);
  const regime = useModelStore((s) => s.regime);

  const [tradeModalSignal, setTradeModalSignal] = useState<Signal | null>(null);

  const currentTicker = tickers[activeSymbol] || tickers['BTCUSDT'];
  const topSignal = signals.find((s) => s.symbol === activeSymbol) || signals[0];
  const selectedSignal = signals.find((s) => s.id === selectedSignalId) || topSignal;

  const handleExplainClick = (sig: Signal) => {
    setSelectedSignalId(sig.id);
    setIsExplainModalOpen(true);
  };

  const handleTradeClick = (sig: Signal) => {
    setTradeModalSignal(sig);
  };

  return (
    <div className="space-y-3 p-3">
      {/* 1. TOP PORTFOLIO & RISK KPI SUMMARY BAR */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
        <MetricCard
          label="Portfolio Equity"
          value={formatCurrency(riskStatus.accountEquity)}
          delta={{ value: '+2.14% Today', isPositive: true }}
          icon={<DollarSign className="w-4 h-4 text-terminal-cyan" />}
          variant="cyan"
        />
        <MetricCard
          label="Daily PnL / Loss"
          value={`$${riskStatus.dailyLossUsd.toFixed(2)}`}
          subValue={`Limit: $${riskStatus.dailyLossLimitUsd.toFixed(2)}`}
          delta={{ value: `${riskStatus.dailyLossPct.toFixed(2)}% used`, isPositive: riskStatus.dailyLossPct < 2 }}
          variant={riskStatus.dailyLossPct > 2 ? 'bear' : 'default'}
        />
        <MetricCard
          label="Historical Win Rate"
          value="68.4%"
          subValue="842 closed trades"
          icon={<TrendingUp className="w-4 h-4 text-terminal-bull" />}
          variant="bull"
        />
        <MetricCard
          label="Max Drawdown"
          value={`-${riskStatus.maxDrawdownPct.toFixed(2)}%`}
          subValue={`Weekly Limit: ${riskStatus.weeklyDrawdownLimitPct.toFixed(2)}%`}
          variant="bear"
        />
        <MetricCard
          label="Open Positions"
          value={`${positions.length} / ${riskStatus.maxOpenPositions}`}
          subValue={`Margin: ${riskStatus.marginUsagePct.toFixed(1)}%`}
          icon={<Layers className="w-4 h-4 text-terminal-muted" />}
        />
        <MetricCard
          label="Market Regime"
          value={regime.currentRegime.replace(/_/g, ' ')}
          subValue={`Prob: ${regime.probability}% • ADX: ${regime.adx}`}
          icon={<Activity className="w-4 h-4 text-terminal-cyan" />}
          variant="cyan"
        />
      </div>

      {/* 2. MAIN CENTER GRID */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
        {/* Left: TradingView Candlestick Chart (8 cols) */}
        <div className="lg:col-span-8 terminal-panel flex flex-col min-h-[440px]">
          <div className="terminal-header">
            <div className="flex items-center gap-2">
              <span className="font-bold text-terminal-text">{activeSymbol} Candlestick Feed</span>
              <span className="text-2xs text-terminal-muted">Bybit Linear 15m</span>
            </div>
            <div className="flex items-center gap-2 font-mono text-xs">
              <span className="font-bold text-terminal-text">
                ${formatPrice(currentTicker.price, activeSymbol)}
              </span>
              <span className={currentTicker.change24h >= 0 ? 'text-terminal-bull' : 'text-terminal-bear'}>
                {formatPercent(currentTicker.change24h)}
              </span>
            </div>
          </div>
          <div className="p-2 flex-1 relative min-h-[380px]">
            <TradingViewChart />
          </div>
        </div>

        {/* Right: AI Signal & Live Order Book (4 cols) */}
        <div className="lg:col-span-4 flex flex-col gap-3">
          {/* Active AI Signal Card */}
          {topSignal ? (
            <SignalCard
              signal={topSignal}
              onExplainClick={handleExplainClick}
              onTradeClick={handleTradeClick}
            />
          ) : (
            <div className="terminal-panel p-6 text-center text-terminal-muted text-xs">
              Evaluating live models...
            </div>
          )}

          {/* L2 Depth Order Book Ladder */}
          <div className="terminal-panel flex-1 flex flex-col min-h-[220px]">
            <OrderBook />
          </div>
        </div>
      </div>

      {/* 3. BOTTOM SECTION: 10-MODEL CONSENSUS + RISK CENTER */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
        {/* Left: 10-Model Consensus Matrix (8 cols) */}
        <div className="lg:col-span-8 terminal-panel flex flex-col">
          <div className="terminal-header">
            <div className="flex items-center gap-2">
              <Cpu className="w-3.5 h-3.5 text-terminal-cyan" />
              <span>Multi-Model AI Consensus Engine (10 Quantitative Models)</span>
            </div>
            <span className="text-terminal-cyan text-2xs font-mono">Ensemble Agreement: 81.2%</span>
          </div>
          <div className="p-2 flex-1">
            <ConsensusTable
              models={
                topSignal?.models ||
                models.map((m) => ({
                  name: m.name,
                  category: m.type as any,
                  direction: 'LONG',
                  probability: 0.82,
                  weight: m.weight,
                  accuracy: m.metrics.accuracy,
                  status: m.status as any,
                }))
              }
            />
          </div>
        </div>

        {/* Right: Live Risk Monitor Gauges (4 cols) */}
        <div className="lg:col-span-4 terminal-panel flex flex-col">
          <div className="terminal-header">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-3.5 h-3.5 text-terminal-bull" />
              <span>Real-Time Risk Center</span>
            </div>
            <StatusBadge variant="HEALTHY" size="xs" />
          </div>
          <div className="p-3 space-y-2.5 flex-1 flex flex-col justify-between">
            <RiskGauge
              label="Daily Loss Limit"
              current={riskStatus.dailyLossPct}
              limit={riskStatus.dailyLossLimitPct}
            />
            <RiskGauge
              label="Weekly Max Drawdown"
              current={riskStatus.weeklyDrawdownPct}
              limit={riskStatus.weeklyDrawdownLimitPct}
            />
            <RiskGauge
              label="Active Position Exposure"
              current={positions.length}
              limit={riskStatus.maxOpenPositions}
              unit=" pos"
              isPercent={false}
            />
            <RiskGauge
              label="Consecutive Loss Guard"
              current={riskStatus.consecutiveLosses}
              limit={riskStatus.maxConsecutiveLosses}
              unit=" loss"
              isPercent={false}
            />
          </div>
        </div>
      </div>

      {/* Deep Explainability Drawer */}
      <SignalExplainDrawer
        signal={selectedSignal}
        isOpen={isExplainModalOpen}
        onClose={() => setIsExplainModalOpen(false)}
        onTradeClick={handleTradeClick}
      />

      {/* Interactive 1-Click Trade Execution Modal */}
      <TradeExecutionModal
        signal={tradeModalSignal}
        isOpen={!!tradeModalSignal}
        onClose={() => setTradeModalSignal(null)}
      />
    </div>
  );
};
