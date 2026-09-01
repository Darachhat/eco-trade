import React from 'react';
import { WalkForwardWindow } from '../../types/backtest';
import { cn } from '../../lib/utils';

interface WalkForwardVisualizerProps {
  windows: WalkForwardWindow[];
}

export const WalkForwardVisualizer: React.FC<WalkForwardVisualizerProps> = ({ windows }) => {
  return (
    <div className="space-y-4 font-mono text-xs">
      <div className="text-2xs uppercase tracking-widest text-terminal-muted font-semibold">
        Rolling Train / Validation / Out-of-Sample Test Windows
      </div>

      <div className="space-y-3">
        {windows.map((win) => (
          <div key={win.windowIndex} className="terminal-card p-3 space-y-2">
            <div className="flex items-center justify-between text-2xs">
              <span className="font-bold text-terminal-text">WINDOW #{win.windowIndex}</span>
              <div className="flex items-center gap-3">
                <span className="text-terminal-muted">
                  WFE Ratio: <strong className="text-terminal-cyan">{(win.wfeRatio * 100).toFixed(0)}%</strong>
                </span>
                <span className="text-terminal-muted">
                  Stability: <strong className="text-terminal-bull">{win.stabilityScore}%</strong>
                </span>
              </div>
            </div>

            {/* Split Visualization Bar */}
            <div className="h-5 w-full bg-terminal-bg rounded flex overflow-hidden border border-terminal-border/80">
              <div
                className="bg-terminal-blue/40 border-r border-terminal-border flex items-center justify-center text-3xs font-bold text-terminal-cyan px-1"
                style={{ width: '45%' }}
                title={`Train: ${win.trainRange}`}
              >
                TRAIN ({win.trainRange})
              </div>
              <div
                className="bg-terminal-amber/30 border-r border-terminal-border flex items-center justify-center text-3xs font-bold text-terminal-amber px-1"
                style={{ width: '25%' }}
                title={`Validation: ${win.valRange}`}
              >
                VAL ({win.valRange})
              </div>
              <div
                className="bg-terminal-bull/40 flex items-center justify-center text-3xs font-bold text-terminal-bull px-1"
                style={{ width: '30%' }}
                title={`Out-of-Sample Test: ${win.testRange}`}
              >
                TEST ({win.testRange})
              </div>
            </div>

            <div className="flex items-center justify-between text-2xs text-terminal-muted pt-1">
              <span>
                In-Sample Sharpe: <strong className="text-terminal-text">{win.inSampleSharpe.toFixed(2)}</strong>
              </span>
              <span>
                Out-of-Sample Sharpe:{' '}
                <strong className={cn(win.outOfSampleSharpe > 1.5 ? 'text-terminal-bull' : 'text-terminal-amber')}>
                  {win.outOfSampleSharpe.toFixed(2)}
                </strong>
              </span>
              <span className="text-terminal-dim">{win.parameterShift}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
