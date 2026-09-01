import { create } from 'zustand';
import { Signal, SignalDirection, SignalStatus } from '../types/signal';
import { SymbolName, Ticker } from '../types/market';
import { INITIAL_SIGNALS } from '../lib/mock/quantData';

interface SignalFilter {
  symbol?: SymbolName | 'ALL';
  direction?: SignalDirection | 'ALL';
  status?: SignalStatus | 'ALL';
}

export function generateSignalTargets(
  symbol: SymbolName,
  currentPrice: number,
  direction: SignalDirection = 'LONG'
) {
  const isLong = direction === 'LONG';
  const volatility = symbol === 'BTCUSDT' ? 0.008 : 0.005;
  const spreadMargin = currentPrice * (volatility * 0.2);

  const entryZoneMin = isLong
    ? Number((currentPrice - spreadMargin).toFixed(2))
    : Number((currentPrice).toFixed(2));

  const entryZoneMax = isLong
    ? Number((currentPrice + spreadMargin * 0.5).toFixed(2))
    : Number((currentPrice + spreadMargin).toFixed(2));

  const slDist = currentPrice * (volatility * 0.9);
  const stopLoss = isLong
    ? Number((currentPrice - slDist).toFixed(2))
    : Number((currentPrice + slDist).toFixed(2));

  const tp1 = isLong
    ? Number((currentPrice + slDist * 1.5).toFixed(2))
    : Number((currentPrice - slDist * 1.5).toFixed(2));

  const tp2 = isLong
    ? Number((currentPrice + slDist * 2.5).toFixed(2))
    : Number((currentPrice - slDist * 2.5).toFixed(2));

  const tp3 = isLong
    ? Number((currentPrice + slDist * 3.8).toFixed(2))
    : Number((currentPrice - slDist * 3.8).toFixed(2));

  const riskRewardRatio = Number(((Math.abs(tp2 - currentPrice)) / (slDist || 1)).toFixed(2));

  return {
    entryZoneMin,
    entryZoneMax,
    stopLoss,
    tp1,
    tp2,
    tp3,
    riskRewardRatio,
  };
}

interface SignalState {
  signals: Signal[];
  selectedSignalId: string | null;
  filter: SignalFilter;
  isExplainModalOpen: boolean;
  setSelectedSignalId: (id: string | null) => void;
  setIsExplainModalOpen: (open: boolean) => void;
  setFilter: (filter: Partial<SignalFilter>) => void;
  addSignal: (signal: Signal) => void;
  setSignals: (signals: Signal[]) => void;
  updateSignalStatus: (id: string, status: SignalStatus) => void;
  syncSignalsWithLivePrices: (tickers: Record<SymbolName, Ticker>) => void;
}

export const useSignalStore = create<SignalState>((set, get) => ({
  signals: [...INITIAL_SIGNALS],
  selectedSignalId: null,
  filter: {
    symbol: 'ALL',
    direction: 'ALL',
    status: 'ALL',
  },
  isExplainModalOpen: false,

  setSelectedSignalId: (id) => set({ selectedSignalId: id }),
  setIsExplainModalOpen: (open) => set({ isExplainModalOpen: open }),
  setFilter: (newFilter) =>
    set((state) => ({ filter: { ...state.filter, ...newFilter } })),

  addSignal: (signal) =>
    set((state) => ({
      signals: [signal, ...state.signals],
      selectedSignalId: state.selectedSignalId || signal.id,
    })),

  setSignals: (signals) =>
    set({
      signals,
      selectedSignalId: signals[0]?.id || null,
    }),

  updateSignalStatus: (id, status) =>
    set((state) => ({
      signals: state.signals.map((s) => (s.id === id ? { ...s, status } : s)),
    })),

  syncSignalsWithLivePrices: (tickers) => {
    set((state) => ({
      signals: state.signals.map((sig) => {
        const liveTicker = tickers[sig.symbol];
        if (!liveTicker || !liveTicker.price) return sig;

        const currentPrice = liveTicker.price;
        // If the signal entry was far away (>3%) from current price, recalculate targets around live price
        const priceDiff = Math.abs(currentPrice - sig.currentPrice) / currentPrice;
        if (priceDiff > 0.03) {
          const targets = generateSignalTargets(sig.symbol, currentPrice, sig.direction);
          return {
            ...sig,
            currentPrice,
            entryZoneMin: targets.entryZoneMin,
            entryZoneMax: targets.entryZoneMax,
            stopLoss: targets.stopLoss,
            tp1: targets.tp1,
            tp2: targets.tp2,
            tp3: targets.tp3,
            riskRewardRatio: targets.riskRewardRatio,
          };
        }
        return {
          ...sig,
          currentPrice,
        };
      }),
    }));
  },
}));
