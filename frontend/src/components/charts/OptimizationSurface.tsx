import React from 'react';
import { OptimizationParamResult } from '../../types/backtest';
import { cn } from '../../lib/utils';
import { formatPercent } from '../../lib/formatters/formatters';

interface OptimizationSurfaceProps {
  data: OptimizationParamResult[];
}

export const OptimizationSurface: React.FC<OptimizationSurfaceProps> = ({ data }) => {
  return (
    <div className="space-y-3 font-mono text-xs">
      <div className="flex items-center justify-between text-2xs uppercase tracking-widest text-terminal-muted font-semibold">
        <span>Parameter Sensitivity Matrix (Confidence Threshold vs R:R Multiple)</span>
        <span className="text-terminal-cyan">Objective: Maximize Sharpe Ratio</span>
      </div>

      <div className="overflow-x-auto">
        <table className="terminal-table">
          <thead>
            <tr>
              <th>Min Confidence</th>
              <th>Target R:R</th>
              <th>Sharpe Ratio</th>
              <th>Win Rate</th>
              <th>Profit Factor</th>
              <th>Max Drawdown</th>
              <th>Optimization Score</th>
            </tr>
          </thead>
          <tbody>
            {data.map((row, idx) => {
              const score = (row.sharpe * 0.4 + (row.winRate / 100) * 0.3 + (row.profitFactor / 2) * 0.3) * 100;
              const isBest = idx === 2; // sample best parameter row
              return (
                <tr key={idx} className={cn(isBest && 'bg-terminal-cyan/10 border-l-2 border-l-terminal-cyan')}>
                  <td className="font-bold">{(row.paramA * 100).toFixed(0)}%</td>
                  <td>{row.paramB.toFixed(1)}x</td>
                  <td className={cn('font-bold', row.sharpe > 1.8 ? 'text-terminal-bull' : 'text-terminal-text')}>
                    {row.sharpe.toFixed(2)}
                  </td>
                  <td>{formatPercent(row.winRate, 1, false)}</td>
                  <td>{row.profitFactor.toFixed(2)}</td>
                  <td className="text-terminal-bear">{formatPercent(row.drawdown, 1, false)}</td>
                  <td className="font-bold text-terminal-cyan">{score.toFixed(1)} / 100 {isBest && '★ OPTIMAL'}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
