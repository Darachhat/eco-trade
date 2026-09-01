import React from 'react';
import { Signal } from '../../types/signal';
import { StatusBadge } from '../common/StatusBadge';
import { formatPrice } from '../../lib/formatters/formatters';
import { ArrowUpRight, ArrowDownRight, ShieldCheck, Zap, Activity, Play } from 'lucide-react';
import { cn } from '../../lib/utils';

interface SignalCardProps {
  signal: Signal;
  onExplainClick?: (signal: Signal) => void;
  onTradeClick?: (signal: Signal) => void;
  compact?: boolean;
}

export const SignalCard: React.FC<SignalCardProps> = ({
  signal,
  onExplainClick,
  onTradeClick,
  compact = false,
}) => {
  const isLong = signal.direction === 'LONG';
  const isShort = signal.direction === 'SHORT';

  return (
    <div className="terminal-panel p-3.5 flex flex-col justify-between hover:border-terminal-cyan/50 transition-colors">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-terminal-border/70 pb-2 mb-2.5">
        <div className="flex items-center gap-2">
          <span className="font-mono font-bold text-sm text-terminal-text">{signal.symbol}</span>
          <span className="font-mono text-2xs px-1.5 py-0.5 bg-terminal-surface rounded text-terminal-muted">
            {signal.timeframe}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <StatusBadge variant={signal.status} pulse={signal.status === 'VALID'} />
          <StatusBadge variant={signal.direction} />
        </div>
      </div>

      {/* Main Stats Grid */}
      <div className="grid grid-cols-3 gap-2 font-mono text-xs mb-3">
        <div className="terminal-card p-2 bg-terminal-surface/30">
          <span className="text-3xs uppercase tracking-wider text-terminal-muted block">Confidence</span>
          <span className="font-bold text-sm text-terminal-cyan">{signal.confidence}%</span>
        </div>
        <div className="terminal-card p-2 bg-terminal-surface/30">
          <span className="text-3xs uppercase tracking-wider text-terminal-muted block">Agreement</span>
          <span className="font-bold text-sm text-terminal-bull">{signal.agreement}%</span>
        </div>
        <div className="terminal-card p-2 bg-terminal-surface/30">
          <span className="text-3xs uppercase tracking-wider text-terminal-muted block">Risk/Reward</span>
          <span className="font-bold text-sm text-terminal-text">{signal.riskRewardRatio}R</span>
        </div>
      </div>

      {/* Price Targets Ladder */}
      <div className="space-y-1.5 font-mono text-2xs mb-3 bg-terminal-bg/60 p-2.5 rounded border border-terminal-border/60">
        <div className="flex items-center justify-between">
          <span className="text-terminal-muted">Entry Zone:</span>
          <span className="font-semibold text-terminal-text">
            {formatPrice(signal.entryZoneMin, signal.symbol)} — {formatPrice(signal.entryZoneMax, signal.symbol)}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-terminal-bear">Stop Loss (SL):</span>
          <span className="font-semibold text-terminal-bear">
            {formatPrice(signal.stopLoss, signal.symbol)}
          </span>
        </div>
        <div className="flex items-center justify-between text-terminal-bull">
          <span>Take Profit (TP1 / TP2 / TP3):</span>
          <span className="font-semibold">
            {formatPrice(signal.tp1, signal.symbol)} | {formatPrice(signal.tp2, signal.symbol)} | {formatPrice(signal.tp3, signal.symbol)}
          </span>
        </div>
      </div>

      {/* Footer Info & Actions */}
      <div className="flex items-center justify-between pt-2 border-t border-terminal-border/70 text-2xs font-mono gap-2">
        <div className="flex items-center gap-1.5 text-terminal-muted truncate">
          <Activity className="w-3.5 h-3.5 text-terminal-cyan shrink-0" />
          <span className="truncate">Regime: <strong className="text-terminal-text">{signal.regime.replace(/_/g, ' ')}</strong></span>
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          {onExplainClick && (
            <button
              onClick={() => onExplainClick(signal)}
              className="px-2 py-1 bg-terminal-surface hover:bg-terminal-elevated text-terminal-cyan hover:text-white border border-terminal-cyan/30 rounded text-2xs transition-colors flex items-center gap-1 font-semibold"
            >
              <Zap className="w-3 h-3" />
              Explain
            </button>
          )}

          {onTradeClick && (
            <button
              onClick={() => onTradeClick(signal)}
              className={cn(
                'px-2.5 py-1 rounded text-2xs font-bold transition-all flex items-center gap-1 uppercase tracking-wider',
                isLong
                  ? 'bg-terminal-bull hover:bg-emerald-600 text-black shadow-bull'
                  : 'bg-terminal-bear hover:bg-rose-600 text-white shadow-bear'
              )}
            >
              <Play className="w-3 h-3 fill-current" />
              Follow Trade
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
