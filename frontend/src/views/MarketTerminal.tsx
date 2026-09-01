import React from 'react';
import { useMarketStore } from '../stores/useMarketStore';
import { Timeframe } from '../types/market';
import { TradingViewChart } from '../components/charts/TradingViewChart';
import { OrderBook } from '../components/trading/OrderBook';
import { CVDChart } from '../components/trading/CVDChart';
import { FundingOIWidget } from '../components/trading/FundingOIWidget';
import { MetricCard } from '../components/common/MetricCard';
import { formatCurrency, formatPercent, formatPrice } from '../lib/formatters/formatters';
import { Sliders, RefreshCw, BarChart2, Eye } from 'lucide-react';
import { cn } from '../lib/utils';

const TIMEFRAMES: Timeframe[] = ['1m', '5m', '15m', '1h', '4h', '1D'];

export const MarketTerminal: React.FC = () => {
  const activeSymbol = useMarketStore((s) => s.activeSymbol);
  const activeTimeframe = useMarketStore((s) => s.activeTimeframe);
  const setActiveTimeframe = useMarketStore((s) => s.setActiveTimeframe);
  const tickers = useMarketStore((s) => s.tickers);
  const indicators = useMarketStore((s) => s.indicators);
  const toggleIndicator = useMarketStore((s) => s.toggleIndicator);
  const refreshCandles = useMarketStore((s) => s.refreshCandles);

  const currentTicker = tickers[activeSymbol] || tickers['BTCUSDT'];

  return (
    <div className="space-y-3 p-3 font-mono">
      {/* 1. TOP MARKET STATS BANNER */}
      <div className="terminal-panel p-3 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold text-terminal-text">{activeSymbol}</span>
              <span className="text-2xs px-2 py-0.5 bg-terminal-cyan/10 text-terminal-cyan rounded border border-terminal-cyan/30">
                LINEAR PERPETUAL
              </span>
            </div>
            <span className="text-2xs text-terminal-muted">Exchange: Bybit Derivatives</span>
          </div>

          <div className="border-l border-terminal-border pl-4">
            <span className="text-2xs uppercase text-terminal-muted block">Mark Price</span>
            <span className="text-lg font-bold text-terminal-text">
              ${formatPrice(currentTicker.price, activeSymbol)}
            </span>
          </div>

          <div className="border-l border-terminal-border pl-4">
            <span className="text-2xs uppercase text-terminal-muted block">24h Change</span>
            <span
              className={cn(
                'text-sm font-bold',
                currentTicker.change24h >= 0 ? 'text-terminal-bull' : 'text-terminal-bear'
              )}
            >
              {formatPercent(currentTicker.change24h, 2)} (${currentTicker.change24hAmount.toFixed(2)})
            </span>
          </div>

          <div className="border-l border-terminal-border pl-4 hidden md:block">
            <span className="text-2xs uppercase text-terminal-muted block">24h High / Low</span>
            <span className="text-xs font-semibold text-terminal-text">
              {formatPrice(currentTicker.high24h, activeSymbol)} / {formatPrice(currentTicker.low24h, activeSymbol)}
            </span>
          </div>

          <div className="border-l border-terminal-border pl-4 hidden lg:block">
            <span className="text-2xs uppercase text-terminal-muted block">24h Volume</span>
            <span className="text-xs font-semibold text-terminal-cyan">
              {formatCurrency(currentTicker.volume24hUsd, 0)}
            </span>
          </div>
        </div>

        {/* Controls Toolbar: Timeframes & Refresh */}
        <div className="flex items-center gap-2">
          {/* Timeframe Switcher */}
          <div className="flex items-center bg-terminal-surface rounded p-0.5 border border-terminal-border">
            {TIMEFRAMES.map((tf) => (
              <button
                key={tf}
                onClick={() => setActiveTimeframe(tf)}
                className={cn(
                  'px-2 py-1 text-2xs font-semibold rounded transition-colors',
                  activeTimeframe === tf
                    ? 'bg-terminal-cyan text-black font-bold'
                    : 'text-terminal-muted hover:text-terminal-text'
                )}
              >
                {tf}
              </button>
            ))}
          </div>

          <button
            onClick={refreshCandles}
            className="p-1.5 bg-terminal-surface hover:bg-terminal-elevated text-terminal-muted hover:text-terminal-text rounded border border-terminal-border transition-colors"
            title="Refresh Historical Candles"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* 2. TECHNICAL INDICATOR TOGGLE BAR */}
      <div className="terminal-panel p-2 flex flex-wrap items-center gap-2 text-2xs">
        <div className="flex items-center gap-1 text-terminal-muted uppercase tracking-wider font-semibold mr-2">
          <Eye className="w-3 h-3 text-terminal-cyan" />
          <span>Overlays:</span>
        </div>

        {[
          { key: 'ema8', label: 'EMA 8', color: 'text-terminal-cyan' },
          { key: 'ema21', label: 'EMA 21', color: 'text-terminal-amber' },
          { key: 'ema55', label: 'EMA 55', color: 'text-terminal-purple' },
          { key: 'ema200', label: 'EMA 200', color: 'text-pink-400' },
          { key: 'bollinger', label: 'Bollinger (20,2)', color: 'text-blue-400' },
          { key: 'supertrend', label: 'Supertrend (10,3)', color: 'text-terminal-bull' },
        ].map(({ key, label, color }) => (
          <button
            key={key}
            onClick={() => toggleIndicator(key as any)}
            className={cn(
              'px-2 py-1 rounded border transition-all',
              indicators[key as keyof typeof indicators]
                ? `bg-terminal-elevated ${color} border-terminal-border font-bold shadow-xs`
                : 'bg-terminal-bg/50 text-terminal-dim border-transparent hover:text-terminal-muted'
            )}
          >
            {label}
          </button>
        ))}
      </div>

      {/* 3. MAIN TRADING WORKSPACE */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
        {/* Candlestick Chart (8 cols) */}
        <div className="lg:col-span-8 terminal-panel flex flex-col h-[560px]">
          <div className="terminal-header">
            <span>TradingView Quantitative Candlestick Terminal</span>
            <span className="text-terminal-cyan text-2xs">Tick Resolution: Realtime Bybit WS</span>
          </div>
          <div className="flex-1 w-full relative">
            <TradingViewChart className="h-full" />
          </div>
        </div>

        {/* Level 2 Order Book (4 cols) */}
        <div className="lg:col-span-4 h-[560px]">
          <OrderBook depth={15} />
        </div>
      </div>

      {/* 4. DERIVATIVES FLOW & ORDERBOOK METRICS (CVD & FUNDING / OPEN INTEREST) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <CVDChart className="h-[220px]" />
        <FundingOIWidget className="h-[220px]" />
      </div>
    </div>
  );
};
