import React from 'react';
import { useMarketStore } from '../../stores/useMarketStore';
import { formatCompactNumber, formatPercent } from '../../lib/formatters/formatters';
import { cn } from '../../lib/utils';

export const FundingOIWidget: React.FC<{ className?: string }> = ({ className }) => {
  const activeSymbol = useMarketStore((s) => s.activeSymbol);
  const fundingRates = useMarketStore((s) => s.fundingRates);
  const openInterestHistory = useMarketStore((s) => s.openInterestHistory);

  const funding = fundingRates[activeSymbol] || {
    rate: 0.0001,
    predictedRate: 0.0001,
    nextFundingTime: '04:00:00',
    annualizedRate: 10.95,
  };

  const latestOI = openInterestHistory[openInterestHistory.length - 1];

  return (
    <div className={cn('terminal-panel flex flex-col', className)}>
      <div className="terminal-header">
        <span>Perpetual Funding & Open Interest</span>
        <span className="font-mono text-2xs text-terminal-muted">Next: {funding.nextFundingTime}</span>
      </div>

      <div className="grid grid-cols-2 gap-2 p-3 font-mono text-xs">
        {/* Funding Rate Box */}
        <div className="terminal-card p-2.5 space-y-1">
          <span className="text-2xs uppercase tracking-wider text-terminal-muted block">8h Funding Rate</span>
          <div className="flex items-baseline justify-between">
            <span
              className={cn(
                'text-sm font-bold',
                funding.rate >= 0 ? 'text-terminal-bull' : 'text-terminal-bear'
              )}
            >
              {(funding.rate * 100).toFixed(4)}%
            </span>
            <span className="text-2xs text-terminal-muted">
              {formatPercent(funding.annualizedRate, 1)} APR
            </span>
          </div>
          <span className="text-3xs text-terminal-dim block">
            Predicted: {(funding.predictedRate * 100).toFixed(4)}%
          </span>
        </div>

        {/* Open Interest Box */}
        <div className="terminal-card p-2.5 space-y-1">
          <span className="text-2xs uppercase tracking-wider text-terminal-muted block">Open Interest</span>
          <div className="flex items-baseline justify-between">
            <span className="text-sm font-bold text-terminal-cyan">
              {latestOI?.openInterest ? `${latestOI.openInterest.toLocaleString()} BTC` : '—'}
            </span>
            <span className="text-2xs text-terminal-bull font-semibold">
              +{latestOI?.oiChangePct}% (1h)
            </span>
          </div>
          <span className="text-3xs text-terminal-dim block">
            Aggregated Linear Perps
          </span>
        </div>
      </div>
    </div>
  );
};
