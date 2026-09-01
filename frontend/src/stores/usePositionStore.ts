import { create } from 'zustand';
import { Position, JournalTrade } from '../types/position';
import { INITIAL_POSITIONS, INITIAL_JOURNAL } from '../lib/mock/quantData';
import { SymbolName, Ticker } from '../types/market';

interface PositionState {
  positions: Position[];
  journalTrades: JournalTrade[];
  closePosition: (id: string, exitPrice?: number) => void;
  modifyPositionSlTp: (id: string, sl: number, tp1: number) => void;
  addPosition: (pos: Position) => void;
  addJournalTrade: (trade: JournalTrade) => void;
  syncMarkPrices: (tickers: Record<SymbolName, Ticker>) => void;
}

export const usePositionStore = create<PositionState>((set) => ({
  positions: [...INITIAL_POSITIONS],
  journalTrades: [...INITIAL_JOURNAL],

  syncMarkPrices: (tickers) => {
    set((state) => ({
      positions: state.positions.map((pos) => {
        const curTicker = tickers[pos.symbol];
        if (!curTicker || !curTicker.price) return pos;

        const markPrice = curTicker.price;
        const priceDiff = pos.side === 'LONG' ? markPrice - pos.entryPrice : pos.entryPrice - markPrice;
        const unrealizedPnlUsd = Number((priceDiff * pos.size).toFixed(2));
        const unrealizedPnlPct = Number(((priceDiff / pos.entryPrice) * pos.leverage * 100).toFixed(2));

        return {
          ...pos,
          markPrice,
          unrealizedPnlUsd,
          unrealizedPnlPct,
        };
      }),
    }));
  },

  closePosition: (id, exitPrice) => {
    set((state) => {
      const posToClose = state.positions.find((p) => p.id === id);
      if (!posToClose) return state;

      const pnlUsd = posToClose.unrealizedPnlUsd;
      const pnlPct = posToClose.unrealizedPnlPct;
      const closedTrade: JournalTrade = {
        id: `j-closed-${Date.now()}`,
        symbol: posToClose.symbol,
        side: posToClose.side,
        mode: posToClose.mode,
        entryPrice: posToClose.entryPrice,
        exitPrice: exitPrice || posToClose.markPrice,
        size: posToClose.size,
        pnlUsd,
        pnlPct,
        returnR: Number((pnlUsd / (posToClose.marginUsd * 0.05)).toFixed(2)),
        openedAt: posToClose.openedAt,
        closedAt: new Date().toISOString(),
        duration: posToClose.durationFormatted,
        strategy: posToClose.strategy,
        regimeAtEntry: 'BULL_TRENDING',
        modelAgreementAtEntry: 84.5,
        exitReason: 'Manual Close',
        tags: ['Manual', 'Terminal Execution'],
        notes: 'Position closed manually from EcoTrade terminal.',
      };

      return {
        positions: state.positions.filter((p) => p.id !== id),
        journalTrades: [closedTrade, ...state.journalTrades],
      };
    });
  },

  modifyPositionSlTp: (id, sl, tp1) => {
    set((state) => ({
      positions: state.positions.map((p) =>
        p.id === id ? { ...p, stopLoss: sl, tp1 } : p
      ),
    }));
  },

  addPosition: (pos) => set((state) => ({ positions: [pos, ...state.positions] })),

  addJournalTrade: (trade) =>
    set((state) => ({ journalTrades: [trade, ...state.journalTrades] })),
}));
