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
import { EquityPoint } from '../../types/backtest';
import { formatCurrency, formatPercent } from '../../lib/formatters/formatters';

interface EquityDrawdownChartProps {
  data: EquityPoint[];
  showBenchmark?: boolean;
}

export const EquityDrawdownChart: React.FC<EquityDrawdownChartProps> = ({
  data,
  showBenchmark = true,
}) => {
  return (
    <div className="flex flex-col h-full w-full space-y-2">
      {/* 1. Equity Curve */}
      <div className="flex-1 w-full min-h-[220px]">
        <div className="text-2xs uppercase tracking-widest text-terminal-muted font-semibold mb-1 flex items-center justify-between">
          <span>Portfolio Equity vs Benchmark</span>
          <div className="flex items-center gap-3 font-mono text-2xs normal-case">
            <span className="flex items-center gap-1 text-terminal-cyan">
              <span className="w-2 h-0.5 bg-terminal-cyan inline-block"></span>
              AI Ensemble
            </span>
            {showBenchmark && (
              <span className="flex items-center gap-1 text-terminal-muted">
                <span className="w-2 h-0.5 bg-terminal-muted inline-block"></span>
                Buy & Hold (BTC)
              </span>
            )}
          </div>
        </div>

        <ResponsiveContainer width="100%" height={210}>
          <AreaChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 0 }}>
            <defs>
              <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
            <XAxis
              dataKey="time"
              stroke="#484f58"
              tick={{ fontSize: 10, fill: '#8b949e', fontFamily: 'JetBrains Mono' }}
              tickLine={false}
            />
            <YAxis
              domain={['dataMin - 500', 'dataMax + 1000']}
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
                name === 'equity' ? 'AI Ensemble' : 'Benchmark',
              ]}
              labelStyle={{ color: '#8b949e' }}
            />
            <Area
              type="monotone"
              dataKey="equity"
              stroke="#06b6d4"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#equityGrad)"
              name="equity"
            />
            {showBenchmark && (
              <Line
                type="monotone"
                dataKey="benchmarkEquity"
                stroke="#484f58"
                strokeWidth={1.5}
                strokeDasharray="4 4"
                dot={false}
                name="benchmark"
              />
            )}
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* 2. Underwater Drawdown Curve */}
      <div className="h-[90px] w-full pt-1 border-t border-terminal-border/60">
        <div className="text-2xs uppercase tracking-widest text-terminal-muted font-semibold mb-0.5">
          <span>Underwater Drawdown</span>
        </div>
        <ResponsiveContainer width="100%" height={70}>
          <AreaChart data={data} margin={{ top: 0, right: 10, left: 10, bottom: 0 }}>
            <defs>
              <linearGradient id="ddGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.05} />
                <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.35} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
            <XAxis dataKey="time" hide />
            <YAxis
              domain={['dataMin - 1', 0]}
              stroke="#484f58"
              tick={{ fontSize: 9, fill: '#8b949e', fontFamily: 'JetBrains Mono' }}
              tickFormatter={(v) => `${v}%`}
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
              formatter={(val: any) => [formatPercent(Number(val), 2, false), 'Drawdown']}
              labelStyle={{ color: '#8b949e' }}
            />
            <Area
              type="monotone"
              dataKey="drawdown"
              stroke="#f43f5e"
              strokeWidth={1.5}
              fill="url(#ddGrad)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
