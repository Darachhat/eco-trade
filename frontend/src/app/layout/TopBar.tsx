import React from 'react';
import { useMarketStore } from '../../stores/useMarketStore';
import { useTradingModeStore } from '../../stores/useTradingModeStore';
import { useSystemStore } from '../../stores/useSystemStore';
import { useMT5Store } from '../../stores/useMT5Store';
import { MT5ConnectModal } from '../../components/trading/MT5ConnectModal';
import { SymbolName, Timeframe } from '../../types/market';
import { formatPrice, formatPercent, formatCurrency } from '../../lib/formatters/formatters';
import {
  Activity,
  ShieldAlert,
  Radio,
  Database,
  Layers,
  ChevronDown,
  Lock,
  Cpu,
  Server,
} from 'lucide-react';
import { cn } from '../../lib/utils';

const SYMBOLS: SymbolName[] = ['BTCUSDT', 'XAUUSDT'];
const TIMEFRAMES: Timeframe[] = ['1m', '5m', '15m', '1h', '4h', '1D'];

export const TopBar: React.FC<{ onMenuToggle?: () => void }> = ({ onMenuToggle }) => {
  const activeSymbol = useMarketStore((s) => s.activeSymbol);
  const setActiveSymbol = useMarketStore((s) => s.setActiveSymbol);
  const activeTimeframe = useMarketStore((s) => s.activeTimeframe);
  const setActiveTimeframe = useMarketStore((s) => s.setActiveTimeframe);
  const tickers = useMarketStore((s) => s.tickers);

  const mode = useTradingModeStore((s) => s.mode);
  const environment = useTradingModeStore((s) => s.environment);
  const setMode = useTradingModeStore((s) => s.setMode);
  const setEnvironment = useTradingModeStore((s) => s.setEnvironment);

  const wsState = useSystemStore((s) => s.wsState);

  const isMT5Connected = useMT5Store((s) => s.isConnected);
  const mt5Account = useMT5Store((s) => s.account);
  const setIsConnectModalOpen = useMT5Store((s) => s.setIsConnectModalOpen);

  const currentTicker = tickers[activeSymbol] || tickers['BTCUSDT'];

  return (
    <header className="h-12 bg-terminal-panel border-b border-terminal-border flex items-center justify-between px-3 font-mono text-xs select-none shrink-0 z-30">
      {/* 1. Left: Brand & Symbol / Ticker Selector */}
      <div className="flex items-center gap-3">
        {/* Mobile menu trigger */}
        <button
          onClick={onMenuToggle}
          className="lg:hidden p-1.5 text-terminal-muted hover:text-terminal-text rounded bg-terminal-surface"
        >
          <Layers className="w-4 h-4" />
        </button>

        {/* Brand */}
        <div className="flex items-center gap-2 pr-2 border-r border-terminal-border/80">
          <div className="w-6 h-6 rounded bg-terminal-cyan/10 border border-terminal-cyan/40 flex items-center justify-center text-terminal-cyan font-bold text-xs">
            <Cpu className="w-3.5 h-3.5" />
          </div>
          <span className="font-bold text-sm text-terminal-text tracking-wider">ECOTRADE</span>
        </div>

        {/* Symbol Dropdown */}
        <div className="flex items-center gap-1.5">
          <select
            value={activeSymbol}
            onChange={(e) => setActiveSymbol(e.target.value as SymbolName)}
            className="bg-terminal-surface border border-terminal-border/80 rounded px-2 py-1 font-bold text-xs text-terminal-text focus:outline-none focus:border-terminal-cyan cursor-pointer"
          >
            {SYMBOLS.map((sym) => (
              <option key={sym} value={sym}>
                {sym}
              </option>
            ))}
          </select>

          {/* Live Price & Change */}
          <div className="flex items-baseline gap-2 pl-1">
            <span className="font-bold text-sm text-terminal-text">
              ${formatPrice(currentTicker.price, activeSymbol)}
            </span>
            <span
              className={cn(
                'font-semibold text-2xs',
                currentTicker.change24h >= 0 ? 'text-terminal-bull' : 'text-terminal-bear'
              )}
            >
              {formatPercent(currentTicker.change24h)}
            </span>
          </div>
        </div>

        {/* Timeframe Switcher */}
        <div className="hidden md:flex items-center gap-0.5 pl-3 border-l border-terminal-border/60">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf}
              onClick={() => setActiveTimeframe(tf)}
              className={cn(
                'px-2 py-0.5 rounded text-2xs font-semibold transition-colors',
                activeTimeframe === tf
                  ? 'bg-terminal-cyan text-black'
                  : 'text-terminal-muted hover:text-terminal-text hover:bg-terminal-surface'
              )}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>

      {/* 2. Center: Real-time Status Badge */}
      <div className="hidden xl:flex items-center gap-2 text-2xs text-terminal-muted">
        <span className="w-2 h-2 rounded-full bg-terminal-bull animate-pulse" />
        <span className="font-semibold text-terminal-dim tracking-wider">
          MARKET OPEN • BYBIT 24/7 & EXNESS MT5
        </span>
      </div>

      {/* 3. Right: Exness MT5 Bridge, System Telemetry & Mode Toggles */}
      <div className="flex items-center gap-2.5">
        {/* Exness MT5 Status Button */}
        <button
          type="button"
          onClick={() => setIsConnectModalOpen(true)}
          className={cn(
            'flex items-center gap-1.5 px-2.5 py-1 rounded text-2xs font-bold border transition-colors cursor-pointer',
            isMT5Connected
              ? 'bg-terminal-bull/10 border-terminal-bull/40 text-terminal-bull hover:bg-terminal-bull/20'
              : 'bg-terminal-surface border-terminal-border text-terminal-muted hover:text-terminal-text'
          )}
          title="Click to manage Exness MT5 Account Connection"
        >
          <Server className="w-3.5 h-3.5" />
          <span>EXNESS MT5:</span>
          <span className="text-terminal-text">
            {mt5Account ? formatCurrency(mt5Account.balance) : 'DEMO'}
          </span>
          <span className="w-1.5 h-1.5 rounded-full bg-terminal-bull animate-pulse" />
        </button>

        {/* Backend & Feed Telemetry Status Lights */}
        <div className="hidden md:flex items-center gap-2 text-3xs text-terminal-muted pr-2 border-r border-terminal-border/80">
          <div className="flex items-center gap-1" title="Bybit WebSocket">
            <span
              className={cn(
                'w-1.5 h-1.5 rounded-full',
                wsState === 'CONNECTED' ? 'bg-terminal-bull' : 'bg-terminal-warning animate-ping'
              )}
            />
            <span>WS</span>
          </div>
          <div className="flex items-center gap-1" title="FastAPI Backend">
            <span className="w-1.5 h-1.5 rounded-full bg-terminal-bull" />
            <span>API</span>
          </div>
          <div className="flex items-center gap-1" title="TimescaleDB">
            <span className="w-1.5 h-1.5 rounded-full bg-terminal-bull" />
            <span>DB</span>
          </div>
        </div>

        {/* Environment Toggle (TESTNET / MAINNET) */}
        <button
          onClick={() => setEnvironment(environment === 'testnet' ? 'mainnet' : 'testnet')}
          className="hidden sm:block text-3xs px-2 py-0.5 rounded border border-terminal-border bg-terminal-surface text-terminal-muted hover:text-terminal-text transition-colors"
        >
          ENV: <strong className="text-terminal-cyan uppercase">{environment}</strong>
        </button>

        {/* Trading Mode Button (PAPER vs LIVE with warning) */}
        <div className="flex items-center">
          {mode === 'live' ? (
            <button
              onClick={() => setMode('paper')}
              className="px-2.5 py-1 bg-terminal-bear text-white rounded font-bold text-2xs uppercase tracking-wider flex items-center gap-1.5 shadow-bear-glow animate-pulse"
            >
              <ShieldAlert className="w-3.5 h-3.5" />
              ⚠ LIVE TRADING
            </button>
          ) : (
            <button
              onClick={() => setMode('live')}
              className="px-2.5 py-1 bg-terminal-surface hover:bg-terminal-elevated text-terminal-cyan border border-terminal-cyan/30 rounded font-bold text-2xs uppercase tracking-wider transition-colors flex items-center gap-1.5"
            >
              <Lock className="w-3 h-3 text-terminal-cyan" />
              PAPER TRADING
            </button>
          )}
        </div>
      </div>

      {/* MT5 Connect Modal */}
      <MT5ConnectModal />
    </header>
  );
};
