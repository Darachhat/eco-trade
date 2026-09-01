import React from 'react';
import { Signal } from '../../types/signal';
import { StatusBadge } from '../common/StatusBadge';
import { ConsensusTable } from './ConsensusTable';
import { SHAPWaterfall } from './SHAPWaterfall';
import { formatCurrency, formatPrice } from '../../lib/formatters/formatters';
import { X, CheckCircle2, AlertCircle, Cpu, Zap, Activity, Play } from 'lucide-react';
import { cn } from '../../lib/utils';

interface SignalExplainDrawerProps {
  signal: Signal | null;
  isOpen: boolean;
  onClose: () => void;
  onTradeClick?: (signal: Signal) => void;
}

export const SignalExplainDrawer: React.FC<SignalExplainDrawerProps> = ({
  signal,
  isOpen,
  onClose,
  onTradeClick,
}) => {
  if (!isOpen || !signal) return null;

  const isLong = signal.direction === 'LONG';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in font-mono">
      <div className="bg-terminal-panel border border-terminal-border rounded-lg max-w-4xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-terminal-border flex items-center justify-between bg-terminal-surface/40 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded bg-terminal-cyan/10 border border-terminal-cyan/40 flex items-center justify-center text-terminal-cyan">
              <Cpu className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-bold text-terminal-text uppercase tracking-wider">
                  AI Signal Explainability — {signal.symbol} ({signal.timeframe})
                </h2>
                <StatusBadge variant={signal.direction} />
                <StatusBadge variant={signal.status} />
              </div>
              <p className="text-3xs text-terminal-muted">
                Signal ID: <span className="text-terminal-dim">{signal.id}</span> • Generated {signal.ageMinutes}m ago • Regime: <strong className="text-terminal-text">{signal.regime}</strong>
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded text-terminal-muted hover:text-terminal-text hover:bg-terminal-elevated transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body Content */}
        <div className="p-4 overflow-y-auto space-y-4 text-xs">
          {/* 1. Summary Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
            <div className="terminal-card p-2.5">
              <span className="text-3xs text-terminal-muted uppercase tracking-wider block">Ensemble Confidence</span>
              <span className="text-base font-bold text-terminal-cyan">{signal.confidence}%</span>
            </div>
            <div className="terminal-card p-2.5">
              <span className="text-3xs text-terminal-muted uppercase tracking-wider block">Model Agreement</span>
              <span className="text-base font-bold text-terminal-bull">{signal.agreement}%</span>
            </div>
            <div className="terminal-card p-2.5">
              <span className="text-3xs text-terminal-muted uppercase tracking-wider block">Risk / Reward (R:R)</span>
              <span className="text-base font-bold text-terminal-text">{signal.riskRewardRatio}R</span>
            </div>
            <div className="terminal-card p-2.5">
              <span className="text-3xs text-terminal-muted uppercase tracking-wider block">MTF Confirmation</span>
              <span className="text-xs font-bold text-terminal-bull">
                {signal.mtfConfirmation ? '✓ 5m/15m/1h ALIGNED' : '⚠ DIVERGING'}
              </span>
            </div>
          </div>

          {/* 2. Key Decision Drivers (Heuristics & Orderflow) */}
          <div className="terminal-panel p-3 space-y-2">
            <div className="flex items-center gap-1.5 text-2xs uppercase tracking-widest text-terminal-muted font-semibold">
              <Zap className="w-3 h-3 text-terminal-cyan" />
              <span>Key Decision Drivers (Heuristics & Flow)</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-2xs">
              {signal.keyDrivers.map((driver, idx) => (
                <div
                  key={idx}
                  className={cn(
                    'p-2 rounded border flex items-center gap-2',
                    driver.type === 'positive'
                      ? 'bg-terminal-bull/5 border-terminal-bull/30 text-terminal-bull'
                      : 'bg-terminal-bear/5 border-terminal-bear/30 text-terminal-bear'
                  )}
                >
                  {driver.type === 'positive' ? (
                    <CheckCircle2 className="w-4 h-4 shrink-0" />
                  ) : (
                    <AlertCircle className="w-4 h-4 shrink-0" />
                  )}
                  <span className="font-medium text-terminal-text">{driver.text}</span>
                </div>
              ))}
            </div>
          </div>

          {/* 3. 10-Model Consensus Breakdown */}
          <div className="terminal-panel p-3 space-y-2">
            <div className="flex items-center justify-between text-2xs uppercase tracking-widest text-terminal-muted font-semibold">
              <span>Multi-Model Consensus Votes & Weights (10 Quantitative Models)</span>
              <span className="text-terminal-cyan">Ensemble Mode: Weighted Bayesian Voting</span>
            </div>
            <ConsensusTable models={signal.models} />
          </div>

          {/* 4. SHAP Feature Contribution Waterfall */}
          <div className="terminal-panel p-3 space-y-2">
            <div className="flex items-center justify-between text-2xs uppercase tracking-widest text-terminal-muted font-semibold">
              <span>SHAP Feature Attribution (Local Model Explanation)</span>
              <span className="text-terminal-dim">TreeSHAP + KernelSHAP Estimators</span>
            </div>
            <SHAPWaterfall contributions={signal.shapContributions} />
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-3 border-t border-terminal-border text-2xs text-terminal-muted font-mono shrink-0 bg-terminal-surface/30">
          <span>* Predictions are probabilistic decision-support outputs based on Bybit market data.</span>
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-4 py-1.5 bg-terminal-surface hover:bg-terminal-elevated text-terminal-text rounded font-semibold transition-colors"
            >
              Close
            </button>
            {onTradeClick && (
              <button
                onClick={() => {
                  onClose();
                  onTradeClick(signal);
                }}
                className={cn(
                  'px-4 py-1.5 rounded font-bold text-2xs transition-all flex items-center gap-1.5 uppercase tracking-wider',
                  isLong ? 'bg-terminal-bull text-black hover:bg-emerald-600 shadow-bull' : 'bg-terminal-bear text-white hover:bg-rose-600 shadow-bear'
                )}
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                Follow Signal & Open Position
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
