import React from 'react';
import { useModelStore } from '../stores/useModelStore';
import { ChallengerComparison } from '../components/models/ChallengerComparison';
import { StatusBadge } from '../components/common/StatusBadge';
import { FlaskConical, Sliders, RefreshCw, Cpu, Award } from 'lucide-react';

export const ModelLabView: React.FC = () => {
  const optunaTrials = useModelStore((s) => s.optunaTrials);

  return (
    <div className="space-y-4 p-3 font-mono">
      {/* 1. Header Banner */}
      <div className="terminal-panel p-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Cpu className="w-5 h-5 text-terminal-cyan" />
          <div>
            <h1 className="text-sm font-bold text-terminal-text uppercase tracking-wider">
              Model Lab & Self-Learning Lifecycle
            </h1>
            <p className="text-2xs text-terminal-muted">
              Champion vs Challenger Out-of-Sample Protocol, Optuna Hyperparameter Optimization
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button className="px-3 py-1.5 bg-terminal-surface hover:bg-terminal-elevated text-terminal-text border border-terminal-border rounded text-2xs transition-colors flex items-center gap-1.5">
            <RefreshCw className="w-3.5 h-3.5" />
            Trigger Retrain Cycle
          </button>
        </div>
      </div>

      {/* 2. Champion vs Challenger Comparison */}
      <ChallengerComparison />

      {/* 3. Optuna Hyperparameter Optimization Trials */}
      <div className="terminal-panel flex flex-col">
        <div className="terminal-header">
          <div className="flex items-center gap-2">
            <Sliders className="w-3.5 h-3.5 text-terminal-cyan" />
            <span>Optuna Bayesian TPE Hyperparameter Tuning Runs (Recent Trials)</span>
          </div>
          <span className="text-2xs text-terminal-muted">Objective: Maximize Validation Sharpe</span>
        </div>

        <div className="p-2 overflow-x-auto">
          <table className="terminal-table">
            <thead>
              <tr>
                <th>Trial #</th>
                <th>Objective (Sharpe)</th>
                <th>Hyperparameters Evaluated</th>
                <th>Execution Time</th>
                <th>State</th>
              </tr>
            </thead>
            <tbody>
              {optunaTrials.map((tr) => (
                <tr key={tr.trialNumber}>
                  <td className="font-bold text-terminal-text">Trial #{tr.trialNumber}</td>
                  <td className="font-bold text-terminal-cyan">{tr.value.toFixed(2)}</td>
                  <td className="text-terminal-muted text-2xs">
                    {Object.entries(tr.params)
                      .map(([k, v]) => `${k}=${v}`)
                      .join(', ')}
                  </td>
                  <td className="text-terminal-dim">{tr.durationSeconds}s</td>
                  <td>
                    <StatusBadge variant={tr.state === 'COMPLETE' ? 'VALID' : 'WATCH'} label={tr.state} size="xs" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
