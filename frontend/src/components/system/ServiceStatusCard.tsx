import React from 'react';
import { ServiceHealthItem } from '../../types/system';
import { StatusBadge } from '../common/StatusBadge';
import { Server, Database, Activity, RefreshCw } from 'lucide-react';
import { cn } from '../../lib/utils';

export const ServiceStatusCard: React.FC<{ service: ServiceHealthItem }> = ({ service }) => {
  return (
    <div className="terminal-panel p-3 flex flex-col justify-between space-y-2">
      <div className="flex items-center justify-between border-b border-terminal-border/60 pb-2">
        <div className="flex items-center gap-2">
          <Server className="w-4 h-4 text-terminal-cyan" />
          <span className="font-mono font-bold text-xs text-terminal-text">{service.name}</span>
        </div>
        <StatusBadge variant={service.status} size="xs" pulse={service.status === 'HEALTHY'} />
      </div>

      <div className="grid grid-cols-2 gap-2 font-mono text-xs">
        <div className="terminal-card p-1.5 bg-terminal-surface/20">
          <span className="text-3xs uppercase text-terminal-muted block">Latency</span>
          <span className="font-bold text-terminal-text">{service.latencyMs} ms</span>
        </div>
        <div className="terminal-card p-1.5 bg-terminal-surface/20">
          <span className="text-3xs uppercase text-terminal-muted block">Uptime</span>
          <span className="font-bold text-terminal-bull">{service.uptimePct}%</span>
        </div>
      </div>

      <div className="flex items-center justify-between text-3xs font-mono text-terminal-dim pt-1 border-t border-terminal-border/40">
        <span className="truncate max-w-[140px]">{service.details}</span>
        <span>Heartbeat: {service.lastHeartbeat}</span>
      </div>
    </div>
  );
};
