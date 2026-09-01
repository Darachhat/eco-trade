import React, { useState } from 'react';
import { usePositionStore } from '../stores/usePositionStore';
import { TradeJournalTable } from '../components/journal/TradeJournalTable';
import { MetricCard } from '../components/common/MetricCard';
import { formatCurrency, formatPercent, formatR } from '../lib/formatters/formatters';
import { BookOpen, TrendingUp, Filter, Plus } from 'lucide-react';

export const TradeJournalView: React.FC = () => {
  const journalTrades = usePositionStore((s) => s.journalTrades);

  const totalTrades = journalTrades.length;
  const wins = journalTrades.filter((t) => t.pnlUsd > 0).length;
  const winRate = totalTrades > 0 ? (wins / totalTrades) * 100 : 0;
  const totalPnL = journalTrades.reduce((acc, t) => acc + t.pnlUsd, 0);
  const avgR = totalTrades > 0 ? journalTrades.reduce((acc, t) => acc + t.returnR, 0) / totalTrades : 0;

  return (
    <div className="space-y-4 p-3 font-mono">
      {/* 1. Header Banner */}
      <div className="terminal-panel p-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <BookOpen className="w-5 h-5 text-terminal-cyan" />
          <div>
            <h1 className="text-sm font-bold text-terminal-text uppercase tracking-wider">
              Quantitative Trade Journal & Execution Log
            </h1>
            <p className="text-2xs text-terminal-muted">
              Audit trail of all executed paper and live orders with model consensus metadata
            </p>
          </div>
        </div>
      </div>

      {/* 2. Journal Performance Metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        <MetricCard
          label="Total Realized PnL"
          value={totalPnL >= 0 ? `+${formatCurrency(totalPnL)}` : formatCurrency(totalPnL)}
          delta={{ value: `${winRate.toFixed(0)}% Win Rate`, isPositive: totalPnL >= 0 }}
          variant={totalPnL >= 0 ? 'bull' : 'bear'}
        />
        <MetricCard
          label="Closed Trades"
          value={totalTrades}
          subValue={`${wins} Wins / ${totalTrades - wins} Losses`}
        />
        <MetricCard
          label="Average Return (R)"
          value={formatR(avgR)}
          subValue="Calculated against 1R initial risk"
          variant="cyan"
        />
        <MetricCard
          label="Execution Strategy"
          value="AI Ensemble"
          subValue="Cross-model consensus"
        />
      </div>

      {/* 3. Trade Journal Table */}
      <div className="terminal-panel flex flex-col">
        <div className="terminal-header">
          <span>Executed Trades & Post-Trade Analysis</span>
          <span className="text-2xs text-terminal-muted font-mono">{totalTrades} Logged Trades</span>
        </div>
        <div className="p-2">
          <TradeJournalTable trades={journalTrades} />
        </div>
      </div>
    </div>
  );
};
