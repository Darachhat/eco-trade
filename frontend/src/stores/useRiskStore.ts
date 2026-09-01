import { create } from 'zustand';
import { RiskStatus } from '../types/risk';
import { INITIAL_RISK } from '../lib/mock/quantData';

interface RiskState {
  riskStatus: RiskStatus;
  isKillSwitchModalOpen: boolean;
  setIsKillSwitchModalOpen: (open: boolean) => void;
  activateKillSwitch: (reason: string) => void;
  deactivateKillSwitch: () => void;
  togglePauseTrading: () => void;
  updateEquity: (delta: number) => void;
}

export const useRiskStore = create<RiskState>((set) => ({
  riskStatus: { ...INITIAL_RISK },
  isKillSwitchModalOpen: false,

  setIsKillSwitchModalOpen: (open) => set({ isKillSwitchModalOpen: open }),

  activateKillSwitch: (reason) => {
    set((state) => ({
      riskStatus: {
        ...state.riskStatus,
        killSwitchActive: true,
        killSwitchReason: reason,
        tradingPaused: true,
      },
    }));
  },

  deactivateKillSwitch: () => {
    set((state) => ({
      riskStatus: {
        ...state.riskStatus,
        killSwitchActive: false,
        killSwitchReason: undefined,
        tradingPaused: false,
      },
    }));
  },

  togglePauseTrading: () => {
    set((state) => ({
      riskStatus: {
        ...state.riskStatus,
        tradingPaused: !state.riskStatus.tradingPaused,
      },
    }));
  },

  updateEquity: (delta) => {
    set((state) => {
      const newEquity = state.riskStatus.accountEquity + delta;
      return {
        riskStatus: {
          ...state.riskStatus,
          accountEquity: Number(newEquity.toFixed(2)),
        },
      };
    });
  },
}));
