import React, { useState } from 'react';
import { useSignalStore, generateSignalTargets } from '../stores/useSignalStore';
import { useMarketStore } from '../stores/useMarketStore';
import { SignalCard } from '../components/signals/SignalCard';
import { SignalExplainDrawer } from '../components/signals/SignalExplainDrawer';
import { TradeExecutionModal } from '../components/trading/TradeExecutionModal';
import { Signal, SignalDirection, SignalStatus } from '../types/signal';
import { Zap, Filter, RefreshCw } from 'lucide-react';
import { cn } from '../lib/utils';

export const SignalCenter: React.FC = () => {
  const signals = useSignalStore((s) => s.signals);
  const selectedSignalId = useSignalStore((s) => s.selectedSignalId);
  const setSelectedSignalId = useSignalStore((s) => s.setSelectedSignalId);
  const isExplainModalOpen = useSignalStore((s) => s.isExplainModalOpen);
  const setIsExplainModalOpen = useSignalStore((s) => s.setIsExplainModalOpen);
  const filter = useSignalStore((s) => s.filter);
  const setFilter = useSignalStore((s) => s.setFilter);
  const addSignal = useSignalStore((s) => s.addSignal);

  const activeSymbol = useMarketStore((s) => s.activeSymbol);
  const activeTimeframe = useMarketStore((s) => s.activeTimeframe);
  const tickers = useMarketStore((s) => s.tickers);

  const [isGenerating, setIsGenerating] = useState(false);
  const [tradeModalSignal, setTradeModalSignal] = useState<Signal | null>(null);

  const selectedSignal = signals.find((s) => s.id === selectedSignalId) || signals[0];

  const filteredSignals = signals.filter((s) => {
    if (filter.symbol && filter.symbol !== 'ALL' && s.symbol !== filter.symbol) return false;
    if (filter.direction && filter.direction !== 'ALL' && s.direction !== filter.direction) return false;
    if (filter.status && filter.status !== 'ALL' && s.status !== filter.status) return false;
    return true;
  });

  const handleExplainClick = (signal: Signal) => {
    setSelectedSignalId(signal.id);
    setIsExplainModalOpen(true);
  };

  const handleTradeClick = (signal: Signal) => {
    setTradeModalSignal(signal);
  };

  const handleGenerateSignal = () => {
    setIsGenerating(true);
    setTimeout(() => {
      setIsGenerating(false);
      const currentTicker = tickers[activeSymbol] || tickers['BTCUSDT'];
      const curPrice = currentTicker.price;
      const direction: SignalDirection = currentTicker.change24h >= 0 ? 'LONG' : 'SHORT';

      const targets = generateSignalTargets(activeSymbol, curPrice, direction);

      const newSig: Signal = {
        id: `sig-gen-${Date.now()}`,
        symbol: activeSymbol,
        timeframe: activeTimeframe,
        direction,
        status: 'VALID',
        confidence: Number((81 + Math.random() * 8).toFixed(1)),
        agreement: Number((79 + Math.random() * 9).toFixed(1)),
        regime: 'BULL_TRENDING',
        entryZoneMin: targets.entryZoneMin,
        entryZoneMax: targets.entryZoneMax,
        currentPrice: curPrice,
        stopLoss: targets.stopLoss,
        tp1: targets.tp1,
        tp2: targets.tp2,
        tp3: targets.tp3,
        riskRewardRatio: targets.riskRewardRatio,
        mtfConfirmation: true,
        generatedAt: new Date().toISOString(),
        ageMinutes: 0,
        models: signals[0]?.models || [],
        shapContributions: signals[0]?.shapContributions || [],
        keyDrivers: [
          { text: `Real-time Bybit mark price alignment ($${curPrice.toLocaleString()})`, type: 'positive', strength: 'high' },
          { text: 'EMA slope (8 > 21 > 55) bull trend confirmed', type: 'positive', strength: 'high' },
          { text: 'Positive Cumulative Volume Delta flow', type: 'positive', strength: 'medium' },
          { text: 'Funding rate in normal boundary', type: 'positive', strength: 'low' },
        ],
      };
      addSignal(newSig);
    }, 600);
  };

  return (
    <div className="space-y-4 p-3 font-mono">
      {/* Header Banner & Controls */}
      <div className="terminal-panel p-3.5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Zap className="w-5 h-5 text-terminal-cyan" />
          <div>
            <h1 className="text-sm font-bold text-terminal-text uppercase tracking-wider">
              AI Quantitative Signal Center
            </h1>
            <p className="text-2xs text-terminal-muted">
              Live Bybit prices • 1-Click trade follower with automated stop-loss & take-profit execution
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Generate On-Demand Signal */}
          <button
            onClick={handleGenerateSignal}
            disabled={isGenerating}
            className="px-3 py-1.5 bg-terminal-cyan hover:bg-cyan-600 disabled:opacity-50 text-black font-bold text-2xs rounded transition-colors uppercase tracking-wider flex items-center gap-1.5 shadow-cyan-glow"
          >
            {isGenerating ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Zap className="w-3.5 h-3.5" />
            )}
            {isGenerating ? 'Evaluating Models...' : `Generate Signal (${activeSymbol})`}
          </button>
        </div>
      </div>

      {/* Filter Tabs Toolbar */}
      <div className="terminal-panel p-2 flex flex-wrap items-center justify-between gap-2 text-2xs">
        {/* Status Filters */}
        <div className="flex items-center gap-1">
          <span className="text-terminal-muted uppercase tracking-wider font-semibold mr-1 flex items-center gap-1">
            <Filter className="w-3 h-3 text-terminal-cyan" />
            Status:
          </span>
          {['ALL', 'VALID', 'WATCH', 'EXECUTED', 'INVALIDATED', 'CLOSED'].map((st) => (
            <button
              key={st}
              onClick={() => setFilter({ status: st as any })}
              className={cn(
                'px-2 py-0.5 rounded border transition-colors',
                filter.status === st
                  ? 'bg-terminal-elevated text-terminal-cyan border-terminal-cyan font-bold'
                  : 'bg-terminal-bg text-terminal-muted border-terminal-border/60 hover:text-terminal-text'
              )}
            >
              {st}
            </button>
          ))}
        </div>

        {/* Direction Filter */}
        <div className="flex items-center gap-1">
          <span className="text-terminal-muted uppercase tracking-wider font-semibold mr-1">Direction:</span>
          {['ALL', 'LONG', 'SHORT', 'NEUTRAL'].map((dir) => (
            <button
              key={dir}
              onClick={() => setFilter({ direction: dir as any })}
              className={cn(
                'px-2 py-0.5 rounded border transition-colors',
                filter.direction === dir
                  ? 'bg-terminal-elevated text-terminal-cyan border-terminal-cyan font-bold'
                  : 'bg-terminal-bg text-terminal-muted border-terminal-border/60 hover:text-terminal-text'
              )}
            >
              {dir}
            </button>
          ))}
        </div>
      </div>

      {/* Signals Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {filteredSignals.map((signal) => (
          <SignalCard
            key={signal.id}
            signal={signal}
            onExplainClick={handleExplainClick}
            onTradeClick={handleTradeClick}
          />
        ))}
      </div>

      {filteredSignals.length === 0 && (
        <div className="terminal-panel p-12 text-center text-terminal-muted text-xs">
          No signals match current filter criteria.
        </div>
      )}

      {/* Deep Explainability Drawer / Modal */}
      <SignalExplainDrawer
        signal={selectedSignal}
        isOpen={isExplainModalOpen}
        onClose={() => setIsExplainModalOpen(false)}
        onTradeClick={handleTradeClick}
      />

      {/* Interactive 1-Click Trade Execution Modal */}
      <TradeExecutionModal
        signal={tradeModalSignal}
        isOpen={!!tradeModalSignal}
        onClose={() => setTradeModalSignal(null)}
      />
    </div>
  );
};
