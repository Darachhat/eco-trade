import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { useMarketStore } from '../../stores/useMarketStore';
import { formatCompactNumber } from '../../lib/formatters/formatters';

export const CVDChart: React.FC<{ className?: string }> = ({ className }) => {
  const cvdHistory = useMarketStore((s) => s.cvdHistory);

  return (
    <div className={`terminal-panel flex flex-col ${className || ''}`}>
      <div className="terminal-header">
        <span>Cumulative Volume Delta (CVD)</span>
        <span className="font-mono text-terminal-bull text-2xs font-semibold">
          +${formatCompactNumber(cvdHistory[cvdHistory.length - 1]?.cvd || 0)} Net Flow
        </span>
      </div>

      <div className="flex-1 p-2 min-h-[140px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={cvdHistory} margin={{ top: 5, right: 10, left: 10, bottom: 0 }}>
            <defs>
              <linearGradient id="cvdGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
            <XAxis dataKey="time" hide />
            <YAxis
              stroke="#484f58"
              tick={{ fontSize: 9, fill: '#8b949e', fontFamily: 'JetBrains Mono' }}
              tickFormatter={(v) => `$${formatCompactNumber(v)}`}
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
              formatter={(val: any) => [`$${Number(val).toLocaleString()}`, 'CVD Flow']}
            />
            <Area type="monotone" dataKey="cvd" stroke="#06b6d4" strokeWidth={1.5} fill="url(#cvdGrad)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
