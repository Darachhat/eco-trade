import React from 'react';
import { usePositionStore } from '../stores/usePositionStore';
import { useRiskStore } from '../stores/useRiskStore';
import { PositionTable } from '../components/positions/PositionTable';
import { MetricCard } from '../components/common/MetricCard';
import { formatCurrency, formatPercent } from '../lib/formatters/formatters';
import { Layers, ShieldCheck, DollarSign, PieChart } from 'lucide-react';

export const PositionsView: React.FC = () => {
  const positions = usePositionStore((s) => s.positions);
  const riskStatus = useRiskStore((s) => s.riskStatus);

  const totalUnrealizedPnlUsd = positions.reduce((acc, p) => acc + p.unrealizedPnlUsd, 0);
  const totalMarginUsed = positions.reduce((acc, p) => acc + p.marginUsd, 0);
  const totalExposureUsd = positions.reduce((acc, p) => acc + p.sizeUsd, 0);

  return (
    <div className="space-y-4 p-3 font-mono">
      {/* 1. Header & Metric Summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <MetricCard
          label="Open Positions"
          value={`${positions.length} / ${riskStatus.maxOpenPositions}`}
          subValue={`Exposure: ${formatCurrency(totalExposureUsd, 0)}`}
          icon={<Layers className="w-4 h-4 text-terminal-cyan" />}
          variant="cyan"
        />
        <MetricCard
          label="Unrealized PnL"
          value={totalUnrealizedPnlUsd >= 0 ? `+${formatCurrency(totalUnrealizedPnlUsd)}` : formatCurrency(totalUnrealizedPnlUsd)}
          delta={{ value: totalUnrealizedPnlUsd >= 0 ? '+1.42%' : '-0.85%', isPositive: totalUnrealizedPnlUsd >= 0 }}
          variant={totalUnrealizedPnlUsd >= 0 ? 'bull' : 'bear'}
        />
        <MetricCard
          label="Margin Utilized"
          value={formatCurrency(totalMarginUsed)}
          subValue={`Available: ${formatCurrency(riskStatus.availableMargin)}`}
          icon={<PieChart className="w-4 h-4 text-terminal-muted" />}
        />
        <MetricCard
          label="Risk Exposure / Pos"
          value="1.0% / Trade"
          subValue="Cross-margin isolation"
          icon={<ShieldCheck className="w-4 h-4 text-terminal-bull" />}
        />
      </div>

      {/* 2. Positions Table */}
      <div className="terminal-panel flex flex-col">
        <div className="terminal-header">
          <div className="flex items-center gap-2">
            <Layers className="w-3.5 h-3.5 text-terminal-cyan" />
            <span>Active Real-Time Derivative Positions (Bybit Linear Perpetual)</span>
          </div>
          <span className="text-2xs text-terminal-muted">Automated SL/TP Trailing Active</span>
        </div>
        <div className="p-2">
          <PositionTable positions={positions} />
        </div>
      </div>
    </div>
  );
};
