import React from 'react';
import { cn } from '../../lib/utils';

export type BadgeVariant =
  | 'LONG'
  | 'SHORT'
  | 'NEUTRAL'
  | 'VALID'
  | 'WATCH'
  | 'INVALIDATED'
  | 'EXECUTED'
  | 'CLOSED'
  | 'CHAMPION'
  | 'CHALLENGER'
  | 'BENCHMARK'
  | 'HEALTHY'
  | 'WARNING'
  | 'CRITICAL'
  | 'BULL_TRENDING'
  | 'BEAR_TRENDING'
  | 'RANGING'
  | 'HIGH_VOLATILITY'
  | 'PAPER'
  | 'LIVE';

interface StatusBadgeProps {
  variant: BadgeVariant | string;
  label?: string;
  size?: 'xs' | 'sm' | 'md';
  pulse?: boolean;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  variant,
  label,
  size = 'xs',
  pulse = false,
  className,
}) => {
  const displayLabel = label || variant.replace(/_/g, ' ');

  const getVariantStyles = (): { bg: string; text: string; border: string; dot: string } => {
    switch (variant) {
      case 'LONG':
      case 'VALID':
      case 'CHAMPION':
      case 'HEALTHY':
      case 'BULL_TRENDING':
        return {
          bg: 'bg-terminal-bullDim',
          text: 'text-terminal-bull',
          border: 'border-terminal-bullBorder',
          dot: 'bg-terminal-bull',
        };
      case 'SHORT':
      case 'INVALIDATED':
      case 'CRITICAL':
      case 'BEAR_TRENDING':
      case 'LIVE':
        return {
          bg: 'bg-terminal-bearDim',
          text: 'text-terminal-bear',
          border: 'border-terminal-bearBorder',
          dot: 'bg-terminal-bear',
        };
      case 'WATCH':
      case 'CHALLENGER':
      case 'WARNING':
      case 'HIGH_VOLATILITY':
      case 'PAPER':
        return {
          bg: 'bg-terminal-amberDim',
          text: 'text-terminal-amber',
          border: 'border-terminal-amber/30',
          dot: 'bg-terminal-amber',
        };
      case 'EXECUTED':
      case 'CLOSED':
      case 'BENCHMARK':
      case 'RANGING':
      case 'NEUTRAL':
      default:
        return {
          bg: 'bg-terminal-blueDim',
          text: 'text-terminal-cyan',
          border: 'border-terminal-cyan/30',
          dot: 'bg-terminal-cyan',
        };
    }
  };

  const styles = getVariantStyles();

  const sizeClasses = {
    xs: 'text-2xs px-1.5 py-0.5',
    sm: 'text-xs px-2 py-0.5',
    md: 'text-xs px-2.5 py-1',
  }[size];

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 font-mono font-semibold uppercase tracking-wider rounded border',
        styles.bg,
        styles.text,
        styles.border,
        sizeClasses,
        className
      )}
    >
      <span
        className={cn('w-1.5 h-1.5 rounded-full inline-block', styles.dot, {
          'blinking-dot': pulse,
        })}
      />
      {displayLabel}
    </span>
  );
};
