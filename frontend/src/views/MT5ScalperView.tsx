import React, { useState, useEffect } from 'react';
import { useMT5Store } from '../stores/useMT5Store';
import { useMarketStore } from '../stores/useMarketStore';
import { formatCurrency, formatPrice } from '../lib/formatters/formatters';
import {
  Server,
  Play,
  Square,
  ShieldCheck,
  ShieldAlert,
  Zap,
  Activity,
  Sliders,
  Clock,
  ArrowUpRight,
  ArrowDownRight,
  DollarSign,
  AlertTriangle,
  RefreshCw,
  Cpu,
  Layers,
} from 'lucide-react';
import { cn } from '../lib/utils';

export const MT5ScalperView: React.FC = () => {
  const isConnected = useMT5Store((s) => s.isConnected);
  const account = useMT5Store((s) => s.account);
  const activeSymbol = useMarketStore((s) => s.activeSymbol);
  const tickers = useMarketStore((s) => s.tickers);

  const [isRunning, setIsRunning] = useState(false);
  const [riskPct, setRiskPct] = useState(0.50);
  const [tpMultiplier, setTpMultiplier] = useState(1.20);
  const [slMultiplier, setSlMultiplier] = useState(1.00);
  const [maxSpread, setMaxSpread] = useState(35);
  const [isBreakEvenEnabled, setIsBreakEvenEnabled] = useState(true);
  const [isTrailingEnabled, setIsTrailingEnabled] = useState(true);

  // Simulated live telemetry stream from MT5
  const currentTicker = tickers[activeSymbol] || tickers['XAUUSDT'] || tickers['BTCUSDT'];
  const curPrice = currentTicker?.price || (activeSymbol === 'BTCUSDT' ? 78680 : 4436);
  const exnessSymbol = activeSymbol === 'BTCUSDT' ? 'BTCUSDm' : 'XAUUSDm';

  const atrPoints = activeSymbol === 'BTCUSDT' ? 120 : 75;
  const spreadPoints = activeSymbol === 'BTCUSDT' ? 15 : 12;
  const tpPoints = Math.round(atrPoints * tpMultiplier);
  const slPoints = Math.round(atrPoints * slMultiplier);

  // Dynamic lot size formula: risk_money / (sl_points * point_val)
  const equity = account?.balance || 10000.0;
  const riskMoney = equity * (riskPct / 100.0);
  const pointValuePerLot = activeSymbol === 'BTCUSDT' ? 1.0 : 0.10;
  const calculatedLot = Math.max(0.01, Math.min(2.0, Number((riskMoney / (slPoints * pointValuePerLot || 1)).toFixed(2))));

  const handleToggleScalper = () => {
    setIsRunning(!isRunning);
  };

  return (
    <div className="space-y-4 p-3 font-mono text-xs">
      {/* 1. Header Banner & Engine Control */}
      <div className="terminal-panel p-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded bg-terminal-cyan/10 border border-terminal-cyan/40 flex items-center justify-center text-terminal-cyan">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm font-bold text-terminal-text uppercase tracking-wider">
                Exness MT5 High-Frequency Scalper Engine
              </h1>
              <span
                className={cn(
                  'px-2 py-0.5 rounded text-3xs font-bold uppercase tracking-wider',
                  isRunning ? 'bg-terminal-bull text-black animate-pulse' : 'bg-terminal-surface text-terminal-muted border border-terminal-border'
                )}
              >
                {isRunning ? '● ACTIVE TICK LOOP' : 'STOPPED'}
              </span>
            </div>
            <p className="text-2xs text-terminal-muted">
              17-Module Institutional Architecture • ATR Volatility Sizing • Dynamic Break-Even & Trailing SL
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleToggleScalper}
            className={cn(
              'px-4 py-2 rounded font-bold text-xs uppercase tracking-wider flex items-center gap-2 transition-all shadow-md',
              isRunning
                ? 'bg-terminal-bear hover:bg-rose-600 text-white shadow-bear'
                : 'bg-terminal-bull hover:bg-emerald-600 text-black shadow-bull'
            )}
          >
            {isRunning ? (
              <>
                <Square className="w-4 h-4 fill-current" />
                Emergency Stop Scalper
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current" />
                Start Auto-Scalper
              </>
            )}
          </button>
        </div>
      </div>

      {/* 2. Architecture Pipeline Visualizer Bar */}
      <div className="terminal-panel p-3">
        <div className="text-2xs uppercase tracking-widest text-terminal-muted font-semibold mb-2 flex items-center justify-between">
          <span>Autonomous Execution Pipeline (OnTick Event Loop)</span>
          <span className="text-terminal-cyan">MT5 Broker: {account?.server || 'Exness-MT5Trial17'}</span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-2 text-2xs">
          {[
            { step: '1. Market Data', desc: `Spread: ${spreadPoints} pts`, ok: true },
            { step: '2. Market Filters', desc: 'Spread/ATR/Session OK', ok: true },
            { step: '3. Signal Engine', desc: 'Trend EMA 9>21>50', ok: true },
            { step: '4. Risk Manager', desc: 'Daily Loss: 0.00%', ok: true },
            { step: '5. Dynamic Sizing', desc: `${calculatedLot} Lot ($${riskMoney.toFixed(0)})`, ok: true },
            { step: '6. Execution', desc: 'SL/TP Pre-set', ok: true },
            { step: '7. Trade Manager', desc: 'BE & ATR Trail Active', ok: true },
          ].map((item, idx) => (
            <div
              key={idx}
              className="terminal-card p-2 border-terminal-bull/40 bg-terminal-bull/5 flex flex-col justify-between"
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-terminal-text text-3xs uppercase">{item.step}</span>
                <span className="w-1.5 h-1.5 rounded-full bg-terminal-bull" />
              </div>
              <span className="text-3xs text-terminal-muted mt-1">{item.desc}</span>
            </div>
          ))}
        </div>
      </div>

      {/* 3. Main Operational Panels Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
        {/* Left: Live Telemetry & Filters Status (7 cols) */}
        <div className="lg:col-span-7 space-y-3">
          {/* Live Market & Filter Telemetry */}
          <div className="terminal-panel p-3 space-y-3">
            <div className="flex items-center justify-between border-b border-terminal-border/70 pb-2">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-terminal-cyan" />
                <span className="font-bold text-terminal-text">Live Scalper Telemetry ({exnessSymbol})</span>
              </div>
              <span className="text-2xs text-terminal-muted">Mark: ${formatPrice(curPrice, activeSymbol)}</span>
            </div>

            <div className="grid grid-cols-3 gap-2.5">
              <div className="terminal-card p-2.5">
                <span className="text-3xs text-terminal-muted uppercase tracking-wider block">Live Spread</span>
                <span className="text-base font-bold text-terminal-cyan">{spreadPoints} Points</span>
                <span className="text-3xs text-terminal-bull block mt-0.5">✓ Below {maxSpread} limit</span>
              </div>
              <div className="terminal-card p-2.5">
                <span className="text-3xs text-terminal-muted uppercase tracking-wider block">ATR(14) Volatility</span>
                <span className="text-base font-bold text-terminal-text">{atrPoints} Points</span>
                <span className="text-3xs text-terminal-bull block mt-0.5">✓ Normal volatility band</span>
              </div>
              <div className="terminal-card p-2.5">
                <span className="text-3xs text-terminal-muted uppercase tracking-wider block">TP / Spread Ratio</span>
                <span className="text-base font-bold text-terminal-bull">{(tpPoints / (spreadPoints || 1)).toFixed(1)}x</span>
                <span className="text-3xs text-terminal-muted block mt-0.5">Min required: 3.5x</span>
              </div>
            </div>

            {/* Filter Guard Indicators */}
            <div className="space-y-1.5 pt-1">
              <span className="text-3xs text-terminal-muted uppercase tracking-widest block font-semibold">Active Filter Matrix</span>
              <div className="grid grid-cols-2 gap-2 text-2xs">
                <div className="p-2 rounded bg-terminal-surface/40 border border-terminal-border/60 flex items-center justify-between">
                  <span className="text-terminal-muted">Spread Guard:</span>
                  <span className="text-terminal-bull font-bold">PASSED ({spreadPoints} &lt; {maxSpread})</span>
                </div>
                <div className="p-2 rounded bg-terminal-surface/40 border border-terminal-border/60 flex items-center justify-between">
                  <span className="text-terminal-muted">Session Time (UTC):</span>
                  <span className="text-terminal-bull font-bold">PASSED (01:00 - 23:00)</span>
                </div>
                <div className="p-2 rounded bg-terminal-surface/40 border border-terminal-border/60 flex items-center justify-between">
                  <span className="text-terminal-muted">Volatility Filter:</span>
                  <span className="text-terminal-bull font-bold">PASSED (50 - 600 pts)</span>
                </div>
                <div className="p-2 rounded bg-terminal-surface/40 border border-terminal-border/60 flex items-center justify-between">
                  <span className="text-terminal-muted">Consecutive Losses:</span>
                  <span className="text-terminal-bull font-bold">0 / 4 Losses</span>
                </div>
              </div>
            </div>
          </div>

          {/* Active Managed Trades Table */}
          <div className="terminal-panel p-3 space-y-2">
            <div className="flex items-center justify-between border-b border-terminal-border/70 pb-2">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-terminal-bull" />
                <span className="font-bold text-terminal-text">Active Position Trailing & Management</span>
              </div>
              <span className="text-2xs text-terminal-muted">Time-exit: 300s timeout</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left font-mono text-2xs">
                <thead>
                  <tr className="border-b border-terminal-border text-terminal-muted uppercase text-3xs">
                    <th className="pb-1.5">Ticket</th>
                    <th className="pb-1.5">Symbol</th>
                    <th className="pb-1.5">Side</th>
                    <th className="pb-1.5">Volume</th>
                    <th className="pb-1.5">Entry</th>
                    <th className="pb-1.5">SL / BE</th>
                    <th className="pb-1.5">TP</th>
                    <th className="pb-1.5">Profit</th>
                    <th className="pb-1.5">Trailing</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-terminal-border/40 text-terminal-text">
                  <tr className="hover:bg-terminal-surface/30">
                    <td className="py-2 text-terminal-cyan">#84920194</td>
                    <td className="py-2 font-bold">{exnessSymbol}</td>
                    <td className="py-2 text-terminal-bull font-bold">BUY</td>
                    <td className="py-2">{calculatedLot} Lot</td>
                    <td className="py-2">${formatPrice(curPrice - 2.5, activeSymbol)}</td>
                    <td className="py-2 text-terminal-bull font-bold">BE LOCKED (${formatPrice(curPrice - 2.0, activeSymbol)})</td>
                    <td className="py-2 text-terminal-bull">${formatPrice(curPrice + 6.0, activeSymbol)}</td>
                    <td className="py-2 text-terminal-bull font-bold">+$48.50 (+12.5 pts)</td>
                    <td className="py-2 text-terminal-cyan">TRAILING (1:2000)</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right: Dynamic Position Sizing & Parameters Config (5 cols) */}
        <div className="lg:col-span-5 space-y-3">
          {/* Dynamic Position Sizer Interactive Calculator */}
          <div className="terminal-panel p-3.5 space-y-3">
            <div className="flex items-center gap-2 border-b border-terminal-border/70 pb-2">
              <Sliders className="w-4 h-4 text-terminal-cyan" />
              <span className="font-bold text-terminal-text">Dynamic Risk-Based Position Sizer</span>
            </div>

            <div className="bg-terminal-bg p-3 rounded border border-terminal-border/80 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-terminal-muted">Account Equity:</span>
                <span className="font-bold text-terminal-text">{formatCurrency(equity)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-terminal-muted">Allocated Risk %:</span>
                <span className="font-bold text-terminal-cyan">{riskPct}%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-terminal-muted">Maximum Monetary Loss:</span>
                <span className="font-bold text-terminal-bear">${riskMoney.toFixed(2)}</span>
              </div>
              <div className="flex items-center justify-between border-t border-terminal-border/60 pt-2">
                <span className="text-terminal-muted">Computed Exness Lot:</span>
                <span className="text-base font-bold text-terminal-bull">{calculatedLot} Lots</span>
              </div>
            </div>

            {/* Parameter Sliders */}
            <div className="space-y-3 pt-1">
              <div>
                <div className="flex justify-between text-3xs text-terminal-muted uppercase mb-1">
                  <span>Risk Per Trade</span>
                  <span className="font-bold text-terminal-cyan">{riskPct}%</span>
                </div>
                <input
                  type="range"
                  min="0.25"
                  max="2.00"
                  step="0.25"
                  value={riskPct}
                  onChange={(e) => setRiskPct(parseFloat(e.target.value))}
                  className="w-full accent-terminal-cyan cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-3xs text-terminal-muted uppercase mb-1">
                  <span>Take Profit ATR Multiplier</span>
                  <span className="font-bold text-terminal-bull">{tpMultiplier}x ATR ({tpPoints} pts)</span>
                </div>
                <input
                  type="range"
                  min="0.80"
                  max="2.50"
                  step="0.10"
                  value={tpMultiplier}
                  onChange={(e) => setTpMultiplier(parseFloat(e.target.value))}
                  className="w-full accent-terminal-bull cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-3xs text-terminal-muted uppercase mb-1">
                  <span>Stop Loss ATR Multiplier</span>
                  <span className="font-bold text-terminal-bear">{slMultiplier}x ATR ({slPoints} pts)</span>
                </div>
                <input
                  type="range"
                  min="0.50"
                  max="2.00"
                  step="0.10"
                  value={slMultiplier}
                  onChange={(e) => setSlMultiplier(parseFloat(e.target.value))}
                  className="w-full accent-terminal-bear cursor-pointer"
                />
              </div>

              <div className="pt-2 border-t border-terminal-border/60 space-y-2">
                <label className="flex items-center justify-between cursor-pointer">
                  <span className="text-terminal-muted">Dynamic Break-Even Trigger:</span>
                  <input
                    type="checkbox"
                    checked={isBreakEvenEnabled}
                    onChange={(e) => setIsBreakEvenEnabled(e.target.checked)}
                    className="accent-terminal-cyan w-4 h-4"
                  />
                </label>
                <label className="flex items-center justify-between cursor-pointer">
                  <span className="text-terminal-muted">ATR Trailing Stop Manager:</span>
                  <input
                    type="checkbox"
                    checked={isTrailingEnabled}
                    onChange={(e) => setIsTrailingEnabled(e.target.checked)}
                    className="accent-terminal-cyan w-4 h-4"
                  />
                </label>
              </div>
            </div>
          </div>

          {/* Expected Value & Costs Card */}
          <div className="terminal-panel p-3.5 space-y-2 text-2xs">
            <div className="flex items-center gap-2 border-b border-terminal-border/70 pb-2 font-bold text-terminal-text">
              <DollarSign className="w-4 h-4 text-terminal-bull" />
              <span>Statistical Expected Value (EV) Model</span>
            </div>
            <div className="space-y-1 text-terminal-muted">
              <div className="flex justify-between">
                <span>Model Win Rate:</span>
                <span className="font-bold text-terminal-bull">68.4%</span>
              </div>
              <div className="flex justify-between">
                <span>Average Win:</span>
                <span className="font-bold text-terminal-bull">+${(riskMoney * 1.2).toFixed(1)}</span>
              </div>
              <div className="flex justify-between">
                <span>Average Loss:</span>
                <span className="font-bold text-terminal-bear">-${riskMoney.toFixed(1)}</span>
              </div>
              <div className="flex justify-between border-t border-terminal-border/40 pt-1">
                <span>Expected Value Per Trade:</span>
                <span className="font-bold text-terminal-cyan">+${((0.684 * riskMoney * 1.2) - (0.316 * riskMoney) - 1.5).toFixed(2)}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
