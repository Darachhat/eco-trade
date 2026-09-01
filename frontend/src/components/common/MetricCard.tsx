import React from 'react';
import { cn } from '../../lib/utils';

interface MetricCardProps {
  label: string;
  value: string | number;
  subValue?: string;
  delta?: {
    value: string;
    isPositive?: boolean;
  };
  icon?: React.ReactNode;
  variant?: 'default' | 'bull' | 'bear' | 'cyan' | 'amber';
  className?: string;
  dense?: boolean;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  subValue,
  delta,
  icon,
  variant = 'default',
  className,
  dense = false,
}) => {
  const variantBorder = {
    default: 'border-terminal-border hover:border-terminal-border/80',
    bull: 'border-terminal-bullBorder/60 bg-terminal-bullDim/10',
    bear: 'border-terminal-bearBorder/60 bg-terminal-bearDim/10',
    cyan: 'border-terminal-cyan/40 bg-terminal-cyan/5',
    amber: 'border-terminal-amber/40 bg-terminal-amberDim/10',
  }[variant];

  const valueColor = {
    default: 'text-terminal-text',
    bull: 'text-terminal-bull',
    bear: 'text-terminal-bear',
    cyan: 'text-terminal-cyan',
    amber: 'text-terminal-amber',
  }[variant];

  return (
    <div
      className={cn(
        'terminal-card transition-colors duration-150',
        variantBorder,
        dense ? 'p-2' : 'p-3',
        className
      )}
    >
      <div className="flex items-center justify-between gap-1 text-2xs uppercase tracking-widest text-terminal-muted font-medium mb-1">
        <span>{label}</span>
        {icon && <span className="text-terminal-dim">{icon}</span>}
      </div>

      <div className="flex items-baseline justify-between gap-2">
        <div className={cn('font-mono font-bold tracking-tight', dense ? 'text-sm' : 'text-base', valueColor)}>
          {value}
        </div>
        {delta && (
          <span
            className={cn(
              'font-mono text-2xs font-semibold',
              delta.isPositive ? 'text-terminal-bull' : 'text-terminal-bear'
            )}
          >
            {delta.value}
          </span>
        )}
      </div>

      {subValue && (
        <div className="text-2xs text-terminal-muted mt-0.5 font-mono truncate">
          {subValue}
        </div>
      )}
    </div>
  );
};
