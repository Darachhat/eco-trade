import React from 'react';
import { ModelInfo } from '../../types/model';
import { StatusBadge } from '../common/StatusBadge';
import { formatPercent } from '../../lib/formatters/formatters';
import { Award, Layers, Clock, Cpu } from 'lucide-react';
import { cn } from '../../lib/utils';

interface ModelCardProps {
  model: ModelInfo;
  isSelected?: boolean;
  onSelect?: (id: string) => void;
}

export const ModelCard: React.FC<ModelCardProps> = ({
  model,
  isSelected = false,
  onSelect,
}) => {
  return (
    <div
      onClick={() => onSelect?.(model.id)}
      className={cn(
        'terminal-panel p-3 cursor-pointer transition-all duration-150 flex flex-col justify-between',
        isSelected ? 'border-terminal-cyan shadow-cyan-glow/20' : 'hover:border-terminal-border/80',
        model.champion && 'bg-terminal-cyan/5 border-terminal-cyan/40'
      )}
    >
      <div>
        {/* Header */}
        <div className="flex items-center justify-between mb-2 pb-2 border-b border-terminal-border/60">
          <div className="flex items-center gap-1.5">
            <Cpu className={cn('w-4 h-4', model.champion ? 'text-terminal-cyan' : 'text-terminal-muted')} />
            <span className="font-mono font-bold text-xs text-terminal-text">{model.name}</span>
            <span className="text-3xs font-mono px-1 py-0.2 bg-terminal-surface text-terminal-muted rounded">
              {model.version}
            </span>
          </div>
          <StatusBadge variant={model.status} size="xs" />
        </div>

        {/* Core Metrics */}
        <div className="grid grid-cols-2 gap-2 font-mono text-xs mb-3">
          <div className="terminal-card p-1.5 bg-terminal-surface/20">
            <span className="text-3xs uppercase text-terminal-muted block">Accuracy</span>
            <span className="font-bold text-terminal-text">
              {formatPercent(model.metrics.accuracy * 100, 1, false)}
            </span>
          </div>
          <div className="terminal-card p-1.5 bg-terminal-surface/20">
            <span className="text-3xs uppercase text-terminal-muted block">Win Rate</span>
            <span className="font-bold text-terminal-bull">
              {formatPercent(model.metrics.winRate * 100, 1, false)}
            </span>
          </div>
          <div className="terminal-card p-1.5 bg-terminal-surface/20">
            <span className="text-3xs uppercase text-terminal-muted block">Sharpe Ratio</span>
            <span className="font-bold text-terminal-cyan">{model.metrics.sharpe.toFixed(2)}</span>
          </div>
          <div className="terminal-card p-1.5 bg-terminal-surface/20">
            <span className="text-3xs uppercase text-terminal-muted block">Profit Factor</span>
            <span className="font-bold text-terminal-text">{model.metrics.profitFactor.toFixed(2)}</span>
          </div>
        </div>

        {/* Ensemble Weight Bar */}
        <div className="space-y-1 font-mono text-2xs mb-2">
          <div className="flex justify-between text-terminal-muted">
            <span>Ensemble Weight</span>
            <span className="font-bold text-terminal-cyan">{(model.weight * 100).toFixed(0)}%</span>
          </div>
          <div className="h-1.5 w-full bg-terminal-border rounded-full overflow-hidden">
            <div
              className={cn(
                'h-full rounded-full transition-all duration-300',
                model.champion ? 'bg-terminal-cyan' : 'bg-terminal-blue'
              )}
              style={{ width: `${model.weight * 100 * 3.5}%` }}
            />
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between text-3xs font-mono text-terminal-dim pt-2 border-t border-terminal-border/60">
        <span>Type: {model.type}</span>
        <span>Trained: {model.lastTrained}</span>
      </div>
    </div>
  );
};
