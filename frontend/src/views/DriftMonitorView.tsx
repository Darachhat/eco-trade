import React from 'react';
import { useModelStore } from '../stores/useModelStore';
import { DriftTable } from '../components/models/DriftTable';
import { MetricCard } from '../components/common/MetricCard';
import { Activity, AlertTriangle, ShieldCheck, RefreshCw } from 'lucide-react';

export const DriftMonitorView: React.FC = () => {
  const driftMetrics = useModelStore((s) => s.driftMetrics);

  const criticalCount = driftMetrics.filter((m) => m.status === 'CRITICAL').length;
  const warningCount = driftMetrics.filter((m) => m.status === 'WARNING').length;
  const normalCount = driftMetrics.filter((m) => m.status === 'NORMAL').length;

  return (
    <div className="space-y-4 p-3 font-mono">
      {/* 1. Header Banner */}
      <div className="terminal-panel p-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Activity className="w-5 h-5 text-terminal-cyan" />
          <div>
            <h1 className="text-sm font-bold text-terminal-text uppercase tracking-wider">
              Feature & Concept Drift Monitoring
            </h1>
            <p className="text-2xs text-terminal-muted">
              Population Stability Index (PSI) & Kolmogorov-Smirnov Distribution Shifts
            </p>
          </div>
        </div>
        <button className="px-3 py-1.5 bg-terminal-surface hover:bg-terminal-elevated text-terminal-text border border-terminal-border rounded text-2xs transition-colors flex items-center gap-1.5">
          <RefreshCw className="w-3.5 h-3.5" />
          Run Distribution Scan
        </button>
      </div>

      {/* 2. Drift KPI Overview */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        <MetricCard
          label="Monitored Features"
          value={driftMetrics.length}
          subValue="Realtime Bybit indicators"
          variant="cyan"
        />
        <MetricCard
          label="Stable Features (PSI < 0.1)"
          value={normalCount}
          subValue="Distribution aligned"
          variant="bull"
        />
        <MetricCard
          label="Warning Drift (PSI 0.1 - 0.25)"
          value={warningCount}
          subValue="Requires monitoring"
          variant={warningCount > 0 ? 'amber' : 'default'}
        />
        <MetricCard
          label="Critical Drift (PSI > 0.25)"
          value={criticalCount}
          subValue="Retraining suggested"
          variant={criticalCount > 0 ? 'bear' : 'bull'}
        />
      </div>

      {/* 3. Detailed Feature Drift Table */}
      <div className="terminal-panel flex flex-col">
        <div className="terminal-header">
          <span>Feature Distribution Drift Telemetry</span>
          <span className="text-2xs text-terminal-cyan">Baseline: 30-Day Training Window</span>
        </div>
        <div className="p-2">
          <DriftTable metrics={driftMetrics} />
        </div>
      </div>
    </div>
  );
};
