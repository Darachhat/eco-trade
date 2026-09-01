import { create } from 'zustand';
import {
  Candle,
  IndicatorToggles,
  OrderBook,
  SymbolName,
  Ticker,
  Timeframe,
  CVDPoint,
  OpenInterestPoint,
  FundingRatePoint,
} from '../types/market';
import {
  INITIAL_TICKERS,
} from '../lib/mock/quantData';
import { BybitLiveClient, computeIndicatorsOnCandles } from '../lib/api/bybitLive';
import { evaluateRealSignal } from '../lib/quant/engine';
import { useSignalStore } from './useSignalStore';

interface MarketState {
  activeSymbol: SymbolName;
  activeTimeframe: Timeframe;
  tickers: Record<SymbolName, Ticker>;
  candles: Candle[];
  orderBook: OrderBook;
  indicators: IndicatorToggles;
  cvdHistory: CVDPoint[];
  openInterestHistory: OpenInterestPoint[];
  fundingRates: Record<SymbolName, FundingRatePoint>;
  isLoadingRealData: boolean;
  setActiveSymbol: (symbol: SymbolName) => Promise<void>;
  setActiveTimeframe: (timeframe: Timeframe) => Promise<void>;
  toggleIndicator: (indicator: keyof IndicatorToggles) => void;
  updateLiveTick: (symbol: SymbolName, price: number, timestamp?: string) => void;
  updateLiveOrderBook: (orderBook: OrderBook) => void;
  updateLiveCandle: (candle: Candle) => void;
  fetchRealMarketData: (symbol?: SymbolName, timeframe?: Timeframe) => Promise<void>;
  refreshCandles: () => Promise<void>;
}

const defaultIndicators: IndicatorToggles = {
  ema8: true,
  ema21: true,
  ema55: true,
  ema200: false,
  bollinger: false,
  supertrend: true,
  rsi: true,
  macd: false,
  adx: false,
};

const initialSymbol: SymbolName = 'BTCUSDT';
const initialTimeframe: Timeframe = '15m';

export const useMarketStore = create<MarketState>((set, get) => ({
  activeSymbol: initialSymbol,
  activeTimeframe: initialTimeframe,
  tickers: { ...INITIAL_TICKERS },
  candles: [],
  orderBook: {
    symbol: initialSymbol,
    timestamp: new Date().toISOString(),
    bids: [],
    asks: [],
    spread: 0,
    spreadBps: 0,
    midPrice: 0,
    imbalance: 0,
  },
  indicators: defaultIndicators,
  isLoadingRealData: false,
  cvdHistory: Array.from({ length: 30 }, (_, i) => ({
    time: `${i * 2}m ago`,
    cvd: 450000 + Math.sin(i / 3) * 800000 + i * 25000,
    volumeDelta: 35000 + (Math.random() - 0.4) * 80000,
    buyVol: 120000 + Math.random() * 80000,
    sellVol: 85000 + Math.random() * 70000,
  })),
  openInterestHistory: Array.from({ length: 24 }, (_, i) => ({
    time: `${24 - i}h ago`,
    openInterest: 53330 + i * 42,
    oiChangePct: 1.25,
  })),
  fundingRates: {
    BTCUSDT: { symbol: 'BTCUSDT', rate: 0.00010, predictedRate: 0.00010, nextFundingTime: '04:00:00', annualizedRate: 10.95 },
    XAUUSDT: { symbol: 'XAUUSDT', rate: 0.00020, predictedRate: 0.00020, nextFundingTime: '04:00:00', annualizedRate: 21.90 },
  },

  fetchRealMarketData: async (symbolParam, timeframeParam) => {
    const sym = symbolParam || get().activeSymbol;
    const tf = timeframeParam || get().activeTimeframe;

    set({ isLoadingRealData: true });

    try {
      // 1. Fetch real tickers from Bybit for BTC and XAU
      const liveTickers = await BybitLiveClient.fetchAllTickers();
      if (liveTickers && Object.keys(liveTickers).length > 0) {
        set((state) => ({ tickers: { ...state.tickers, ...liveTickers } }));
      }

      // 2. Fetch real klines from Bybit
      const liveCandles = await BybitLiveClient.fetchKlines(sym, tf, 200);
      if (liveCandles && liveCandles.length > 0) {
        set({ candles: liveCandles });

        // Evaluate live real signals from actual candle indicators and real prices
        const curTicker = (liveTickers && liveTickers[sym]) || get().tickers[sym];
        const evaluatedSignal = evaluateRealSignal(sym, liveCandles, curTicker, tf);

        // Also evaluate other symbol if missing
        const otherSym: SymbolName = sym === 'BTCUSDT' ? 'XAUUSDT' : 'BTCUSDT';
        const otherTicker = (liveTickers && liveTickers[otherSym]) || get().tickers[otherSym];
        const existingSignals = useSignalStore.getState().signals;

        if (existingSignals.length === 0) {
          const otherSignal = evaluateRealSignal(otherSym, liveCandles, otherTicker, tf);
          useSignalStore.getState().setSignals([evaluatedSignal, otherSignal]);
        } else {
          useSignalStore.getState().setSignals([
            evaluatedSignal,
            ...existingSignals.filter((s) => s.symbol !== sym),
          ]);
        }
      }

      // 3. Fetch real orderbook from Bybit
      const liveOrderBook = await BybitLiveClient.fetchOrderBook(sym, 25);
      if (liveOrderBook) {
        set({ orderBook: liveOrderBook });
      }

      // 4. Fetch real funding & open interest
      const fundingOI = await BybitLiveClient.fetchFundingAndOI(sym);
      if (fundingOI) {
        set((state) => ({
          fundingRates: {
            ...state.fundingRates,
            [sym]: fundingOI.fundingRatePoint,
          },
          openInterestHistory: [
            ...state.openInterestHistory.slice(1),
            fundingOI.openInterestPoint,
          ],
        }));
      }
    } catch (err) {
      console.warn('[useMarketStore] Failed to load full real data:', err);
    } finally {
      set({ isLoadingRealData: false });
    }
  },

  setActiveSymbol: async (symbol) => {
    set({ activeSymbol: symbol });
    const { activeTimeframe } = get();
    await get().fetchRealMarketData(symbol, activeTimeframe);
  },

  setActiveTimeframe: async (timeframe) => {
    set({ activeTimeframe: timeframe });
    const { activeSymbol } = get();
    await get().fetchRealMarketData(activeSymbol, timeframe);
  },

  toggleIndicator: (indicator) => {
    set((state) => ({
      indicators: {
        ...state.indicators,
        [indicator]: !state.indicators[indicator],
      },
    }));
  },

  updateLiveTick: (symbol, price, timestamp = new Date().toISOString()) => {
    set((state) => {
      const curTicker = state.tickers[symbol];
      if (!curTicker) return state;

      const change24hAmount = curTicker.price > 0 ? price - (curTicker.price - curTicker.change24hAmount) : 0;
      const change24h = curTicker.price > 0 ? (change24hAmount / (price - change24hAmount)) * 100 : 0;
      const high24h = Math.max(curTicker.high24h || price, price);
      const low24h = curTicker.low24h > 0 ? Math.min(curTicker.low24h, price) : price;

      const updatedTicker: Ticker = {
        ...curTicker,
        price,
        change24h: Number(change24h.toFixed(2)),
        change24hAmount: Number(change24hAmount.toFixed(2)),
        high24h,
        low24h,
        timestamp,
      };

      const newTickers = { ...state.tickers, [symbol]: updatedTicker };

      // Update current candle if active symbol
      let newCandles = state.candles;
      if (symbol === state.activeSymbol && newCandles.length > 0) {
        const lastIdx = newCandles.length - 1;
        const lastCandle = { ...newCandles[lastIdx] };
        lastCandle.close = price;
        lastCandle.high = Math.max(lastCandle.high, price);
        lastCandle.low = Math.min(lastCandle.low, price);
        newCandles = [...newCandles.slice(0, lastIdx), lastCandle];
        newCandles = computeIndicatorsOnCandles(newCandles);
      }

      return {
        tickers: newTickers,
        candles: newCandles,
      };
    });
  },

  updateLiveOrderBook: (orderBook) => {
    set({ orderBook });
  },

  updateLiveCandle: (newCandle) => {
    set((state) => {
      const candles = [...state.candles];
      const lastIdx = candles.length - 1;
      if (lastIdx >= 0 && candles[lastIdx].time === newCandle.time) {
        candles[lastIdx] = newCandle;
      } else {
        candles.push(newCandle);
        if (candles.length > 250) candles.shift();
      }
      return { candles: computeIndicatorsOnCandles(candles) };
    });
  },

  refreshCandles: async () => {
    const { activeSymbol, activeTimeframe } = get();
    await get().fetchRealMarketData(activeSymbol, activeTimeframe);
  },
}));
