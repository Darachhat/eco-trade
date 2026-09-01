import React from 'react';
import { DriftMetric } from '../../types/model';
import { StatusBadge } from '../common/StatusBadge';
import { AlertTriangle, CheckCircle, Flame } from 'lucide-react';
import { cn } from '../../lib/utils';

export const DriftTable: React.FC<{ metrics: DriftMetric[] }> = ({ metrics }) => {
  return (
    <div className="overflow-x-auto w-full">
      <table className="terminal-table">
        <thead>
          <tr>
            <th>Feature Name</th>
            <th>PSI (Population Stability)</th>
            <th>KS-Statistic</th>
            <th>p-Value</th>
            <th>Baseline Mean (Std)</th>
            <th>Current Mean (Std)</th>
            <th>Drift Status</th>
            <th>Last Checked</th>
          </tr>
        </thead>
        <tbody>
          {metrics.map((m, idx) => (
            <tr
              key={idx}
              className={cn(
                m.status === 'CRITICAL' && 'bg-terminal-bear/10',
                m.status === 'WARNING' && 'bg-terminal-amber/5'
              )}
            >
              <td className="font-bold text-terminal-text flex items-center gap-1.5">
                {m.status === 'CRITICAL' ? (
                  <Flame className="w-3.5 h-3.5 text-terminal-bear" />
                ) : m.status === 'WARNING' ? (
                  <AlertTriangle className="w-3.5 h-3.5 text-terminal-amber" />
                ) : (
                  <CheckCircle className="w-3.5 h-3.5 text-terminal-bull" />
                )}
                {m.featureName}
              </td>
              <td className="font-bold">
                <span
                  className={cn(
                    m.psi >= 0.25
                      ? 'text-terminal-bear'
                      : m.psi >= 0.1
                      ? 'text-terminal-amber'
                      : 'text-terminal-bull'
                  )}
                >
                  {m.psi.toFixed(3)}
                </span>
              </td>
              <td>{m.ksStatistic.toFixed(3)}</td>
              <td className={cn(m.pValue < 0.05 ? 'text-terminal-bear font-bold' : 'text-terminal-muted')}>
                {m.pValue.toFixed(3)}
              </td>
              <td className="text-terminal-muted">
                {m.meanBaseline.toFixed(2)} ({m.stdBaseline.toFixed(2)})
              </td>
              <td className="text-terminal-text">
                {m.meanCurrent.toFixed(2)} ({m.stdCurrent.toFixed(2)})
              </td>
              <td>
                <StatusBadge variant={m.status} size="xs" />
              </td>
              <td className="text-terminal-dim">{m.lastUpdated}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
