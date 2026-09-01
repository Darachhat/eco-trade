import React from 'react';
import { Position } from '../../types/position';
import { usePositionStore } from '../../stores/usePositionStore';
import { StatusBadge } from '../common/StatusBadge';
import { formatCurrency, formatPercent, formatPrice } from '../../lib/formatters/formatters';
import { X, ExternalLink } from 'lucide-react';
import { cn } from '../../lib/utils';

export const PositionTable: React.FC<{ positions: Position[] }> = ({ positions }) => {
  const closePosition = usePositionStore((s) => s.closePosition);

  if (positions.length === 0) {
    return (
      <div className="terminal-panel p-8 text-center font-mono text-xs text-terminal-muted">
        No active positions currently open.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto w-full">
      <table className="terminal-table">
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Mode</th>
            <th>Side</th>
            <th>Size</th>
            <th>Entry Price</th>
            <th>Mark Price</th>
            <th>Unrealized PnL ($)</th>
            <th>Unrealized PnL (%)</th>
            <th>Stop Loss</th>
            <th>Take Profit</th>
            <th>R:R</th>
            <th>Duration</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {positions.map((pos) => {
            const isPos = pos.unrealizedPnlUsd >= 0;
            return (
              <tr key={pos.id}>
                <td className="font-bold text-terminal-text">{pos.symbol}</td>
                <td>
                  <StatusBadge variant={pos.mode} size="xs" />
                </td>
                <td>
                  <StatusBadge variant={pos.side} size="xs" />
                </td>
                <td className="font-mono">{pos.size} ({formatCurrency(pos.sizeUsd, 0)})</td>
                <td>{formatPrice(pos.entryPrice, pos.symbol)}</td>
                <td>{formatPrice(pos.markPrice, pos.symbol)}</td>
                <td className={cn('font-bold', isPos ? 'text-terminal-bull' : 'text-terminal-bear')}>
                  {isPos ? `+${formatCurrency(pos.unrealizedPnlUsd)}` : formatCurrency(pos.unrealizedPnlUsd)}
                </td>
                <td className={cn('font-bold', isPos ? 'text-terminal-bull' : 'text-terminal-bear')}>
                  {formatPercent(pos.unrealizedPnlPct, 2)}
                </td>
                <td className="text-terminal-bear">{formatPrice(pos.stopLoss, pos.symbol)}</td>
                <td className="text-terminal-bull">{formatPrice(pos.tp1, pos.symbol)}</td>
                <td className="font-bold text-terminal-cyan">{pos.riskReward}R</td>
                <td className="text-terminal-muted">{pos.durationFormatted}</td>
                <td>
                  <button
                    onClick={() => closePosition(pos.id)}
                    className="px-2 py-0.5 bg-terminal-bearDim/40 hover:bg-terminal-bear text-terminal-bear hover:text-white border border-terminal-bear/40 rounded text-2xs transition-colors flex items-center gap-1 font-semibold"
                  >
                    <X className="w-3 h-3" />
                    Close
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
