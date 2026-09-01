import { create } from 'zustand';

export type TradingMode = 'paper' | 'live';
export type Environment = 'testnet' | 'mainnet';

interface TradingModeState {
  mode: TradingMode;
  environment: Environment;
  liveExecutionEnabled: boolean;
  isLiveWarningModalOpen: boolean;
  setMode: (mode: TradingMode) => void;
  setEnvironment: (env: Environment) => void;
  setLiveExecutionEnabled: (enabled: boolean) => void;
  setIsLiveWarningModalOpen: (open: boolean) => void;
}

export const useTradingModeStore = create<TradingModeState>((set) => ({
  mode: 'paper',
  environment: 'testnet',
  liveExecutionEnabled: false,
  isLiveWarningModalOpen: false,
  setMode: (mode) => {
    if (mode === 'live') {
      set({ isLiveWarningModalOpen: true });
    } else {
      set({ mode: 'paper', liveExecutionEnabled: false });
    }
  },
  setEnvironment: (environment) => set({ environment }),
  setLiveExecutionEnabled: (enabled) => set({ liveExecutionEnabled: enabled, mode: enabled ? 'live' : 'paper' }),
  setIsLiveWarningModalOpen: (open) => set({ isLiveWarningModalOpen: open }),
}));
