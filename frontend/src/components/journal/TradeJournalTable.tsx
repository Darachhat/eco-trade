import React from 'react';
import { JournalTrade } from '../../types/position';
import { StatusBadge } from '../common/StatusBadge';
import { formatCurrency, formatPercent, formatPrice, formatR } from '../../lib/formatters/formatters';
import { cn } from '../../lib/utils';

export const TradeJournalTable: React.FC<{ trades: JournalTrade[] }> = ({ trades }) => {
  if (trades.length === 0) {
    return (
      <div className="terminal-panel p-8 text-center font-mono text-xs text-terminal-muted">
        No completed trades in journal.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto w-full">
      <table className="terminal-table">
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Side</th>
            <th>Strategy</th>
            <th>Entry</th>
            <th>Exit</th>
            <th>PnL ($)</th>
            <th>Return (%)</th>
            <th>Return (R)</th>
            <th>Exit Reason</th>
            <th>Regime</th>
            <th>Closed At</th>
            <th>Tags & Notes</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((t) => {
            const isWin = t.pnlUsd >= 0;
            return (
              <tr key={t.id}>
                <td className="font-bold text-terminal-text">{t.symbol}</td>
                <td>
                  <StatusBadge variant={t.side} size="xs" />
                </td>
                <td className="text-terminal-muted">{t.strategy}</td>
                <td>{formatPrice(t.entryPrice, t.symbol)}</td>
                <td>{formatPrice(t.exitPrice, t.symbol)}</td>
                <td className={cn('font-bold', isWin ? 'text-terminal-bull' : 'text-terminal-bear')}>
                  {isWin ? `+${formatCurrency(t.pnlUsd)}` : formatCurrency(t.pnlUsd)}
                </td>
                <td className={cn('font-bold', isWin ? 'text-terminal-bull' : 'text-terminal-bear')}>
                  {formatPercent(t.pnlPct, 2)}
                </td>
                <td className={cn('font-bold font-mono', isWin ? 'text-terminal-bull' : 'text-terminal-bear')}>
                  {formatR(t.returnR)}
                </td>
                <td>
                  <span className="text-2xs px-1.5 py-0.5 bg-terminal-surface rounded border border-terminal-border">
                    {t.exitReason}
                  </span>
                </td>
                <td className="text-terminal-dim text-2xs">{t.regimeAtEntry.replace(/_/g, ' ')}</td>
                <td className="text-terminal-muted text-2xs">{t.closedAt}</td>
                <td className="text-terminal-muted text-2xs max-w-xs">
                  <div className="flex flex-wrap gap-1 mb-0.5">
                    {t.tags.map((tag, i) => (
                      <span key={i} className="px-1 bg-terminal-cyan/10 text-terminal-cyan rounded text-3xs">
                        #{tag}
                      </span>
                    ))}
                  </div>
                  <div className="truncate text-3xs text-terminal-dim">{t.notes}</div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
