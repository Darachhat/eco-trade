import React from 'react';
import { SHAPFeatureContribution } from '../../types/signal';
import { cn } from '../../lib/utils';

interface SHAPWaterfallProps {
  contributions: SHAPFeatureContribution[];
}

export const SHAPWaterfall: React.FC<SHAPWaterfallProps> = ({ contributions }) => {
  const maxAbsShap = Math.max(...contributions.map((c) => Math.abs(c.shapValue)), 0.01);

  return (
    <div className="space-y-2 font-mono text-xs">
      <div className="flex items-center justify-between text-2xs uppercase tracking-widest text-terminal-muted font-semibold pb-1 border-b border-terminal-border/60">
        <span>Feature Name</span>
        <div className="flex items-center gap-4">
          <span className="text-terminal-bear">◀ Bearish Influence</span>
          <span className="text-terminal-bull">Bullish Influence ▶</span>
        </div>
      </div>

      <div className="space-y-1.5 pt-1">
        {contributions.map((c, idx) => {
          const isPos = c.shapValue >= 0;
          const barWidthPct = Math.min(100, Math.round((Math.abs(c.shapValue) / maxAbsShap) * 100));

          return (
            <div
              key={idx}
              className="grid grid-cols-12 items-center gap-2 py-1 px-2 hover:bg-terminal-elevated/40 rounded transition-colors"
            >
              {/* Feature info */}
              <div className="col-span-5 flex flex-col">
                <span className="font-bold text-terminal-text text-2xs">{c.feature}</span>
                <span className="text-3xs text-terminal-dim truncate">{c.description}</span>
              </div>

              {/* Centered zero line comparison */}
              <div className="col-span-5 flex items-center h-4 relative bg-terminal-surface/50 rounded overflow-hidden">
                {/* Center marker */}
                <div className="absolute left-1/2 top-0 bottom-0 w-px bg-terminal-border z-10" />

                {isPos ? (
                  <div
                    className="h-full bg-terminal-bull rounded-r"
                    style={{
                      marginLeft: '50%',
                      width: `${barWidthPct / 2}%`,
                    }}
                  />
                ) : (
                  <div
                    className="h-full bg-terminal-bear rounded-l"
                    style={{
                      marginLeft: `${50 - barWidthPct / 2}%`,
                      width: `${barWidthPct / 2}%`,
                    }}
                  />
                )}
              </div>

              {/* Numerical SHAP Value */}
              <div className="col-span-2 text-right">
                <span
                  className={cn(
                    'font-bold text-2xs',
                    isPos ? 'text-terminal-bull' : 'text-terminal-bear'
                  )}
                >
                  {isPos ? `+${c.shapValue.toFixed(2)}` : c.shapValue.toFixed(2)}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
