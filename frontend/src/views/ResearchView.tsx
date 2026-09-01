import React from 'react';
import { useBacktestStore } from '../stores/useBacktestStore';
import { MonteCarloFanChart } from '../components/charts/MonteCarloFanChart';
import { WalkForwardVisualizer } from '../components/charts/WalkForwardVisualizer';
import { OptimizationSurface } from '../components/charts/OptimizationSurface';
import { FlaskConical, TrendingUp, Layers, Activity } from 'lucide-react';

export const ResearchView: React.FC = () => {
  const result = useBacktestStore((s) => s.result);

  if (!result) return null;

  return (
    <div className="space-y-4 p-3 font-mono">
      {/* 1. Header Banner */}
      <div className="terminal-panel p-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <FlaskConical className="w-5 h-5 text-terminal-cyan" />
          <div>
            <h1 className="text-sm font-bold text-terminal-text uppercase tracking-wider">
              Quantitative Research & Robustness Suite
            </h1>
            <p className="text-2xs text-terminal-muted">
              Walk-Forward Efficiency, 1,000-Path Monte Carlo Stress Testing, Parameter Surfaces
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3 text-2xs text-terminal-muted">
          <span>Active Strategy: <strong className="text-terminal-cyan">{result.config.strategy}</strong></span>
        </div>
      </div>

      {/* 2. Monte Carlo Simulation Fan Chart */}
      <div className="terminal-panel p-4">
        <MonteCarloFanChart data={result.monteCarlo} />
      </div>

      {/* 3. Walk-Forward Analysis Visualizer */}
      <div className="terminal-panel p-4">
        <WalkForwardVisualizer windows={result.walkForward} />
      </div>

      {/* 4. Parameter Sensitivity Optimization Matrix */}
      <div className="terminal-panel p-4">
        <OptimizationSurface data={result.optimizationSurface} />
      </div>
    </div>
  );
};
