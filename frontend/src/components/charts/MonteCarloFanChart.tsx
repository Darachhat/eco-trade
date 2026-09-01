import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { MonteCarloResult } from '../../types/backtest';
import { formatCurrency, formatPercent } from '../../lib/formatters/formatters';

interface MonteCarloFanChartProps {
  data: MonteCarloResult;
}

export const MonteCarloFanChart: React.FC<MonteCarloFanChartProps> = ({ data }) => {
  return (
    <div className="flex flex-col h-full w-full space-y-3">
      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-xs">
        <div className="terminal-card p-2">
          <span className="text-2xs uppercase text-terminal-muted block">Simulations</span>
          <span className="font-bold text-terminal-text text-sm">
            {data.simulationsCount.toLocaleString()} Runs
          </span>
        </div>
        <div className="terminal-card p-2">
          <span className="text-2xs uppercase text-terminal-muted block">Median Return</span>
          <span className="font-bold text-terminal-bull text-sm">
            {formatCurrency(data.medianFinalEquity)}
          </span>
        </div>
        <div className="terminal-card p-2">
          <span className="text-2xs uppercase text-terminal-muted block">5th %ile (Worst Case)</span>
          <span className="font-bold text-terminal-bear text-sm">
            {formatCurrency(data.percentile5th)}
          </span>
        </div>
        <div className="terminal-card p-2">
          <span className="text-2xs uppercase text-terminal-muted block">Ruin Probability</span>
          <span className="font-bold text-terminal-bull text-sm">
            {formatPercent(data.probabilityOfRuin, 2, false)}
          </span>
        </div>
      </div>

      {/* Chart */}
      <div className="flex-1 w-full min-h-[260px]">
        <div className="text-2xs uppercase tracking-widest text-terminal-muted font-semibold mb-1 flex items-center justify-between">
          <span>1,000 Path Confidence Fan (5th - 95th Percentile)</span>
          <div className="flex items-center gap-2 text-2xs font-mono">
            <span className="text-terminal-bull">● 95th %ile</span>
            <span className="text-terminal-cyan">● Median</span>
            <span className="text-terminal-bear">● 5th %ile</span>
          </div>
        </div>

        <ResponsiveContainer width="100%" height={240}>
          <AreaChart data={data.samplePaths} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
            <defs>
              <linearGradient id="p95Grad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#10b981" stopOpacity={0.02} />
              </linearGradient>
              <linearGradient id="p5Grad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.02} />
                <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.15} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
            <XAxis
              dataKey="time"
              stroke="#484f58"
              tick={{ fontSize: 10, fill: '#8b949e', fontFamily: 'JetBrains Mono' }}
              tickFormatter={(v) => `t+${v}`}
              tickLine={false}
            />
            <YAxis
              stroke="#484f58"
              tick={{ fontSize: 10, fill: '#8b949e', fontFamily: 'JetBrains Mono' }}
              tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
              orientation="right"
              tickLine={false}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#0d1117',
                borderColor: '#21262d',
                borderRadius: '4px',
                fontSize: '11px',
                fontFamily: 'JetBrains Mono',
              }}
              formatter={(val: any, name: any) => [
                formatCurrency(Number(val)),
                String(name || '').toUpperCase(),
              ]}
              labelStyle={{ color: '#8b949e' }}
            />
            <Area type="monotone" dataKey="p95" stroke="#10b981" strokeWidth={1} fill="url(#p95Grad)" name="95th %ile" />
            <Area type="monotone" dataKey="p75" stroke="#06b6d4" strokeWidth={1} fill="none" strokeDasharray="2 2" name="75th %ile" />
            <Area type="monotone" dataKey="median" stroke="#06b6d4" strokeWidth={2} fill="none" name="Median" />
            <Area type="monotone" dataKey="p25" stroke="#f59e0b" strokeWidth={1} fill="none" strokeDasharray="2 2" name="25th %ile" />
            <Area type="monotone" dataKey="p5" stroke="#f43f5e" strokeWidth={1} fill="url(#p5Grad)" name="5th %ile" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
