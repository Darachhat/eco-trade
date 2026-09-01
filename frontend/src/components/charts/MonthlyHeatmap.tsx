import React from 'react';
import { MonthlyReturn } from '../../types/backtest';
import { cn } from '../../lib/utils';
import { formatPercent } from '../../lib/formatters/formatters';

interface MonthlyHeatmapProps {
  data: MonthlyReturn[];
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export const MonthlyHeatmap: React.FC<MonthlyHeatmapProps> = ({ data }) => {
  const getCellColor = (val: number | null): string => {
    if (val === null || val === undefined) return 'bg-terminal-border/20 text-terminal-dim';
    if (val > 6) return 'bg-terminal-bull/30 text-terminal-bull font-bold';
    if (val > 3) return 'bg-terminal-bull/20 text-terminal-bull font-medium';
    if (val > 0) return 'bg-terminal-bull/10 text-terminal-bull';
    if (val === 0) return 'bg-terminal-surface text-terminal-muted';
    if (val > -3) return 'bg-terminal-bear/10 text-terminal-bear';
    if (val > -6) return 'bg-terminal-bear/20 text-terminal-bear font-medium';
    return 'bg-terminal-bear/30 text-terminal-bear font-bold';
  };

  return (
    <div className="w-full overflow-x-auto">
      <table className="w-full text-xs font-mono text-center border-collapse">
        <thead>
          <tr className="border-b border-terminal-border bg-terminal-surface/30">
            <th className="py-1 px-2 text-2xs uppercase tracking-wider text-terminal-muted text-left">Year</th>
            {MONTHS.map((m) => (
              <th key={m} className="py-1 px-1.5 text-2xs uppercase tracking-wider text-terminal-muted">
                {m}
              </th>
            ))}
            <th className="py-1 px-2 text-2xs uppercase tracking-wider text-terminal-cyan bg-terminal-cyan/5">
              Year Total
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-terminal-border/40">
          {data.map((row) => (
            <tr key={row.year} className="hover:bg-terminal-elevated/20">
              <td className="py-1.5 px-2 font-bold text-terminal-text text-left">{row.year}</td>
              {row.months.map((mVal, mIdx) => (
                <td
                  key={mIdx}
                  className={cn(
                    'py-1.5 px-1 border border-terminal-border/30 rounded-2xs text-2xs transition-colors',
                    getCellColor(mVal)
                  )}
                >
                  {mVal !== null ? formatPercent(mVal, 1) : '—'}
                </td>
              ))}
              <td
                className={cn(
                  'py-1.5 px-2 font-bold text-2xs border-l border-terminal-border bg-terminal-surface/40',
                  row.totalYear >= 0 ? 'text-terminal-bull' : 'text-terminal-bear'
                )}
              >
                {formatPercent(row.totalYear, 1)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
