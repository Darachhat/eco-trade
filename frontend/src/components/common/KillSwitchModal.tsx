import React, { useState } from 'react';
import { Octagon, AlertOctagon, X } from 'lucide-react';
import { useRiskStore } from '../../stores/useRiskStore';

export const KillSwitchModal: React.FC = () => {
  const isKillSwitchModalOpen = useRiskStore((s) => s.isKillSwitchModalOpen);
  const setIsKillSwitchModalOpen = useRiskStore((s) => s.setIsKillSwitchModalOpen);
  const activateKillSwitch = useRiskStore((s) => s.activateKillSwitch);

  const [reason, setReason] = useState('Manual Emergency Operator Intervention');

  if (!isKillSwitchModalOpen) return null;

  const handleConfirmHalt = () => {
    activateKillSwitch(reason);
    setIsKillSwitchModalOpen(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-sm p-4">
      <div className="bg-terminal-panel border border-terminal-bear max-w-md w-full rounded-sm shadow-2xl p-5 text-terminal-text">
        <div className="flex items-center justify-between border-b border-terminal-border pb-3 mb-4">
          <div className="flex items-center gap-2 text-terminal-bear font-bold uppercase tracking-wider text-sm">
            <Octagon className="w-5 h-5 fill-terminal-bear/20 text-terminal-bear" />
            <span>EMERGENCY KILL SWITCH</span>
          </div>
          <button
            onClick={() => setIsKillSwitchModalOpen(false)}
            className="text-terminal-muted hover:text-terminal-text transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="space-y-3 text-xs leading-relaxed text-terminal-muted">
          <div className="p-3 bg-terminal-bearDim border border-terminal-bear/50 rounded text-terminal-bear flex gap-2.5 items-start">
            <AlertOctagon className="w-5 h-5 shrink-0 mt-0.5" />
            <div>
              <div className="font-bold uppercase text-xs">Immediate Trading Halt</div>
              Triggering the Kill Switch will immediately cancel all pending orders, freeze algorithmic execution, and pause all signal dispatchers.
            </div>
          </div>

          <div>
            <label className="block text-2xs uppercase tracking-wider text-terminal-muted mb-1 font-semibold">
              Reason for Emergency Halt:
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={2}
              className="w-full bg-terminal-bg border border-terminal-border px-2.5 py-1.5 font-mono text-xs text-terminal-text rounded focus:outline-none focus:border-terminal-bear resize-none"
            />
          </div>
        </div>

        <div className="flex items-center justify-end gap-2.5 mt-5 pt-3 border-t border-terminal-border">
          <button
            onClick={() => setIsKillSwitchModalOpen(false)}
            className="px-3 py-1.5 bg-terminal-surface hover:bg-terminal-elevated text-terminal-text text-xs rounded transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirmHalt}
            className="px-4 py-1.5 bg-terminal-bear hover:bg-red-700 text-white font-bold text-xs rounded transition-colors uppercase tracking-wider flex items-center gap-1.5 shadow-bear-glow"
          >
            <Octagon className="w-4 h-4" />
            TRIGGER KILL SWITCH NOW
          </button>
        </div>
      </div>
    </div>
  );
};
