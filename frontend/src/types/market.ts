export type SymbolName = 'BTCUSDT' | 'XAUUSDT';

export type Timeframe = '1m' | '5m' | '15m' | '1h' | '4h' | '1D';

export interface Candle {
  time: number; // Unix timestamp in seconds
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  ema8?: number;
  ema21?: number;
  ema55?: number;
  ema200?: number;
  bbUpper?: number;
  bbMiddle?: number;
  bbLower?: number;
  supertrend?: number;
  supertrendDirection?: 'bull' | 'bear';
  rsi?: number;
  macd?: number;
  macdSignal?: number;
  macdHist?: number;
  adx?: number;
}

export interface Ticker {
  symbol: SymbolName;
  price: number;
  change24h: number;
  change24hAmount: number;
  high24h: number;
  low24h: number;
  volume24hUsd: number;
  turnover24h: number;
  timestamp: string;
}

export interface OrderBookLevel {
  price: number;
  size: number;
  total: number;
  percent: number; // 0 to 100% of maximum cumulative volume in view
}

export interface OrderBook {
  symbol: SymbolName;
  timestamp: string;
  bids: OrderBookLevel[];
  asks: OrderBookLevel[];
  spread: number;
  spreadBps: number;
  midPrice: number;
  imbalance: number; // between -1 (extreme ask) and +1 (extreme bid)
}

export interface CVDPoint {
  time: string;
  cvd: number;
  volumeDelta: number;
  buyVol: number;
  sellVol: number;
}

export interface OpenInterestPoint {
  time: string;
  openInterest: number;
  oiChangePct: number;
}

export interface FundingRatePoint {
  symbol: SymbolName;
  rate: number;
  predictedRate: number;
  nextFundingTime: string;
  annualizedRate: number;
}

export interface IndicatorToggles {
  ema8: boolean;
  ema21: boolean;
  ema55: boolean;
  ema200: boolean;
  bollinger: boolean;
  supertrend: boolean;
  rsi: boolean;
  macd: boolean;
  adx: boolean;
}
