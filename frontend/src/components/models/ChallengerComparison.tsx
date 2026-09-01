import React from 'react';
import { ModelInfo } from '../../types/model';
import { useModelStore } from '../../stores/useModelStore';
import { StatusBadge } from '../common/StatusBadge';
import { formatPercent } from '../../lib/formatters/formatters';
import { Award, ArrowRight, Check, X, Sliders, Zap } from 'lucide-react';
import { cn } from '../../lib/utils';

export const ChallengerComparison: React.FC = () => {
  const models = useModelStore((s) => s.models);
  const promoteChallenger = useModelStore((s) => s.promoteChallenger);

  const champion = models.find((m) => m.champion) || models[0];
  const challenger = models.find((m) => m.status === 'CHALLENGER') || models[1];

  const handlePromote = () => {
    promoteChallenger(challenger.id);
  };

  return (
    <div className="terminal-panel p-4 space-y-4 font-mono text-xs">
      <div className="flex items-center justify-between border-b border-terminal-border/60 pb-2">
        <div className="flex items-center gap-2">
          <Award className="w-4 h-4 text-terminal-cyan" />
          <span className="text-2xs uppercase tracking-widest font-semibold text-terminal-muted">
            Model Lifecycle Management (Champion vs Challenger Protocol)
          </span>
        </div>
        <span className="text-2xs text-terminal-dim">Automated OOS Validation Active</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Champion Side */}
        <div className="terminal-card p-3.5 space-y-3 bg-terminal-cyan/5 border-terminal-cyan/40">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <Award className="w-4 h-4 text-terminal-cyan" />
              <span className="font-bold text-terminal-cyan text-sm">CURRENT CHAMPION</span>
            </div>
            <StatusBadge variant="CHAMPION" />
          </div>

          <div className="text-xs space-y-1">
            <div className="text-base font-bold text-terminal-text">{champion.name} ({champion.version})</div>
            <div className="text-terminal-muted text-2xs">Architecture: {champion.type}</div>
          </div>

          <div className="grid grid-cols-2 gap-2 pt-1">
            <div className="p-2 bg-terminal-bg/60 rounded border border-terminal-border/40">
              <span className="text-3xs uppercase text-terminal-muted block">Out-of-Sample Sharpe</span>
              <span className="font-bold text-terminal-cyan text-sm">{champion.metrics.sharpe.toFixed(2)}</span>
            </div>
            <div className="p-2 bg-terminal-bg/60 rounded border border-terminal-border/40">
              <span className="text-3xs uppercase text-terminal-muted block">Win Rate</span>
              <span className="font-bold text-terminal-bull text-sm">
                {formatPercent(champion.metrics.winRate * 100, 1, false)}
              </span>
            </div>
            <div className="p-2 bg-terminal-bg/60 rounded border border-terminal-border/40">
              <span className="text-3xs uppercase text-terminal-muted block">Profit Factor</span>
              <span className="font-bold text-terminal-text text-sm">{champion.metrics.profitFactor.toFixed(2)}</span>
            </div>
            <div className="p-2 bg-terminal-bg/60 rounded border border-terminal-border/40">
              <span className="text-3xs uppercase text-terminal-muted block">Max Drawdown</span>
              <span className="font-bold text-terminal-bear text-sm">
                {formatPercent(champion.metrics.maxDrawdown * 100, 1, false)}
              </span>
            </div>
          </div>
        </div>

        {/* Challenger Side */}
        <div className="terminal-card p-3.5 space-y-3 bg-terminal-amber/5 border-terminal-amber/40">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <Zap className="w-4 h-4 text-terminal-amber" />
              <span className="font-bold text-terminal-amber text-sm">ACTIVE CHALLENGER</span>
            </div>
            <StatusBadge variant="CHALLENGER" />
          </div>

          <div className="text-xs space-y-1">
            <div className="text-base font-bold text-terminal-text">{challenger.name} ({challenger.version})</div>
            <div className="text-terminal-muted text-2xs">Architecture: {challenger.type}</div>
          </div>

          <div className="grid grid-cols-2 gap-2 pt-1">
            <div className="p-2 bg-terminal-bg/60 rounded border border-terminal-border/40">
              <span className="text-3xs uppercase text-terminal-muted block">Out-of-Sample Sharpe</span>
              <span className="font-bold text-terminal-amber text-sm">{challenger.metrics.sharpe.toFixed(2)}</span>
            </div>
            <div className="p-2 bg-terminal-bg/60 rounded border border-terminal-border/40">
              <span className="text-3xs uppercase text-terminal-muted block">Win Rate</span>
              <span className="font-bold text-terminal-bull text-sm">
                {formatPercent(challenger.metrics.winRate * 100, 1, false)}
              </span>
            </div>
            <div className="p-2 bg-terminal-bg/60 rounded border border-terminal-border/40">
              <span className="text-3xs uppercase text-terminal-muted block">Profit Factor</span>
              <span className="font-bold text-terminal-text text-sm">{challenger.metrics.profitFactor.toFixed(2)}</span>
            </div>
            <div className="p-2 bg-terminal-bg/60 rounded border border-terminal-border/40">
              <span className="text-3xs uppercase text-terminal-muted block">Max Drawdown</span>
              <span className="font-bold text-terminal-bear text-sm">
                {formatPercent(challenger.metrics.maxDrawdown * 100, 1, false)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Promotion Action Bar */}
      <div className="flex items-center justify-between p-3 bg-terminal-surface/40 rounded border border-terminal-border/80">
        <div className="text-2xs text-terminal-muted">
          <span>Promotion Rule: Challenger Sharpe &gt; Champion Sharpe + 0.15 across 200+ test samples.</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handlePromote}
            className="px-3 py-1.5 bg-terminal-cyan hover:bg-cyan-600 text-black font-bold rounded transition-colors text-2xs uppercase tracking-wider flex items-center gap-1"
          >
            <Check className="w-3.5 h-3.5" />
            Promote Challenger to Champion
          </button>
        </div>
      </div>
    </div>
  );
};
