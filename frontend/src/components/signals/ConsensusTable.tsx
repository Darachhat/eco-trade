import React from 'react';
import { ModelVote } from '../../types/signal';
import { StatusBadge } from '../common/StatusBadge';
import { formatPercent } from '../../lib/formatters/formatters';
import { cn } from '../../lib/utils';

interface ConsensusTableProps {
  models: ModelVote[];
}

export const ConsensusTable: React.FC<ConsensusTableProps> = ({ models }) => {
  return (
    <div className="overflow-x-auto w-full">
      <table className="terminal-table">
        <thead>
          <tr>
            <th>Model Architecture</th>
            <th>Type</th>
            <th>Signal</th>
            <th>Probability</th>
            <th>Ensemble Weight</th>
            <th>Historical Acc</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {models.map((m, idx) => (
            <tr key={idx} className={cn(m.status === 'CHAMPION' && 'bg-terminal-cyan/5')}>
              <td className="font-semibold text-terminal-text flex items-center gap-1.5">
                {m.name}
                {m.status === 'CHAMPION' && (
                  <span className="text-3xs px-1 py-0.2 bg-terminal-cyan/20 text-terminal-cyan rounded border border-terminal-cyan/40 font-mono">
                    CHAMPION
                  </span>
                )}
              </td>
              <td className="text-terminal-muted text-2xs">{m.category}</td>
              <td>
                <StatusBadge variant={m.direction} size="xs" />
              </td>
              <td className="font-bold">{(m.probability * 100).toFixed(0)}%</td>
              <td>
                <div className="flex items-center gap-1.5">
                  <div className="w-12 h-1.5 bg-terminal-border rounded-full overflow-hidden">
                    <div
                      className="h-full bg-terminal-cyan rounded-full"
                      style={{ width: `${m.weight * 100 * 3}%` }}
                    />
                  </div>
                  <span>{(m.weight * 100).toFixed(0)}%</span>
                </div>
              </td>
              <td>{formatPercent(m.accuracy * 100, 1, false)}</td>
              <td>
                <StatusBadge variant={m.status} size="xs" />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
