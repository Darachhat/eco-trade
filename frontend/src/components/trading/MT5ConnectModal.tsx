import React, { useState } from 'react';
import { useMT5Store } from '../../stores/useMT5Store';
import { formatCurrency } from '../../lib/formatters/formatters';
import {
  X,
  ShieldCheck,
  Zap,
  Server,
  Key,
  User,
  CheckCircle2,
  RefreshCw,
  AlertCircle,
  ExternalLink,
} from 'lucide-react';
import { cn } from '../../lib/utils';

export const MT5ConnectModal: React.FC = () => {
  const isConnectModalOpen = useMT5Store((s) => s.isConnectModalOpen);
  const setIsConnectModalOpen = useMT5Store((s) => s.setIsConnectModalOpen);
  const isConnected = useMT5Store((s) => s.isConnected);
  const isLoading = useMT5Store((s) => s.isLoading);
  const account = useMT5Store((s) => s.account);
  const credentials = useMT5Store((s) => s.credentials);
  const connectMT5 = useMT5Store((s) => s.connectMT5);

  const [login, setLogin] = useState(credentials.login.toString());
  const [password, setPassword] = useState(credentials.password);
  const [server, setServer] = useState(credentials.server);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  if (!isConnectModalOpen) return null;

  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatusMsg('Connecting to Exness MetaTrader 5 terminal...');
    const ok = await connectMT5({
      login: parseInt(login, 10) || 463894594,
      password,
      server,
    });
    if (ok) {
      setStatusMsg('Connected successfully to Exness MT5!');
      setTimeout(() => {
        setStatusMsg(null);
        setIsConnectModalOpen(false);
      }, 800);
    } else {
      setStatusMsg('Connection failed. Please check credentials or ensure MT5 is running.');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in font-mono text-xs">
      <div className="bg-terminal-panel border border-terminal-border rounded-lg max-w-md w-full shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-terminal-border flex items-center justify-between bg-terminal-surface/40">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded bg-terminal-bull/10 border border-terminal-bull/40 flex items-center justify-center text-terminal-bull">
              <Server className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-bold text-sm text-terminal-text uppercase tracking-wider">
                  Exness MetaTrader 5 Bridge
                </h2>
                <span
                  className={cn(
                    'px-1.5 py-0.5 rounded text-3xs font-bold',
                    isConnected ? 'bg-terminal-bull/20 text-terminal-bull' : 'bg-terminal-bear/20 text-terminal-bear'
                  )}
                >
                  {isConnected ? 'CONNECTED' : 'DISCONNECTED'}
                </span>
              </div>
              <span className="text-3xs text-terminal-muted">
                Direct IPC connection to MetaTrader 5 desktop client
              </span>
            </div>
          </div>

          <button
            onClick={() => setIsConnectModalOpen(false)}
            className="p-1 rounded text-terminal-muted hover:text-terminal-text hover:bg-terminal-elevated transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleConnect} className="p-4 space-y-4">
          {/* Active Account Telemetry Card */}
          {isConnected && account && (
            <div className="bg-terminal-bg p-3 rounded border border-terminal-bull/30 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-terminal-muted text-2xs uppercase tracking-wider">Active Account:</span>
                <span className="font-bold text-terminal-text">{account.login} ({account.server})</span>
              </div>
              <div className="grid grid-cols-2 gap-2 pt-1 border-t border-terminal-border/60">
                <div>
                  <span className="text-3xs text-terminal-muted block">Balance</span>
                  <span className="text-sm font-bold text-terminal-bull">
                    {formatCurrency(account.balance)}
                  </span>
                </div>
                <div>
                  <span className="text-3xs text-terminal-muted block">Equity</span>
                  <span className="text-sm font-bold text-terminal-text">
                    {formatCurrency(account.equity)}
                  </span>
                </div>
                <div>
                  <span className="text-3xs text-terminal-muted block">Broker Leverage</span>
                  <span className="text-xs font-bold text-terminal-cyan">
                    1:{account.leverage}
                  </span>
                </div>
                <div>
                  <span className="text-3xs text-terminal-muted block">Free Margin</span>
                  <span className="text-xs font-bold text-terminal-text">
                    {formatCurrency(account.free_margin)}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Form Inputs */}
          <div className="space-y-3">
            <div>
              <label className="text-2xs text-terminal-muted uppercase tracking-wider block mb-1">
                Exness MT5 Server Name
              </label>
              <select
                value={server}
                onChange={(e) => setServer(e.target.value)}
                className="w-full bg-terminal-bg border border-terminal-border rounded px-2.5 py-1.5 text-terminal-text focus:outline-none focus:border-terminal-cyan"
              >
                <option value="Exness-MT5Trial17">Exness-MT5Trial17 (Demo)</option>
                <option value="Exness-MT5Trial">Exness-MT5Trial (Demo)</option>
                <option value="Exness-MT5Trial2">Exness-MT5Trial2 (Demo)</option>
                <option value="Exness-MT5Real">Exness-MT5Real (Live)</option>
                <option value="Exness-MT5Real2">Exness-MT5Real2 (Live)</option>
                <option value="Exness-MT5Real3">Exness-MT5Real3 (Live)</option>
              </select>
            </div>

            <div>
              <label className="text-2xs text-terminal-muted uppercase tracking-wider block mb-1">
                Account Number (Login)
              </label>
              <div className="relative">
                <User className="w-3.5 h-3.5 absolute left-2.5 top-2 text-terminal-muted" />
                <input
                  type="text"
                  value={login}
                  onChange={(e) => setLogin(e.target.value)}
                  placeholder="e.g. 463894594"
                  required
                  className="w-full bg-terminal-bg border border-terminal-border rounded pl-8 pr-2.5 py-1.5 text-terminal-text focus:outline-none focus:border-terminal-cyan font-bold"
                />
              </div>
            </div>

            <div>
              <label className="text-2xs text-terminal-muted uppercase tracking-wider block mb-1">
                Trading Password
              </label>
              <div className="relative">
                <Key className="w-3.5 h-3.5 absolute left-2.5 top-2 text-terminal-muted" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Trading Password"
                  required
                  className="w-full bg-terminal-bg border border-terminal-border rounded pl-8 pr-2.5 py-1.5 text-terminal-text focus:outline-none focus:border-terminal-cyan"
                />
              </div>
            </div>
          </div>

          {statusMsg && (
            <div className="p-2 rounded bg-terminal-surface border border-terminal-border text-2xs text-terminal-cyan flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
              <span>{statusMsg}</span>
            </div>
          )}

          {/* Footer Buttons */}
          <div className="pt-2 border-t border-terminal-border flex items-center justify-between gap-3">
            <button
              type="button"
              onClick={() => setIsConnectModalOpen(false)}
              className="px-3 py-1.5 bg-terminal-surface hover:bg-terminal-elevated text-terminal-muted rounded transition-colors text-2xs uppercase tracking-wider"
            >
              Close
            </button>

            <button
              type="submit"
              disabled={isLoading}
              className="flex-1 py-1.5 bg-terminal-bull hover:bg-emerald-600 disabled:opacity-50 text-black font-bold text-xs rounded transition-colors uppercase tracking-wider flex items-center justify-center gap-1.5 shadow-bull"
            >
              {isLoading ? (
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <ShieldCheck className="w-3.5 h-3.5" />
              )}
              {isLoading ? 'Connecting MT5...' : isConnected ? 'Re-Sync Exness MT5' : 'Connect Exness MT5'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
