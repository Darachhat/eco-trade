import React from 'react';
import { RegimeStatus } from '../../types/model';
import { StatusBadge } from '../common/StatusBadge';
import { Compass, Clock, Activity, TrendingUp } from 'lucide-react';
import { cn } from '../../lib/utils';

export const RegimeIndicator: React.FC<{ regime: RegimeStatus; className?: string }> = ({
  regime,
  className,
}) => {
  return (
    <div className={cn('terminal-panel p-3.5 space-y-3', className)}>
      <div className="flex items-center justify-between border-b border-terminal-border/60 pb-2">
        <div className="flex items-center gap-2">
          <Compass className="w-4 h-4 text-terminal-cyan" />
          <span className="text-2xs uppercase tracking-widest font-semibold text-terminal-muted">
            Market Regime Engine (HMM + Volatility)
          </span>
        </div>
        <StatusBadge variant={regime.currentRegime} pulse />
      </div>

      {/* Main Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-xs">
        <div className="terminal-card p-2">
          <span className="text-3xs uppercase text-terminal-muted block">Regime Probability</span>
          <span className="font-bold text-sm text-terminal-bull">{regime.probability}%</span>
        </div>
        <div className="terminal-card p-2">
          <span className="text-3xs uppercase text-terminal-muted block">Trend Strength (ADX)</span>
          <span className="font-bold text-sm text-terminal-cyan">{regime.adx}</span>
        </div>
        <div className="terminal-card p-2">
          <span className="text-3xs uppercase text-terminal-muted block">Volatility State</span>
          <span className="font-bold text-sm text-terminal-text">{regime.volatilityState}</span>
        </div>
        <div className="terminal-card p-2">
          <span className="text-3xs uppercase text-terminal-muted block">Duration</span>
          <span className="font-bold text-sm text-terminal-text">
            {regime.durationHours}h {regime.durationMinutes}m
          </span>
        </div>
      </div>

      {/* Transition Probabilities */}
      <div className="terminal-card p-2.5 font-mono text-xs space-y-1.5 bg-terminal-surface/30">
        <span className="text-3xs uppercase tracking-wider text-terminal-muted block font-semibold">
          Markov Transition Matrix Probabilities
        </span>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1">
          {Object.entries(regime.transitionProbabilities).map(([reg, prob]) => (
            <div key={reg} className="flex justify-between items-center text-2xs p-1 bg-terminal-bg rounded border border-terminal-border/60">
              <span className="text-terminal-muted">{reg.replace(/_/g, ' ')}:</span>
              <span className={cn('font-bold', prob > 0.5 ? 'text-terminal-bull' : 'text-terminal-text')}>
                {(prob * 100).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
