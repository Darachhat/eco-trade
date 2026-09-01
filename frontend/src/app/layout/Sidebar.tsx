import React from 'react';
import {
  LayoutDashboard,
  CandlestickChart,
  Zap,
  Layers,
  Cpu,
  ShieldCheck,
  BarChart3,
  FlaskConical,
  GitBranch,
  Activity,
  BookOpen,
  Server,
  Radio,
  Lock,
} from 'lucide-react';
import { useTradingModeStore } from '../../stores/useTradingModeStore';
import { useSystemStore } from '../../stores/useSystemStore';
import { cn } from '../../lib/utils';

export type NavTab =
  | 'overview'
  | 'markets'
  | 'signals'
  | 'positions'
  | 'scalper'
  | 'ai'
  | 'risk'
  | 'backtest'
  | 'research'
  | 'model-lab'
  | 'drift'
  | 'journal'
  | 'system';

interface SidebarProps {
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
  className?: string;
  onCloseMobile?: () => void;
}

const NAV_ITEMS: { id: NavTab; label: string; icon: React.ReactNode; badge?: string }[] = [
  { id: 'overview', label: 'Overview', icon: <LayoutDashboard className="w-4 h-4" /> },
  { id: 'markets', label: 'Market Terminal', icon: <CandlestickChart className="w-4 h-4" /> },
  { id: 'signals', label: 'AI Signals', icon: <Zap className="w-4 h-4" />, badge: 'LIVE' },
  { id: 'scalper', label: 'MT5 Scalper', icon: <Server className="w-4 h-4 text-terminal-bull" />, badge: 'EXNESS' },
  { id: 'positions', label: 'Positions', icon: <Layers className="w-4 h-4" /> },
  { id: 'ai', label: 'AI Intelligence', icon: <Cpu className="w-4 h-4" /> },
  { id: 'risk', label: 'Risk Center', icon: <ShieldCheck className="w-4 h-4" /> },
  { id: 'backtest', label: 'Backtesting', icon: <BarChart3 className="w-4 h-4" /> },
  { id: 'research', label: 'Research & Monte Carlo', icon: <FlaskConical className="w-4 h-4" /> },
  { id: 'model-lab', label: 'Model Lab', icon: <GitBranch className="w-4 h-4" /> },
  { id: 'drift', label: 'Drift Monitor', icon: <Activity className="w-4 h-4" /> },
  { id: 'journal', label: 'Trade Journal', icon: <BookOpen className="w-4 h-4" /> },
  { id: 'system', label: 'System Monitor', icon: <Server className="w-4 h-4" /> },
];

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onTabChange,
  className,
  onCloseMobile,
}) => {
  const mode = useTradingModeStore((s) => s.mode);
  const environment = useTradingModeStore((s) => s.environment);
  const wsState = useSystemStore((s) => s.wsState);

  const handleSelect = (tab: NavTab) => {
    onTabChange(tab);
    onCloseMobile?.();
  };

  return (
    <aside
      className={cn(
        'w-56 bg-terminal-panel border-r border-terminal-border flex flex-col justify-between select-none font-mono text-xs shrink-0',
        className
      )}
    >
      {/* Navigation List */}
      <div className="p-2 space-y-0.5 overflow-y-auto">
        <div className="px-2.5 py-1.5 text-3xs uppercase tracking-widest text-terminal-dim font-bold">
          Quantitative Terminal
        </div>

        {NAV_ITEMS.map((item) => {
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => handleSelect(item.id)}
              className={cn(
                'w-full flex items-center justify-between px-2.5 py-2 rounded text-xs transition-colors group',
                isActive
                  ? 'bg-terminal-cyan/15 text-terminal-cyan font-bold border-l-2 border-terminal-cyan pl-2'
                  : 'text-terminal-muted hover:text-terminal-text hover:bg-terminal-surface/70'
              )}
            >
              <div className="flex items-center gap-2.5">
                <span className={cn(isActive ? 'text-terminal-cyan' : 'text-terminal-dim group-hover:text-terminal-muted')}>
                  {item.icon}
                </span>
                <span>{item.label}</span>
              </div>
              {item.badge && (
                <span className="text-3xs px-1 py-0.2 bg-terminal-bullDim text-terminal-bull rounded border border-terminal-bullBorder">
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Bottom Telemetry & Status Widgets */}
      <div className="p-3 border-t border-terminal-border/80 bg-terminal-surface/30 space-y-2 text-2xs">
        <div className="space-y-1">
          <div className="flex items-center justify-between text-terminal-muted">
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-terminal-bull" />
              Bybit REST:
            </span>
            <span className="text-terminal-text font-bold">HEALTHY</span>
          </div>

          <div className="flex items-center justify-between text-terminal-muted">
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-terminal-bull" />
              WebSocket Feed:
            </span>
            <span className="text-terminal-bull font-bold">LIVE</span>
          </div>

          <div className="flex items-center justify-between text-terminal-muted">
            <span>Environment:</span>
            <span className="text-terminal-cyan font-bold uppercase">{environment}</span>
          </div>

          <div className="flex items-center justify-between text-terminal-muted">
            <span>Trading Mode:</span>
            <span className={cn('font-bold uppercase', mode === 'live' ? 'text-terminal-bear' : 'text-terminal-text')}>
              {mode}
            </span>
          </div>
        </div>

        <div className="pt-2 border-t border-terminal-border/40 text-3xs text-terminal-dim text-center">
          EcoTrade AI Quant Terminal v1.0.0
        </div>
      </div>
    </aside>
  );
};
