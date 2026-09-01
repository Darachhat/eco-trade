import React from 'react';
import { useBacktestStore } from '../stores/useBacktestStore';
import { MetricCard } from '../components/common/MetricCard';
import { EquityDrawdownChart } from '../components/charts/EquityDrawdownChart';
import { MonthlyHeatmap } from '../components/charts/MonthlyHeatmap';
import { StatusBadge } from '../components/common/StatusBadge';
import { formatCurrency, formatPercent, formatPrice, formatR } from '../lib/formatters/formatters';
import { Play, RotateCcw, BarChart3, TrendingUp, Calendar, Sliders, Shield } from 'lucide-react';
import { cn } from '../lib/utils';

export const BacktestTerminalView: React.FC = () => {
  const config = useBacktestStore((s) => s.config);
  const setConfig = useBacktestStore((s) => s.setConfig);
  const isRunning = useBacktestStore((s) => s.isRunning);
  const progress = useBacktestStore((s) => s.progress);
  const result = useBacktestStore((s) => s.result);
  const runBacktest = useBacktestStore((s) => s.runBacktest);

  if (!result) return null;

  const { metrics } = result;

  return (
    <div className="space-y-4 p-3 font-mono">
      {/* 1. BACKTEST CONFIGURATION PANEL */}
      <div className="terminal-panel p-4 space-y-3">
        <div className="flex items-center justify-between border-b border-terminal-border/60 pb-2">
          <div className="flex items-center gap-2">
            <Sliders className="w-4 h-4 text-terminal-cyan" />
            <span className="text-2xs uppercase tracking-widest font-semibold text-terminal-muted">
              Alpha Engine — Quantitative Backtest Configuration
            </span>
          </div>
          <span className="text-2xs text-terminal-dim">Historical Bybit Candles & Orderbook Replay</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2.5 text-2xs">
          {/* Symbol */}
          <div>
            <label className="text-terminal-muted block mb-1">Symbol</label>
            <select
              value={config.symbol}
              onChange={(e) => setConfig({ symbol: e.target.value as any })}
              className="w-full bg-terminal-bg border border-terminal-border rounded px-2 py-1 text-terminal-text font-bold"
            >
              <option value="BTCUSDT">BTCUSDT</option>
              <option value="XAUUSDT">XAUUSDT</option>
            </select>
          </div>

          {/* Timeframe */}
          <div>
            <label className="text-terminal-muted block mb-1">Timeframe</label>
            <select
              value={config.timeframe}
              onChange={(e) => setConfig({ timeframe: e.target.value as any })}
              className="w-full bg-terminal-bg border border-terminal-border rounded px-2 py-1 text-terminal-text"
            >
              <option value="1m">1m</option>
              <option value="5m">5m</option>
              <option value="15m">15m</option>
              <option value="1h">1h</option>
              <option value="4h">4h</option>
              <option value="1D">1D</option>
            </select>
          </div>

          {/* Strategy */}
          <div className="lg:col-span-2">
            <label className="text-terminal-muted block mb-1">Alpha Strategy Model</label>
            <select
              value={config.strategy}
              onChange={(e) => setConfig({ strategy: e.target.value as any })}
              className="w-full bg-terminal-bg border border-terminal-border rounded px-2 py-1 text-terminal-cyan font-bold"
            >
              <option value="AI Ensemble">AI Ensemble (10-Model Bayesian)</option>
              <option value="Transformer Alpha">Transformer Alpha (Self-Attention)</option>
              <option value="XGBoost Momentum">XGBoost Momentum + Orderbook</option>
              <option value="Multi-Model Regime Adaptive">Multi-Model Regime Adaptive</option>
            </select>
          </div>

          {/* Start Date */}
          <div>
            <label className="text-terminal-muted block mb-1">Start Date</label>
            <input
              type="date"
              value={config.startDate}
              onChange={(e) => setConfig({ startDate: e.target.value })}
              className="w-full bg-terminal-bg border border-terminal-border rounded px-1.5 py-0.5 text-terminal-text text-2xs"
            />
          </div>

          {/* End Date */}
          <div>
            <label className="text-terminal-muted block mb-1">End Date</label>
            <input
              type="date"
              value={config.endDate}
              onChange={(e) => setConfig({ endDate: e.target.value })}
              className="w-full bg-terminal-bg border border-terminal-border rounded px-1.5 py-0.5 text-terminal-text text-2xs"
            />
          </div>

          {/* Initial Capital */}
          <div>
            <label className="text-terminal-muted block mb-1">Initial Cap ($)</label>
            <input
              type="number"
              value={config.initialCapital}
              onChange={(e) => setConfig({ initialCapital: Number(e.target.value) })}
              className="w-full bg-terminal-bg border border-terminal-border rounded px-2 py-1 text-terminal-text"
            />
          </div>

          {/* Run Action Button */}
          <div className="flex items-end">
            <button
              onClick={runBacktest}
              disabled={isRunning}
              className="w-full py-1.5 bg-terminal-cyan hover:bg-cyan-600 disabled:opacity-50 text-black font-bold text-2xs rounded transition-colors uppercase tracking-wider flex items-center justify-center gap-1.5 shadow-cyan-glow"
            >
              <Play className="w-3.5 h-3.5 fill-black" />
              {isRunning ? `Running ${progress}%` : 'Run Backtest'}
            </button>
          </div>
        </div>

        {/* Progress Bar when running */}
        {isRunning && (
          <div className="h-1 w-full bg-terminal-border rounded-full overflow-hidden">
            <div
              className="h-full bg-terminal-cyan transition-all duration-150"
              style={{ width: `${progress}%` }}
            />
          </div>
        )}
      </div>

      {/* 2. QUANTITATIVE PERFORMANCE SUMMARY KPI CARDS */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
        <MetricCard
          label="Total Return"
          value={formatPercent(metrics.totalReturnPct, 1)}
          delta={{ value: `CAGR: ${metrics.cagr}%`, isPositive: true }}
          variant="bull"
        />
        <MetricCard
          label="Win Rate"
          value={formatPercent(metrics.winRate, 1, false)}
          subValue={`${metrics.winningTrades}W / ${metrics.losingTrades}L`}
          variant="bull"
        />
        <MetricCard
          label="Sharpe Ratio"
          value={metrics.sharpeRatio.toFixed(2)}
          subValue={`Sortino: ${metrics.sortinoRatio.toFixed(2)}`}
          variant="cyan"
        />
        <MetricCard
          label="Profit Factor"
          value={metrics.profitFactor.toFixed(2)}
          subValue="Gross Win / Gross Loss"
        />
        <MetricCard
          label="Max Drawdown"
          value={formatPercent(metrics.maxDrawdownPct, 1, false)}
          subValue={`Duration: ${metrics.maxDrawdownDurationDays}d`}
          variant="bear"
        />
        <MetricCard
          label="Expectancy"
          value={formatR(metrics.expectancyR)}
          subValue={`Avg Win: +${metrics.avgWinR.toFixed(2)}R`}
        />
        <MetricCard
          label="Long / Short Win"
          value={`${metrics.longWinRate.toFixed(0)}% / ${metrics.shortWinRate.toFixed(0)}%`}
          subValue={`${metrics.longCount}L / ${metrics.shortCount}S`}
        />
        <MetricCard
          label="Total Trades"
          value={metrics.totalTrades.toLocaleString()}
          subValue="Bybit 15m Bars"
        />
      </div>

      {/* 3. CHARTS ROW: EQUITY CURVE + UNDERWATER DRAWDOWN */}
      <div className="terminal-panel p-4">
        <EquityDrawdownChart data={result.equityCurve} />
      </div>

      {/* 4. MONTHLY RETURNS HEATMAP */}
      <div className="terminal-panel p-4 space-y-2">
        <div className="flex items-center justify-between border-b border-terminal-border/60 pb-2">
          <span className="text-2xs uppercase tracking-widest font-semibold text-terminal-muted">
            Monthly Returns Performance Heatmap
          </span>
          <span className="text-2xs text-terminal-cyan">Alpha Engine Institutional Matrix</span>
        </div>
        <MonthlyHeatmap data={result.monthlyReturns} />
      </div>

      {/* 5. SAMPLE EXECUTED TRADES TABLE */}
      <div className="terminal-panel flex flex-col">
        <div className="terminal-header">
          <span>Sample Historical Executed Trades Log</span>
          <span className="text-2xs text-terminal-muted font-mono">{metrics.totalTrades} Total Samples</span>
        </div>
        <div className="p-2 overflow-x-auto">
          <table className="terminal-table">
            <thead>
              <tr>
                <th>Trade ID</th>
                <th>Symbol</th>
                <th>Side</th>
                <th>Entry Time</th>
                <th>Exit Time</th>
                <th>Entry Price</th>
                <th>Exit Price</th>
                <th>PnL ($)</th>
                <th>Return (%)</th>
                <th>Return (R)</th>
                <th>Exit Trigger</th>
                <th>Duration (Bars)</th>
              </tr>
            </thead>
            <tbody>
              {result.trades.map((tr) => (
                <tr key={tr.id}>
                  <td className="font-mono text-terminal-muted">{tr.id}</td>
                  <td className="font-bold text-terminal-text">{tr.symbol}</td>
                  <td>
                    <StatusBadge variant={tr.side} size="xs" />
                  </td>
                  <td className="text-terminal-muted">{tr.entryTime}</td>
                  <td className="text-terminal-muted">{tr.exitTime}</td>
                  <td>{formatPrice(tr.entryPrice, tr.symbol)}</td>
                  <td>{formatPrice(tr.exitPrice, tr.symbol)}</td>
                  <td className={cn('font-bold', tr.pnlUsd >= 0 ? 'text-terminal-bull' : 'text-terminal-bear')}>
                    {tr.pnlUsd >= 0 ? `+${formatCurrency(tr.pnlUsd)}` : formatCurrency(tr.pnlUsd)}
                  </td>
                  <td className={cn('font-bold', tr.pnlPct >= 0 ? 'text-terminal-bull' : 'text-terminal-bear')}>
                    {formatPercent(tr.pnlPct, 2)}
                  </td>
                  <td className={cn('font-bold font-mono', tr.returnR >= 0 ? 'text-terminal-bull' : 'text-terminal-bear')}>
                    {formatR(tr.returnR)}
                  </td>
                  <td>
                    <span className="text-3xs px-1.5 py-0.5 bg-terminal-surface rounded border border-terminal-border">
                      {tr.exitReason}
                    </span>
                  </td>
                  <td className="text-terminal-dim">{tr.durationBars} bars</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
