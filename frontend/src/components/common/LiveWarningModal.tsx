import React, { useState } from 'react';
import { AlertTriangle, ShieldAlert, X } from 'lucide-react';
import { useTradingModeStore } from '../../stores/useTradingModeStore';

export const LiveWarningModal: React.FC = () => {
  const isLiveWarningModalOpen = useTradingModeStore((s) => s.isLiveWarningModalOpen);
  const setIsLiveWarningModalOpen = useTradingModeStore((s) => s.setIsLiveWarningModalOpen);
  const setLiveExecutionEnabled = useTradingModeStore((s) => s.setLiveExecutionEnabled);

  const [confirmedRisk, setConfirmedRisk] = useState(false);
  const [typedConfirmation, setTypedConfirmation] = useState('');

  if (!isLiveWarningModalOpen) return null;

  const handleEnableLive = () => {
    if (confirmedRisk && typedConfirmation.trim().toUpperCase() === 'ENABLE LIVE TRADING') {
      setLiveExecutionEnabled(true);
      setIsLiveWarningModalOpen(false);
      setConfirmedRisk(false);
      setTypedConfirmation('');
    }
  };

  const handleCancel = () => {
    setIsLiveWarningModalOpen(false);
    setConfirmedRisk(false);
    setTypedConfirmation('');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="bg-terminal-panel border border-terminal-bear/60 max-w-lg w-full rounded-sm shadow-2xl p-5 text-terminal-text">
        <div className="flex items-center justify-between border-b border-terminal-border pb-3 mb-4">
          <div className="flex items-center gap-2 text-terminal-bear font-bold uppercase tracking-wider text-sm">
            <ShieldAlert className="w-5 h-5" />
            <span>CRITICAL SAFETY: Enable Live Execution</span>
          </div>
          <button
            onClick={handleCancel}
            className="text-terminal-muted hover:text-terminal-text transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="space-y-3 text-xs leading-relaxed text-terminal-muted">
          <div className="p-3 bg-terminal-bearDim/20 border border-terminal-bear/40 rounded text-terminal-bear flex gap-2.5 items-start">
            <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
            <div>
              <div className="font-bold text-xs uppercase mb-0.5">Real Capital at Risk</div>
              You are about to switch EcoTrade from Paper Simulation to <strong>LIVE REAL-CAPITAL EXECUTION</strong> on Bybit. Live orders will be sent to the exchange order book.
            </div>
          </div>

          <p>
            Please verify your risk limits, position sizing, and stop-loss parameters before proceeding. The platform requires explicit authorization.
          </p>

          <div className="space-y-2 pt-2 border-t border-terminal-border/80">
            <label className="flex items-start gap-2.5 cursor-pointer text-terminal-text select-none">
              <input
                type="checkbox"
                checked={confirmedRisk}
                onChange={(e) => setConfirmedRisk(e.target.checked)}
                className="mt-0.5 rounded bg-terminal-surface border-terminal-border text-terminal-bear focus:ring-0"
              />
              <span>
                I understand that live orders will execute with real funds and that algorithmic trading involves substantial financial risk.
              </span>
            </label>
          </div>

          <div className="pt-2">
            <label className="block text-2xs uppercase tracking-wider text-terminal-muted mb-1">
              Type <span className="text-terminal-bear font-mono font-bold">ENABLE LIVE TRADING</span> to confirm:
            </label>
            <input
              type="text"
              value={typedConfirmation}
              onChange={(e) => setTypedConfirmation(e.target.value)}
              placeholder="ENABLE LIVE TRADING"
              className="w-full bg-terminal-bg border border-terminal-border px-3 py-1.5 font-mono text-xs text-terminal-text rounded focus:outline-none focus:border-terminal-bear"
            />
          </div>
        </div>

        <div className="flex items-center justify-end gap-2.5 mt-5 pt-3 border-t border-terminal-border">
          <button
            onClick={handleCancel}
            className="px-3 py-1.5 bg-terminal-surface hover:bg-terminal-elevated text-terminal-text text-xs rounded transition-colors"
          >
            Cancel (Keep Paper)
          </button>
          <button
            onClick={handleEnableLive}
            disabled={!confirmedRisk || typedConfirmation.trim().toUpperCase() !== 'ENABLE LIVE TRADING'}
            className="px-4 py-1.5 bg-terminal-bear hover:bg-terminal-bear/80 disabled:opacity-40 disabled:cursor-not-allowed text-white font-bold text-xs rounded transition-colors uppercase tracking-wider flex items-center gap-1.5"
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            Switch to Live Execution
          </button>
        </div>
      </div>
    </div>
  );
};
