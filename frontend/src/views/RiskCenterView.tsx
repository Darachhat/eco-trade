import React from 'react';
import { useRiskStore } from '../stores/useRiskStore';
import { RiskGauge } from '../components/common/RiskGauge';
import { MetricCard } from '../components/common/MetricCard';
import { KillSwitchModal } from '../components/common/KillSwitchModal';
import { StatusBadge } from '../components/common/StatusBadge';
import { formatCurrency, formatPercent } from '../lib/formatters/formatters';
import {
  ShieldAlert,
  ShieldCheck,
  Octagon,
  PauseCircle,
  PlayCircle,
  AlertTriangle,
  Lock,
} from 'lucide-react';
import { cn } from '../lib/utils';

export const RiskCenterView: React.FC = () => {
  const riskStatus = useRiskStore((s) => s.riskStatus);
  const setIsKillSwitchModalOpen = useRiskStore((s) => s.setIsKillSwitchModalOpen);
  const deactivateKillSwitch = useRiskStore((s) => s.deactivateKillSwitch);
  const togglePauseTrading = useRiskStore((s) => s.togglePauseTrading);

  return (
    <div className="space-y-4 p-3 font-mono">
      {/* 1. Header & Emergency Controls */}
      <div className="terminal-panel p-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <ShieldCheck className="w-6 h-6 text-terminal-bull" />
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm font-bold text-terminal-text uppercase tracking-wider">
                Risk Management & Circuit Breakers
              </h1>
              <StatusBadge
                variant={riskStatus.killSwitchActive ? 'CRITICAL' : riskStatus.tradingPaused ? 'WARNING' : 'HEALTHY'}
                label={riskStatus.killSwitchActive ? 'EMERGENCY HALTED' : riskStatus.tradingPaused ? 'PAUSED' : 'ACTIVE'}
                pulse
              />
            </div>
            <p className="text-2xs text-terminal-muted">
              Pre-flight order validation, hard stop guards, drawdown circuit breakers
            </p>
          </div>
        </div>

        {/* Emergency Kill Switch & Pause Actions */}
        <div className="flex items-center gap-2.5">
          <button
            onClick={togglePauseTrading}
            className={cn(
              'px-3 py-1.5 rounded font-bold text-2xs uppercase tracking-wider border transition-colors flex items-center gap-1.5',
              riskStatus.tradingPaused
                ? 'bg-terminal-bullDim text-terminal-bull border-terminal-bullBorder hover:bg-terminal-bull hover:text-black'
                : 'bg-terminal-amberDim text-terminal-amber border-terminal-amber/40 hover:bg-terminal-amber hover:text-black'
            )}
          >
            {riskStatus.tradingPaused ? (
              <>
                <PlayCircle className="w-4 h-4" />
                Resume Trading
              </>
            ) : (
              <>
                <PauseCircle className="w-4 h-4" />
                Pause Trading
              </>
            )}
          </button>

          {riskStatus.killSwitchActive ? (
            <button
              onClick={deactivateKillSwitch}
              className="px-4 py-1.5 bg-terminal-surface hover:bg-terminal-elevated text-terminal-cyan border border-terminal-cyan/40 rounded font-bold text-2xs uppercase tracking-wider transition-colors flex items-center gap-1.5"
            >
              Reset Kill Switch
            </button>
          ) : (
            <button
              onClick={() => setIsKillSwitchModalOpen(true)}
              className="px-4 py-1.5 bg-terminal-bear hover:bg-red-700 text-white font-bold text-2xs rounded uppercase tracking-wider transition-colors flex items-center gap-1.5 shadow-bear-glow"
            >
              <Octagon className="w-4 h-4" />
              EMERGENCY KILL SWITCH
            </button>
          )}
        </div>
      </div>

      {/* 2. Top Summary KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        <MetricCard
          label="Account Equity"
          value={formatCurrency(riskStatus.accountEquity)}
          subValue={`Initial: ${formatCurrency(riskStatus.initialBalance)}`}
          variant="cyan"
        />
        <MetricCard
          label="Daily Loss Limit"
          value={`$${riskStatus.dailyLossUsd.toFixed(2)} / $${riskStatus.dailyLossLimitUsd.toFixed(2)}`}
          subValue={`${riskStatus.dailyLossPct.toFixed(2)}% / ${riskStatus.dailyLossLimitPct.toFixed(2)}% limit`}
          variant="bull"
        />
        <MetricCard
          label="Weekly Drawdown"
          value={`${riskStatus.weeklyDrawdownPct.toFixed(2)}% / ${riskStatus.weeklyDrawdownLimitPct.toFixed(2)}%`}
          subValue="Hard circuit breaker at 6.0%"
          variant="bear"
        />
        <MetricCard
          label="Risk Per Trade Sizing"
          value={`${riskStatus.riskPerTradePct.toFixed(1)}%`}
          subValue={`Fixed fractional Kelly fraction: 0.35`}
        />
      </div>

      {/* 3. Risk Limit Progress Gauges */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
        <RiskGauge
          label="Daily Loss Ceiling"
          current={riskStatus.dailyLossPct}
          limit={riskStatus.dailyLossLimitPct}
        />
        <RiskGauge
          label="Weekly Drawdown Limit"
          current={riskStatus.weeklyDrawdownPct}
          limit={riskStatus.weeklyDrawdownLimitPct}
        />
        <RiskGauge
          label="Concurrent Positions"
          current={riskStatus.openPositionsCount}
          limit={riskStatus.maxOpenPositions}
          unit=" pos"
          isPercent={false}
        />
        <RiskGauge
          label="Consecutive Loss Guard"
          current={riskStatus.consecutiveLosses}
          limit={riskStatus.maxConsecutiveLosses}
          unit=" loss"
          isPercent={false}
        />
      </div>

      {/* 4. Active Circuit Breakers Rules Engine */}
      <div className="terminal-panel flex flex-col">
        <div className="terminal-header">
          <div className="flex items-center gap-2">
            <Lock className="w-3.5 h-3.5 text-terminal-cyan" />
            <span>Automated Circuit Breaker Guardrails (Enforced Pre-Order)</span>
          </div>
          <span className="text-2xs text-terminal-muted font-mono">5 Active Interceptors</span>
        </div>

        <div className="p-2 overflow-x-auto">
          <table className="terminal-table">
            <thead>
              <tr>
                <th>Rule Name</th>
                <th>Trigger Condition</th>
                <th>Current Telemetry</th>
                <th>Safety Threshold</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {riskStatus.circuitBreakers.map((cb) => (
                <tr key={cb.id}>
                  <td className="font-bold text-terminal-text">{cb.name}</td>
                  <td className="text-terminal-muted">{cb.condition}</td>
                  <td className="font-mono font-bold text-terminal-text">{cb.currentValue}</td>
                  <td className="font-mono text-terminal-dim">{cb.threshold}</td>
                  <td>
                    <StatusBadge variant={cb.status} size="xs" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Kill Switch Modal */}
      <KillSwitchModal />
    </div>
  );
};
