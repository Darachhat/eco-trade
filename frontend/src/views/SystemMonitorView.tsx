import React from 'react';
import { useSystemStore } from '../stores/useSystemStore';
import { ServiceStatusCard } from '../components/system/ServiceStatusCard';
import { TerminalLogs } from '../components/system/TerminalLogs';
import { MetricCard } from '../components/common/MetricCard';
import { Server, Activity, Database, Cpu } from 'lucide-react';

export const SystemMonitorView: React.FC = () => {
  const services = useSystemStore((s) => s.services);
  const telemetry = useSystemStore((s) => s.telemetry);
  const logs = useSystemStore((s) => s.logs);

  return (
    <div className="space-y-4 p-3 font-mono">
      {/* 1. Header Banner */}
      <div className="terminal-panel p-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Server className="w-5 h-5 text-terminal-cyan" />
          <div>
            <h1 className="text-sm font-bold text-terminal-text uppercase tracking-wider">
              System Health & Infrastructure Telemetry
            </h1>
            <p className="text-2xs text-terminal-muted">
              FastAPI backend, TimescaleDB, Redis, Celery Task Queues, and Bybit WebSocket streams
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-2xs text-terminal-muted">
          <span className="w-2 h-2 rounded-full bg-terminal-bull blinking-dot" />
          <span>All Core Services Operational</span>
        </div>
      </div>

      {/* 2. Microservice Status Grid */}
      <div className="space-y-2">
        <div className="text-2xs uppercase tracking-widest text-terminal-muted font-semibold">
          Microservice Topology (7 Connected Nodes)
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
          {services.map((service) => (
            <ServiceStatusCard key={service.id} service={service} />
          ))}
        </div>
      </div>

      {/* 3. Infrastructure Telemetry KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
        <MetricCard label="CPU Load" value={`${telemetry.cpuUsagePct}%`} dense />
        <MetricCard label="Memory Usage" value={`${telemetry.ramUsagePct}%`} dense />
        <MetricCard label="DB Pool Active" value={`${telemetry.dbPoolActive} / ${telemetry.dbPoolMax}`} dense />
        <MetricCard label="Redis Memory" value={`${telemetry.redisMemoryMb} MB`} dense />
        <MetricCard label="Celery Active" value={`${telemetry.celeryActiveTasks} task`} dense />
        <MetricCard label="WS Clients" value={`${telemetry.wsClientsCount} peers`} dense />
        <MetricCard label="FastAPI RPS" value={`${telemetry.fastApiRps}/s`} dense />
      </div>

      {/* 4. Real-Time Engine Logs */}
      <div className="h-[380px]">
        <TerminalLogs logs={logs} />
      </div>
    </div>
  );
};
