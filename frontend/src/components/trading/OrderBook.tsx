import React from 'react';
import { useMarketStore } from '../../stores/useMarketStore';
import { formatPrice } from '../../lib/formatters/formatters';
import { cn } from '../../lib/utils';

export const OrderBook: React.FC<{ className?: string; depth?: number }> = ({
  className,
  depth = 12,
}) => {
  const orderBook = useMarketStore((s) => s.orderBook);
  const activeSymbol = useMarketStore((s) => s.activeSymbol);

  const asks = orderBook.asks.slice(0, depth).reverse();
  const bids = orderBook.bids.slice(0, depth);

  const imbalancePct = Math.round(Math.abs(orderBook.imbalance) * 100);
  const isBidHeavy = orderBook.imbalance > 0;

  return (
    <div className={cn('terminal-panel flex flex-col h-full', className)}>
      <div className="terminal-header">
        <span>Order Book (L2 Depth)</span>
        <div className="flex items-center gap-2">
          <span className="font-mono text-terminal-dim">Spread:</span>
          <span className="font-mono text-terminal-text">
            {formatPrice(orderBook.spread, activeSymbol)} ({orderBook.spreadBps.toFixed(2)} bps)
          </span>
        </div>
      </div>

      {/* Header Columns */}
      <div className="grid grid-cols-3 px-2.5 py-1 text-2xs uppercase tracking-wider text-terminal-muted border-b border-terminal-border/60 bg-terminal-surface/30 font-mono">
        <span>Price (USDT)</span>
        <span className="text-right">Size</span>
        <span className="text-right">Total</span>
      </div>

      <div className="flex-1 flex flex-col justify-between overflow-hidden font-mono text-xs select-none">
        {/* Asks (Sells) */}
        <div className="flex-1 flex flex-col justify-end space-y-0.5 py-1">
          {asks.map((ask, idx) => (
            <div key={`ask-${idx}`} className="relative grid grid-cols-3 px-2.5 py-0.5 hover:bg-terminal-elevated/40">
              <div
                className="absolute inset-y-0 right-0 bg-terminal-bearDim/40 pointer-events-none transition-all duration-150"
                style={{ width: `${ask.percent}%` }}
              />
              <span className="text-terminal-bear z-10">{formatPrice(ask.price, activeSymbol)}</span>
              <span className="text-right text-terminal-text z-10">{ask.size.toFixed(3)}</span>
              <span className="text-right text-terminal-muted z-10">{ask.total.toFixed(2)}</span>
            </div>
          ))}
        </div>

        {/* Mid Price Bar */}
        <div className="px-2.5 py-1.5 bg-terminal-surface/80 border-y border-terminal-border flex items-center justify-between font-bold">
          <div className="flex items-center gap-2">
            <span className="text-terminal-text text-sm">
              {formatPrice(orderBook.midPrice, activeSymbol)}
            </span>
            <span className="text-2xs text-terminal-muted font-normal">MID</span>
          </div>
          <div className="flex items-center gap-1.5 text-2xs">
            <span className="text-terminal-dim">Imbalance:</span>
            <span className={cn('font-semibold', isBidHeavy ? 'text-terminal-bull' : 'text-terminal-bear')}>
              {isBidHeavy ? `+${imbalancePct}% BIDS` : `-${imbalancePct}% ASKS`}
            </span>
          </div>
        </div>

        {/* Bids (Buys) */}
        <div className="flex-1 flex flex-col justify-start space-y-0.5 py-1">
          {bids.map((bid, idx) => (
            <div key={`bid-${idx}`} className="relative grid grid-cols-3 px-2.5 py-0.5 hover:bg-terminal-elevated/40">
              <div
                className="absolute inset-y-0 right-0 bg-terminal-bullDim/40 pointer-events-none transition-all duration-150"
                style={{ width: `${bid.percent}%` }}
              />
              <span className="text-terminal-bull z-10">{formatPrice(bid.price, activeSymbol)}</span>
              <span className="text-right text-terminal-text z-10">{bid.size.toFixed(3)}</span>
              <span className="text-right text-terminal-muted z-10">{bid.total.toFixed(2)}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Imbalance Visual Meter at bottom */}
      <div className="p-2 border-t border-terminal-border/60 bg-terminal-surface/20">
        <div className="flex justify-between text-3xs uppercase font-mono text-terminal-dim mb-1">
          <span className="text-terminal-bull">Bid Flow ({isBidHeavy ? 50 + imbalancePct / 2 : 50 - imbalancePct / 2}%)</span>
          <span className="text-terminal-bear">Ask Flow ({!isBidHeavy ? 50 + imbalancePct / 2 : 50 - imbalancePct / 2}%)</span>
        </div>
        <div className="h-1 w-full bg-terminal-border rounded-full flex overflow-hidden">
          <div
            className="bg-terminal-bull h-full transition-all duration-200"
            style={{ width: `${isBidHeavy ? 50 + imbalancePct / 2 : 50 - imbalancePct / 2}%` }}
          />
          <div
            className="bg-terminal-bear h-full transition-all duration-200"
            style={{ width: `${!isBidHeavy ? 50 + imbalancePct / 2 : 50 - imbalancePct / 2}%` }}
          />
        </div>
      </div>
    </div>
  );
};
