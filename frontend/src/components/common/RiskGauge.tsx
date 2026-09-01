import React from 'react';
import { cn } from '../../lib/utils';

interface RiskGaugeProps {
  label: string;
  current: number;
  limit: number;
  unit?: string;
  isPercent?: boolean;
  reverse?: boolean; // if true, higher is safer
  className?: string;
}

export const RiskGauge: React.FC<RiskGaugeProps> = ({
  label,
  current,
  limit,
  unit = '',
  isPercent = true,
  reverse = false,
  className,
}) => {
  const ratio = Math.min(100, Math.max(0, (Math.abs(current) / limit) * 100));
  
  let statusColor = 'bg-terminal-bull';
  let textColor = 'text-terminal-bull';

  if (!reverse) {
    if (ratio >= 80) {
      statusColor = 'bg-terminal-bear';
      textColor = 'text-terminal-bear';
    } else if (ratio >= 50) {
      statusColor = 'bg-terminal-amber';
      textColor = 'text-terminal-amber';
    }
  } else {
    if (ratio <= 40) {
      statusColor = 'bg-terminal-bear';
      textColor = 'text-terminal-bear';
    } else if (ratio <= 70) {
      statusColor = 'bg-terminal-amber';
      textColor = 'text-terminal-amber';
    }
  }

  return (
    <div className={cn('terminal-card p-3', className)}>
      <div className="flex items-center justify-between text-2xs uppercase tracking-wider text-terminal-muted font-medium mb-1.5">
        <span>{label}</span>
        <span className={cn('font-mono font-bold', textColor)}>
          {current.toFixed(2)}{unit || (isPercent ? '%' : '')} / {limit.toFixed(2)}{unit || (isPercent ? '%' : '')}
        </span>
      </div>

      {/* Progress track */}
      <div className="h-1.5 w-full bg-terminal-border rounded-full overflow-hidden">
        <div
          className={cn('h-full transition-all duration-300 rounded-full', statusColor)}
          style={{ width: `${ratio}%` }}
        />
      </div>

      <div className="flex justify-between text-2xs text-terminal-dim font-mono mt-1">
        <span>0{unit || (isPercent ? '%' : '')}</span>
        <span>{ratio.toFixed(0)}% limit utilized</span>
        <span>{limit}{unit || (isPercent ? '%' : '')}</span>
      </div>
    </div>
  );
};
