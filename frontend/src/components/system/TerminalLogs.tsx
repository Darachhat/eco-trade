import React, { useState } from 'react';
import { SystemLogEntry } from '../../types/system';
import { formatTimestamp } from '../../lib/formatters/formatters';
import { Terminal, Filter, Trash2 } from 'lucide-react';
import { cn } from '../../lib/utils';

export const TerminalLogs: React.FC<{ logs: SystemLogEntry[] }> = ({ logs }) => {
  const [filterLevel, setFilterLevel] = useState<string>('ALL');

  const filteredLogs = logs.filter(
    (l) => filterLevel === 'ALL' || l.level === filterLevel
  );

  return (
    <div className="terminal-panel flex flex-col h-full">
      <div className="terminal-header">
        <div className="flex items-center gap-2">
          <Terminal className="w-3.5 h-3.5 text-terminal-cyan" />
          <span>Real-time System & Signal Engine Logs</span>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={filterLevel}
            onChange={(e) => setFilterLevel(e.target.value)}
            className="bg-terminal-bg border border-terminal-border rounded text-3xs font-mono px-1.5 py-0.5 text-terminal-text focus:outline-none"
          >
            <option value="ALL">ALL LEVELS</option>
            <option value="INFO">INFO</option>
            <option value="WARNING">WARNING</option>
            <option value="ERROR">ERROR</option>
            <option value="DEBUG">DEBUG</option>
          </select>
        </div>
      </div>

      <div className="flex-1 p-3 overflow-y-auto font-mono text-2xs space-y-1 bg-terminal-bg/80 select-text min-h-[220px]">
        {filteredLogs.map((log) => {
          const levelColor = {
            INFO: 'text-terminal-cyan',
            WARNING: 'text-terminal-amber font-semibold',
            ERROR: 'text-terminal-bear font-bold',
            DEBUG: 'text-terminal-dim',
          }[log.level] || 'text-terminal-muted';

          return (
            <div key={log.id} className="flex items-start gap-2 hover:bg-terminal-surface/50 px-1 py-0.5 rounded leading-relaxed">
              <span className="text-terminal-dim shrink-0">{formatTimestamp(log.timestamp)}</span>
              <span className={cn('shrink-0 px-1 rounded text-3xs border border-terminal-border/40', levelColor)}>
                [{log.level}]
              </span>
              <span className="text-terminal-muted shrink-0 font-semibold">{log.service}:</span>
              <span className="text-terminal-text break-all">{log.message}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
