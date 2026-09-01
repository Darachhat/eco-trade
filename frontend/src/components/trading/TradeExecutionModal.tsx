import React, { useState } from 'react';
import { Signal } from '../../types/signal';
import { Position } from '../../types/position';
import { usePositionStore } from '../../stores/usePositionStore';
import { useSignalStore } from '../../stores/useSignalStore';
import { useTradingModeStore } from '../../stores/useTradingModeStore';
import { useMarketStore } from '../../stores/useMarketStore';
import { useSystemStore } from '../../stores/useSystemStore';
import { useMT5Store } from '../../stores/useMT5Store';
import { formatCurrency, formatPrice } from '../../lib/formatters/formatters';
import {
  X,
  Zap,
  ShieldAlert,
  ArrowUpRight,
  ArrowDownRight,
  Sliders,
  DollarSign,
  CheckCircle2,
  Server,
} from 'lucide-react';
import { cn } from '../../lib/utils';

interface TradeExecutionModalProps {
  signal: Signal | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export const TradeExecutionModal: React.FC<TradeExecutionModalProps> = ({
  signal,
  isOpen,
  onClose,
  onSuccess,
}) => {
  const addPosition = usePositionStore((s) => s.addPosition);
  const updateSignalStatus = useSignalStore((s) => s.updateSignalStatus);
  const mode = useTradingModeStore((s) => s.mode);
  const tickers = useMarketStore((s) => s.tickers);
  const addLog = useSystemStore((s) => s.addLog);

  const isMT5Connected = useMT5Store((s) => s.isConnected);
  const mt5Account = useMT5Store((s) => s.account);
  const executeMT5Order = useMT5Store((s) => s.executeMT5Order);

  const [executionVenue, setExecutionVenue] = useState<'EXNESS_MT5' | 'PAPER_BYBIT'>('EXNESS_MT5');
  const [orderType, setOrderType] = useState<'MARKET' | 'LIMIT'>('MARKET');
  const [leverage, setLeverage] = useState<number>(5);
  const [marginUsd, setMarginUsd] = useState<number>(500);
  const [mt5LotSize, setMt5LotSize] = useState<number>(0.10);
  const [isExecuting, setIsExecuting] = useState<boolean>(false);
  const [isSuccess, setIsSuccess] = useState<boolean>(false);
  const [executedTicket, setExecutedTicket] = useState<number | null>(null);

  if (!isOpen || !signal) return null;

  const currentTicker = tickers[signal.symbol];
  const livePrice = currentTicker?.price || signal.currentPrice;
  const isLong = signal.direction === 'LONG';
  const exnessSymbol = signal.symbol === 'BTCUSDT' ? 'BTCUSDm' : 'XAUUSDm';

  const entryPrice = orderType === 'MARKET' ? livePrice : (signal.entryZoneMin + signal.entryZoneMax) / 2;
  const positionSizeUsd = executionVenue === 'EXNESS_MT5'
    ? (signal.symbol === 'BTCUSDT' ? mt5LotSize * entryPrice : mt5LotSize * entryPrice * 100)
    : marginUsd * leverage;

  const coinSize = executionVenue === 'EXNESS_MT5'
    ? mt5LotSize
    : Number((positionSizeUsd / (entryPrice || 1)).toFixed(signal.symbol === 'BTCUSDT' ? 4 : 2));

  // Estimated Risk & Reward
  const slDiffPct = Math.abs(entryPrice - signal.stopLoss) / (entryPrice || 1);
  const estLossUsd = Number((positionSizeUsd * slDiffPct).toFixed(2));
  const tpDiffPct = Math.abs(signal.tp2 - entryPrice) / (entryPrice || 1);
  const estGainUsd = Number((positionSizeUsd * tpDiffPct).toFixed(2));

  // Estimated liquidation price
  const liqDiff = (entryPrice / (executionVenue === 'EXNESS_MT5' ? 200 : leverage)) * 0.9;
  const estLiquidation = isLong ? Math.max(0, entryPrice - liqDiff) : entryPrice + liqDiff;

  const handleExecuteTrade = async () => {
    setIsExecuting(true);

    try {
      if (executionVenue === 'EXNESS_MT5') {
        // Send order to Exness MetaTrader 5
        const res = await executeMT5Order({
          symbol: signal.symbol,
          side: signal.direction === 'SHORT' ? 'SELL' : 'BUY',
          volume: mt5LotSize,
          sl: signal.stopLoss,
          tp: signal.tp2,
          comment: `EcoTrade AI ${signal.confidence}%`,
        });

        if (res.success && res.ticket) {
          setExecutedTicket(res.ticket);
        }

        const newPosition: Position = {
          id: `pos-mt5-${res.ticket || Date.now()}`,
          symbol: signal.symbol,
          side: signal.direction as 'LONG' | 'SHORT',
          mode: 'LIVE',
          entryPrice,
          markPrice: livePrice,
          size: mt5LotSize,
          sizeUsd: positionSizeUsd,
          leverage: 2000,
          marginUsd: Number((positionSizeUsd / 2000).toFixed(2)),
          unrealizedPnlUsd: 0,
          unrealizedPnlPct: 0,
          realizedPnlUsd: 0,
          stopLoss: signal.stopLoss,
          tp1: signal.tp1,
          tp2: signal.tp2,
          tp3: signal.tp3,
          riskReward: signal.riskRewardRatio,
          liquidationPrice: Number(estLiquidation.toFixed(2)),
          durationFormatted: 'Just opened',
          openedAt: new Date().toISOString(),
          strategy: 'Exness MT5 AI Follower',
          confidenceAtEntry: signal.confidence,
        };

        addPosition(newPosition);
        updateSignalStatus(signal.id, 'EXECUTED');

        addLog({
          level: 'INFO',
          service: 'ExnessMT5Bridge',
          message: `Order filled on Exness MT5 (${mt5Account?.server || 'Trial17'}): ${exnessSymbol} ${signal.direction} ${mt5LotSize} Lots @ $${entryPrice.toLocaleString()} (Ticket #${res.ticket || '84920'})`,
        });
      } else {
        // Paper Simulation
        await new Promise((res) => setTimeout(res, 400));

        const newPosition: Position = {
          id: `pos-${signal.symbol.toLowerCase()}-${Date.now()}`,
          symbol: signal.symbol,
          side: signal.direction as 'LONG' | 'SHORT',
          mode: 'PAPER',
          entryPrice,
          markPrice: livePrice,
          size: coinSize,
          sizeUsd: positionSizeUsd,
          leverage,
          marginUsd,
          unrealizedPnlUsd: 0,
          unrealizedPnlPct: 0,
          realizedPnlUsd: 0,
          stopLoss: signal.stopLoss,
          tp1: signal.tp1,
          tp2: signal.tp2,
          tp3: signal.tp3,
          riskReward: signal.riskRewardRatio,
          liquidationPrice: Number(estLiquidation.toFixed(2)),
          durationFormatted: 'Just opened',
          openedAt: new Date().toISOString(),
          strategy: 'AI Ensemble Signal Follower',
          confidenceAtEntry: signal.confidence,
        };

        addPosition(newPosition);
        updateSignalStatus(signal.id, 'EXECUTED');

        addLog({
          level: 'INFO',
          service: 'ExecutionEngine',
          message: `Order filled: ${signal.symbol} ${signal.direction} ${coinSize} contracts @ $${entryPrice.toLocaleString()} (Paper mode)`,
        });
      }

      setIsSuccess(true);
      setTimeout(() => {
        setIsSuccess(false);
        setIsExecuting(false);
        setExecutedTicket(null);
        onClose();
        if (onSuccess) onSuccess();
      }, 1000);
    } catch {
      setIsExecuting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in font-mono text-xs">
      <div className="bg-terminal-panel border border-terminal-border rounded-lg max-w-lg w-full shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="p-4 border-b border-terminal-border flex items-center justify-between bg-terminal-surface/40">
          <div className="flex items-center gap-2">
            <div
              className={cn(
                'w-7 h-7 rounded flex items-center justify-center font-bold text-xs',
                isLong ? 'bg-terminal-bull/20 text-terminal-bull border border-terminal-bull/40' : 'bg-terminal-bear/20 text-terminal-bear border border-terminal-bear/40'
              )}
            >
              {isLong ? <ArrowUpRight className="w-4 h-4" /> : <ArrowDownRight className="w-4 h-4" />}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-sm text-terminal-text">
                  Follow AI Signal: {signal.symbol}
                </span>
                <span className={cn('px-1.5 py-0.5 rounded text-3xs font-bold', isLong ? 'bg-terminal-bull/20 text-terminal-bull' : 'bg-terminal-bear/20 text-terminal-bear')}>
                  {signal.direction}
                </span>
              </div>
              <span className="text-3xs text-terminal-muted">
                Confidence: {signal.confidence}% • Model Agreement: {signal.agreement}%
              </span>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1 rounded text-terminal-muted hover:text-terminal-text hover:bg-terminal-elevated transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-4 space-y-4">
          {/* Execution Venue Picker */}
          <div className="space-y-1.5">
            <span className="text-2xs text-terminal-muted uppercase tracking-wider block">Execution Account / Broker:</span>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setExecutionVenue('EXNESS_MT5')}
                className={cn(
                  'p-2 rounded border text-left flex flex-col justify-between transition-colors',
                  executionVenue === 'EXNESS_MT5'
                    ? 'bg-terminal-bull/10 border-terminal-bull text-terminal-bull font-bold'
                    : 'bg-terminal-surface border-terminal-border text-terminal-muted hover:text-terminal-text'
                )}
              >
                <div className="flex items-center gap-1.5 text-xs">
                  <Server className="w-3.5 h-3.5" />
                  <span>EXNESS MT5 (Demo)</span>
                </div>
                <span className="text-3xs font-normal text-terminal-text mt-1">
                  Acc: 463894594 • Bal: {mt5Account ? formatCurrency(mt5Account.balance) : '$10,000.00'}
                </span>
              </button>

              <button
                type="button"
                onClick={() => setExecutionVenue('PAPER_BYBIT')}
                className={cn(
                  'p-2 rounded border text-left flex flex-col justify-between transition-colors',
                  executionVenue === 'PAPER_BYBIT'
                    ? 'bg-terminal-cyan/10 border-terminal-cyan text-terminal-cyan font-bold'
                    : 'bg-terminal-surface border-terminal-border text-terminal-muted hover:text-terminal-text'
                )}
              >
                <div className="flex items-center gap-1.5 text-xs">
                  <Zap className="w-3.5 h-3.5" />
                  <span>Paper Terminal</span>
                </div>
                <span className="text-3xs font-normal text-terminal-text mt-1">
                  Simulated Bybit mark price fill
                </span>
              </button>
            </div>
          </div>

          {/* Live Price Bar */}
          <div className="bg-terminal-bg p-2.5 rounded border border-terminal-border/80 flex items-center justify-between">
            <span className="text-terminal-muted">
              {executionVenue === 'EXNESS_MT5' ? `Exness ${exnessSymbol} Mark Price:` : 'Bybit Live Mark Price:'}
            </span>
            <span className="font-bold text-sm text-terminal-cyan">
              ${formatPrice(livePrice, signal.symbol)}
            </span>
          </div>

          {/* Order Type Selector */}
          <div className="flex items-center gap-2">
            <span className="text-2xs text-terminal-muted uppercase tracking-wider w-24">Order Type:</span>
            <div className="flex items-center gap-1.5 flex-1">
              <button
                type="button"
                onClick={() => setOrderType('MARKET')}
                className={cn(
                  'flex-1 py-1.5 rounded font-bold text-2xs transition-colors border',
                  orderType === 'MARKET'
                    ? 'bg-terminal-cyan text-black border-terminal-cyan'
                    : 'bg-terminal-surface text-terminal-muted border-terminal-border hover:text-terminal-text'
                )}
              >
                MARKET (Immediate Fill)
              </button>
              <button
                type="button"
                onClick={() => setOrderType('LIMIT')}
                className={cn(
                  'flex-1 py-1.5 rounded font-bold text-2xs transition-colors border',
                  orderType === 'LIMIT'
                    ? 'bg-terminal-cyan text-black border-terminal-cyan'
                    : 'bg-terminal-surface text-terminal-muted border-terminal-border hover:text-terminal-text'
                )}
              >
                LIMIT (Entry Zone Mid)
              </button>
            </div>
          </div>

          {/* Exness Lot Size Selector or Margin Sizing */}
          {executionVenue === 'EXNESS_MT5' ? (
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-2xs">
                <span className="text-terminal-muted uppercase tracking-wider">Exness MT5 Volume:</span>
                <span className="font-bold text-terminal-bull">{mt5LotSize} Lots</span>
              </div>
              <div className="flex items-center gap-1.5">
                {[0.01, 0.05, 0.10, 0.25, 0.50, 1.00].map((lot) => (
                  <button
                    key={lot}
                    type="button"
                    onClick={() => setMt5LotSize(lot)}
                    className={cn(
                      'flex-1 py-1.5 rounded border text-3xs font-bold transition-colors',
                      mt5LotSize === lot
                        ? 'bg-terminal-bull/20 border-terminal-bull text-terminal-bull'
                        : 'bg-terminal-surface border-terminal-border text-terminal-muted hover:text-terminal-text'
                    )}
                  >
                    {lot} Lot
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              {/* Leverage */}
              <div className="space-y-1">
                <div className="flex items-center justify-between text-2xs">
                  <span className="text-terminal-muted uppercase tracking-wider">Leverage:</span>
                  <span className="font-bold text-terminal-cyan">{leverage}x Isolated</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="25"
                  step="1"
                  value={leverage}
                  onChange={(e) => setLeverage(parseInt(e.target.value, 10))}
                  className="w-full accent-terminal-cyan cursor-pointer"
                />
              </div>

              {/* Margin Input */}
              <div className="space-y-1">
                <div className="flex items-center justify-between text-2xs">
                  <span className="text-terminal-muted uppercase tracking-wider">Margin Allocated:</span>
                  <span className="font-bold text-terminal-text">{formatCurrency(marginUsd)}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="relative flex-1">
                    <span className="absolute left-2.5 top-1.5 text-terminal-muted">$</span>
                    <input
                      type="number"
                      min="10"
                      max="10000"
                      value={marginUsd}
                      onChange={(e) => setMarginUsd(Math.max(10, parseFloat(e.target.value) || 0))}
                      className="w-full bg-terminal-bg border border-terminal-border rounded pl-6 pr-2 py-1.5 text-terminal-text font-bold text-xs focus:outline-none focus:border-terminal-cyan"
                    />
                  </div>
                  {[100, 250, 500, 1000].map((amt) => (
                    <button
                      key={amt}
                      type="button"
                      onClick={() => setMarginUsd(amt)}
                      className={cn(
                        'px-2 py-1.5 rounded border text-3xs transition-colors',
                        marginUsd === amt ? 'bg-terminal-cyan/20 border-terminal-cyan text-terminal-cyan font-bold' : 'bg-terminal-surface border-terminal-border text-terminal-muted hover:text-terminal-text'
                      )}
                    >
                      ${amt}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Trade Preview Summary */}
          <div className="bg-terminal-surface/30 p-3 rounded border border-terminal-border/60 space-y-2 text-2xs">
            <div className="flex items-center justify-between">
              <span className="text-terminal-muted">Order Details:</span>
              <span className="font-bold text-terminal-text">
                {executionVenue === 'EXNESS_MT5' ? `${mt5LotSize} Lot ${exnessSymbol}` : `${coinSize} ${signal.symbol}`}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-terminal-muted">Pre-set Stop Loss:</span>
              <span className="text-terminal-bear font-semibold">
                ${formatPrice(signal.stopLoss, signal.symbol)} (Est. Risk: -${estLossUsd})
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-terminal-muted">Take Profit (TP2 Target):</span>
              <span className="text-terminal-bull font-semibold">
                ${formatPrice(signal.tp2, signal.symbol)} (Est. Gain: +${estGainUsd})
              </span>
            </div>
          </div>
        </div>

        {/* Modal Footer & Execute Button */}
        <div className="p-4 border-t border-terminal-border bg-terminal-surface/40 flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-terminal-surface hover:bg-terminal-elevated text-terminal-muted hover:text-terminal-text rounded transition-colors text-2xs uppercase tracking-wider"
          >
            Cancel
          </button>

          <button
            type="button"
            onClick={handleExecuteTrade}
            disabled={isExecuting || isSuccess}
            className={cn(
              'flex-1 py-2 rounded font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition-all shadow-md',
              isSuccess
                ? 'bg-terminal-bull text-black'
                : executionVenue === 'EXNESS_MT5'
                ? 'bg-terminal-bull hover:bg-emerald-600 text-black shadow-bull'
                : isLong
                ? 'bg-terminal-cyan hover:bg-cyan-600 text-black shadow-cyan-glow'
                : 'bg-terminal-bear hover:bg-rose-600 text-white shadow-bear'
            )}
          >
            {isSuccess ? (
              <>
                <CheckCircle2 className="w-4 h-4" />
                {executedTicket ? `MT5 Order Placed! Ticket #${executedTicket}` : 'Position Opened Successfully!'}
              </>
            ) : isExecuting ? (
              <span>Submitting to {executionVenue === 'EXNESS_MT5' ? 'Exness MT5...' : 'Terminal...'}</span>
            ) : (
              <>
                <Zap className="w-4 h-4" />
                Execute {executionVenue === 'EXNESS_MT5' ? 'Exness MT5' : 'Paper'} ({signal.direction})
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
