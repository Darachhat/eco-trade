import React, { useEffect, useState } from 'react';
import { useMarketStore } from '../../stores/useMarketStore';
import { useModelStore } from '../../stores/useModelStore';
import { useRiskStore } from '../../stores/useRiskStore';
import { useTradingModeStore } from '../../stores/useTradingModeStore';
import { Activity, ShieldCheck, Radio, Clock, Cpu } from 'lucide-react';
import { cn } from '../../lib/utils';

export const StatusBar: React.FC = () => {
  const regime = useModelStore((s) => s.regime);
  const models = useModelStore((s) => s.models);
  const riskStatus = useRiskStore((s) => s.riskStatus);
  const mode = useTradingModeStore((s) => s.mode);

  const [utcTime, setUtcTime] = useState<string>('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setUtcTime(now.toUTCString().replace('GMT', 'UTC'));
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const champion = models.find((m) => m.champion) || models[0];

  return (
    <footer className="h-6 bg-terminal-panel border-t border-terminal-border flex items-center justify-between px-3 font-mono text-3xs text-terminal-muted select-none shrink-0 z-30">
      {/* Left: Feed Telemetry */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1 text-terminal-bull">
          <span className="w-1.5 h-1.5 rounded-full bg-terminal-bull blinking-dot" />
          <span className="font-bold">BYBIT LIVE STREAM (18ms)</span>
        </div>

        <div className="hidden sm:flex items-center gap-1.5 text-terminal-text">
          <Activity className="w-3 h-3 text-terminal-cyan" />
          <span>Regime: <strong className="text-terminal-bull">{regime.currentRegime} ({regime.probability}%)</strong></span>
        </div>

        <div className="hidden md:flex items-center gap-1.5">
          <Cpu className="w-3 h-3 text-terminal-cyan" />
          <span>Champion: <strong className="text-terminal-text">{champion?.name} {champion?.version}</strong></span>
        </div>
      </div>

      {/* Right: Risk & Clock */}
      <div className="flex items-center gap-4">
        <div className="hidden lg:flex items-center gap-1.5">
          <ShieldCheck className="w-3 h-3 text-terminal-bull" />
          <span>Risk: <strong className="text-terminal-text">{riskStatus.dailyLossPct.toFixed(1)}% / {riskStatus.dailyLossLimitPct}% Daily Loss</strong></span>
        </div>

        <div className="flex items-center gap-1.5 text-terminal-dim">
          <Clock className="w-3 h-3" />
          <span>{utcTime}</span>
        </div>
      </div>
    </footer>
  );
};
