import { create } from 'zustand';
import { BacktestConfig, BacktestResult } from '../types/backtest';
import { BybitLiveClient } from '../lib/api/bybitLive';
import { runQuantBacktestOnRealCandles } from '../lib/quant/engine';

interface BacktestState {
  config: BacktestConfig;
  isRunning: boolean;
  progress: number;
  result: BacktestResult | null;
  history: BacktestResult[];
  setConfig: (config: Partial<BacktestConfig>) => void;
  runBacktest: () => Promise<void>;
  loadHistoryResult: (id: string) => void;
}

const initialConfig: BacktestConfig = {
  symbol: 'BTCUSDT',
  timeframe: '15m',
  strategy: 'AI Ensemble',
  startDate: '2025-01-01',
  endDate: new Date().toISOString().split('T')[0],
  initialCapital: 10000,
  riskPerTrade: 0.01,
  feePct: 0.055,
  slippagePct: 0.02,
  confidenceThreshold: 0.75,
  minAgreement: 0.70,
};

const initialResult = runQuantBacktestOnRealCandles([], initialConfig);

export const useBacktestStore = create<BacktestState>((set, get) => ({
  config: initialConfig,
  isRunning: false,
  progress: 100,
  result: initialResult,
  history: [initialResult],

  setConfig: (newConfig) =>
    set((state) => ({ config: { ...state.config, ...newConfig } })),

  runBacktest: async () => {
    set({ isRunning: true, progress: 0 });
    const currentConfig = get().config;

    try {
      // 1. Fetch real historical Bybit klines for the selected symbol and timeframe (200 candles)
      set({ progress: 30 });
      const candles = await BybitLiveClient.fetchKlines(currentConfig.symbol, currentConfig.timeframe, 200);

      set({ progress: 65 });
      await new Promise((res) => setTimeout(res, 200));

      // 2. Execute quantitative simulation directly on real candles
      const newResult = runQuantBacktestOnRealCandles(candles, currentConfig);
      newResult.id = `bt-${Date.now()}`;
      newResult.executedAt = new Date().toISOString();

      set({ progress: 100 });

      set((state) => ({
        isRunning: false,
        progress: 100,
        result: newResult,
        history: [newResult, ...state.history],
      }));
    } catch {
      // Fallback with empty candle run
      const fallbackResult = runQuantBacktestOnRealCandles([], currentConfig);
      set({
        isRunning: false,
        progress: 100,
        result: fallbackResult,
      });
    }
  },

  loadHistoryResult: (id) => {
    const found = get().history.find((h) => h.id === id);
    if (found) {
      set({ result: found, config: found.config });
    }
  },
}));
