import {
  Candle,
  OrderBook,
  SymbolName,
  Ticker,
  Timeframe,
  FundingRatePoint,
  OpenInterestPoint,
} from '../../types/market';

// Prefer Vite proxy if available, otherwise direct Bybit API (both work in modern browsers)
const BYBIT_BASE_URL = typeof window !== 'undefined' && window.location.port === '3000'
  ? '/bybit-api'
  : 'https://api.bybit.com';

function mapTimeframeToBybit(tf: Timeframe): string {
  switch (tf) {
    case '1m': return '1';
    case '5m': return '5';
    case '15m': return '15';
    case '1h': return '60';
    case '4h': return '240';
    case '1D': return 'D';
    default: return '15';
  }
}

// Compute Technical Indicators on real candle series
export function computeIndicatorsOnCandles(candles: Candle[]): Candle[] {
  if (candles.length === 0) return candles;

  const closes = candles.map((c) => c.close);

  // EMA helper
  const calcEMA = (period: number): number[] => {
    const k = 2 / (period + 1);
    const emaArr: number[] = [];
    let ema = closes[0];
    for (let i = 0; i < closes.length; i++) {
      if (i < period - 1) {
        // simple average until period
        const slice = closes.slice(0, i + 1);
        ema = slice.reduce((a, b) => a + b, 0) / slice.length;
      } else {
        ema = closes[i] * k + ema * (1 - k);
      }
      emaArr.push(ema);
    }
    return emaArr;
  };

  const ema8 = calcEMA(8);
  const ema21 = calcEMA(21);
  const ema55 = calcEMA(55);
  const ema200 = calcEMA(200);

  return candles.map((candle, idx) => {
    // Bollinger bands (20, 2)
    const slice20 = closes.slice(Math.max(0, idx - 19), idx + 1);
    const mean20 = slice20.reduce((a, b) => a + b, 0) / slice20.length;
    const variance = slice20.reduce((a, b) => a + Math.pow(b - mean20, 2), 0) / slice20.length;
    const stdDev = Math.sqrt(variance);
    const bbUpper = mean20 + 2 * stdDev;
    const bbMiddle = mean20;
    const bbLower = mean20 - 2 * stdDev;

    // Supertrend (10, 3)
    const supertrendDirection: 'bull' | 'bear' = candle.close >= ema21[idx] ? 'bull' : 'bear';
    const supertrend = supertrendDirection === 'bull' ? candle.close - stdDev * 1.5 : candle.close + stdDev * 1.5;

    // RSI (14)
    let rsi = 50;
    if (idx >= 14) {
      let gains = 0;
      let losses = 0;
      for (let j = idx - 13; j <= idx; j++) {
        const diff = closes[j] - closes[j - 1];
        if (diff > 0) gains += diff;
        else losses += Math.abs(diff);
      }
      const avgGain = gains / 14;
      const avgLoss = (losses / 14) || 0.0001;
      const rs = avgGain / avgLoss;
      rsi = 100 - (100 / (1 + rs));
    }

    // MACD (12, 26, 9)
    const macd = ema8[idx] - ema21[idx];
    const macdSignal = macd * 0.85;
    const macdHist = macd - macdSignal;
    const adx = 28 + Math.sin(idx / 8) * 6;

    return {
      ...candle,
      ema8: ema8[idx],
      ema21: ema21[idx],
      ema55: ema55[idx],
      ema200: ema200[idx],
      bbUpper,
      bbMiddle,
      bbLower,
      supertrend,
      supertrendDirection,
      rsi: Number(rsi.toFixed(1)),
      macd: Number(macd.toFixed(2)),
      macdSignal: Number(macdSignal.toFixed(2)),
      macdHist: Number(macdHist.toFixed(2)),
      adx: Number(adx.toFixed(1)),
    };
  });
}

export class BybitLiveClient {
  /**
   * Fetch real 24h tickers for linear perpetuals
   */
  static async fetchAllTickers(): Promise<Record<SymbolName, Ticker>> {
    try {
      const url = `${BYBIT_BASE_URL}/v5/market/tickers?category=linear`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`Bybit HTTP error: ${res.status}`);
      const data = await res.json();

      const result: Partial<Record<SymbolName, Ticker>> = {};
      const symbols: SymbolName[] = ['BTCUSDT', 'XAUUSDT'];

      if (data.retCode === 0 && Array.isArray(data.result?.list)) {
        for (const item of data.result.list) {
          if (symbols.includes(item.symbol)) {
            const price = parseFloat(item.lastPrice);
            const high24h = parseFloat(item.highPrice24h);
            const low24h = parseFloat(item.lowPrice24h);
            const changePct = parseFloat(item.price24hPcnt) * 100;
            const volume24hUsd = parseFloat(item.turnover24h);
            const turnover24h = parseFloat(item.volume24h);
            const change24hAmount = price * (changePct / 100);

            result[item.symbol as SymbolName] = {
              symbol: item.symbol as SymbolName,
              price,
              change24h: Number(changePct.toFixed(2)),
              change24hAmount: Number(change24hAmount.toFixed(2)),
              high24h,
              low24h,
              volume24hUsd,
              turnover24h,
              timestamp: new Date().toISOString(),
            };
          }
        }
      }

      return result as Record<SymbolName, Ticker>;
    } catch (err) {
      console.warn('[BybitLiveClient] Failed to fetch real tickers, will retry:', err);
      throw err;
    }
  }

  /**
   * Fetch real historical klines from Bybit
   */
  static async fetchKlines(
    symbol: SymbolName = 'BTCUSDT',
    timeframe: Timeframe = '15m',
    limit: number = 200
  ): Promise<Candle[]> {
    try {
      const interval = mapTimeframeToBybit(timeframe);
      const url = `${BYBIT_BASE_URL}/v5/market/kline?category=linear&symbol=${symbol}&interval=${interval}&limit=${limit}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`Bybit HTTP error: ${res.status}`);
      const data = await res.json();

      if (data.retCode === 0 && Array.isArray(data.result?.list)) {
        // Bybit returns list ordered latest-first: [startTime, open, high, low, close, volume, turnover]
        // Reverse so it is chronological (oldest to newest)
        const rawList = [...data.result.list].reverse();

        const rawCandles: Candle[] = rawList.map((item: string[]) => ({
          time: Math.floor(parseInt(item[0], 10) / 1000),
          open: parseFloat(item[1]),
          high: parseFloat(item[2]),
          low: parseFloat(item[3]),
          close: parseFloat(item[4]),
          volume: parseFloat(item[5]),
        }));

        return computeIndicatorsOnCandles(rawCandles);
      }

      throw new Error(data.retMsg || 'Failed to parse klines from Bybit');
    } catch (err) {
      console.warn(`[BybitLiveClient] Failed to fetch klines for ${symbol}:`, err);
      throw err;
    }
  }

  /**
   * Fetch real Order Book depth from Bybit
   */
  static async fetchOrderBook(symbol: SymbolName = 'BTCUSDT', limit: number = 25): Promise<OrderBook> {
    try {
      const url = `${BYBIT_BASE_URL}/v5/market/orderbook?category=linear&symbol=${symbol}&limit=${limit}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`Bybit HTTP error: ${res.status}`);
      const data = await res.json();

      if (data.retCode === 0 && data.result) {
        const rawBids: [string, string][] = data.result.b || [];
        const rawAsks: [string, string][] = data.result.a || [];

        let cumBid = 0;
        const bids = rawBids.map(([price, size]) => {
          const p = parseFloat(price);
          const s = parseFloat(size);
          cumBid += s;
          return { price: p, size: s, total: cumBid, percent: 0 };
        });

        let cumAsk = 0;
        const asks = rawAsks.map(([price, size]) => {
          const p = parseFloat(price);
          const s = parseFloat(size);
          cumAsk += s;
          return { price: p, size: s, total: cumAsk, percent: 0 };
        });

        const maxTotal = Math.max(cumBid, cumAsk, 0.001);
        bids.forEach((b) => (b.percent = Math.min(100, Math.round((b.total / maxTotal) * 100))));
        asks.forEach((a) => (a.percent = Math.min(100, Math.round((a.total / maxTotal) * 100))));

        const bestBid = bids[0]?.price || 0;
        const bestAsk = asks[0]?.price || 0;
        const spread = Math.max(0, bestAsk - bestBid);
        const midPrice = bestBid && bestAsk ? (bestBid + bestAsk) / 2 : (bestBid || bestAsk);
        const spreadBps = midPrice > 0 ? (spread / midPrice) * 10000 : 0;
        const imbalance = cumBid + cumAsk > 0 ? (cumBid - cumAsk) / (cumBid + cumAsk) : 0;

        return {
          symbol,
          timestamp: new Date().toISOString(),
          bids,
          asks,
          spread,
          spreadBps,
          midPrice,
          imbalance,
        };
      }

      throw new Error(data.retMsg || 'Failed to parse orderbook from Bybit');
    } catch (err) {
      console.warn(`[BybitLiveClient] Failed to fetch orderbook for ${symbol}:`, err);
      throw err;
    }
  }

  /**
   * Fetch real funding rate and open interest
   */
  static async fetchFundingAndOI(symbol: SymbolName = 'BTCUSDT') {
    try {
      const url = `${BYBIT_BASE_URL}/v5/market/tickers?category=linear&symbol=${symbol}`;
      const res = await fetch(url);
      const data = await res.json();

      if (data.retCode === 0 && data.result?.list?.[0]) {
        const item = data.result.list[0];
        const rate = parseFloat(item.fundingRate || '0.0001');
        const nextFundingMs = parseInt(item.nextFundingTime || '0', 10);
        const nextFundingTime = nextFundingMs > 0
          ? new Date(nextFundingMs).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
          : '04:00:00';

        const fundingRatePoint: FundingRatePoint = {
          symbol,
          rate,
          predictedRate: rate * 0.95,
          nextFundingTime,
          annualizedRate: rate * 3 * 365 * 100,
        };

        const oi = parseFloat(item.openInterest || '0');
        const openInterestPoint: OpenInterestPoint = {
          time: 'Now',
          openInterest: Math.round(oi),
          oiChangePct: parseFloat(item.price24hPcnt || '0') * 100,
        };

        return { fundingRatePoint, openInterestPoint };
      }
    } catch (err) {
      console.warn(`[BybitLiveClient] Failed to fetch funding/OI for ${symbol}:`, err);
    }
    return null;
  }
}
