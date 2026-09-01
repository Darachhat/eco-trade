import { useEffect, useRef } from 'react';
import { useMarketStore } from '../../stores/useMarketStore';
import { useSystemStore } from '../../stores/useSystemStore';
import { useSignalStore } from '../../stores/useSignalStore';
import { usePositionStore } from '../../stores/usePositionStore';
import { Timeframe } from '../../types/market';

function mapTimeframeToWs(tf: Timeframe): string {
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

export function useRealtimeStream() {
  const activeSymbol = useMarketStore((s) => s.activeSymbol);
  const activeTimeframe = useMarketStore((s) => s.activeTimeframe);
  const updateLiveTick = useMarketStore((s) => s.updateLiveTick);
  const updateLiveOrderBook = useMarketStore((s) => s.updateLiveOrderBook);
  const fetchRealMarketData = useMarketStore((s) => s.fetchRealMarketData);
  const setWsState = useSystemStore((s) => s.setWsState);

  const wsRef = useRef<WebSocket | null>(null);
  const pingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Initial load of real Bybit market data
  useEffect(() => {
    fetchRealMarketData(activeSymbol, activeTimeframe).then(() => {
      const tickers = useMarketStore.getState().tickers;
      useSignalStore.getState().syncSignalsWithLivePrices(tickers);
      usePositionStore.getState().syncMarkPrices(tickers);
    });
  }, [activeSymbol, activeTimeframe, fetchRealMarketData]);

  // Real-time Bybit WebSocket streaming
  useEffect(() => {
    let isMounted = true;
    setWsState('CONNECTING');

    const wsUrl = 'wss://stream.bybit.com/v5/public/linear';
    let socket: WebSocket | null = null;

    try {
      socket = new WebSocket(wsUrl);
      wsRef.current = socket;

      socket.onopen = () => {
        if (!isMounted) return;
        setWsState('CONNECTED');

        const interval = mapTimeframeToWs(activeTimeframe);
        // Subscribe to Bybit real-time topics
        const subMsg = {
          op: 'subscribe',
          args: [
            `tickers.${activeSymbol}`,
            `orderbook.50.${activeSymbol}`,
            `kline.${interval}.${activeSymbol}`,
          ],
        };
        socket?.send(JSON.stringify(subMsg));
        setWsState('SUBSCRIBED');
      };

      socket.onmessage = (event) => {
        if (!isMounted) return;
        try {
          const msg = JSON.parse(event.data);

          // 1. Ticker stream from Bybit
          if (msg.topic?.startsWith('tickers.') && msg.data) {
            const tickerData = msg.data;
            const price = parseFloat(tickerData.lastPrice || tickerData.markPrice);
            if (!isNaN(price) && price > 0) {
              updateLiveTick(activeSymbol, price, new Date(msg.ts).toISOString());
              const tickers = useMarketStore.getState().tickers;
              useSignalStore.getState().syncSignalsWithLivePrices(tickers);
              usePositionStore.getState().syncMarkPrices(tickers);
            }
          }

          // 2. Orderbook depth stream from Bybit
          if (msg.topic?.startsWith('orderbook.') && msg.data) {
            const obData = msg.data;
            const rawBids: [string, string][] = obData.b || [];
            const rawAsks: [string, string][] = obData.a || [];

            if (rawBids.length > 0 && rawAsks.length > 0) {
              let cumBid = 0;
              const bids = rawBids.slice(0, 20).map(([pStr, sStr]) => {
                const p = parseFloat(pStr);
                const s = parseFloat(sStr);
                cumBid += s;
                return { price: p, size: s, total: cumBid, percent: 0 };
              });

              let cumAsk = 0;
              const asks = rawAsks.slice(0, 20).map(([pStr, sStr]) => {
                const p = parseFloat(pStr);
                const s = parseFloat(sStr);
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

              updateLiveOrderBook({
                symbol: activeSymbol,
                timestamp: new Date(msg.ts).toISOString(),
                bids,
                asks,
                spread,
                spreadBps,
                midPrice,
                imbalance,
              });
            }
          }
        } catch {
          // ignore parsing error
        }
      };

      socket.onerror = () => {
        if (isMounted) setWsState('ERROR');
      };

      socket.onclose = () => {
        if (isMounted) setWsState('DISCONNECTED');
      };

      // Bybit heartbeat ping every 20s
      pingIntervalRef.current = setInterval(() => {
        if (socket?.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({ op: 'ping' }));
        }
      }, 20000);
    } catch {
      if (isMounted) setWsState('ERROR');
    }

    // Secondary background periodic refresh for funding and all tickers (every 5 seconds)
    const pollInterval = setInterval(() => {
      if (isMounted) {
        useMarketStore.getState().fetchRealMarketData().then(() => {
          const tickers = useMarketStore.getState().tickers;
          useSignalStore.getState().syncSignalsWithLivePrices(tickers);
          usePositionStore.getState().syncMarkPrices(tickers);
        });
      }
    }, 5000);

    return () => {
      isMounted = false;
      if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
      clearInterval(pollInterval);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [activeSymbol, activeTimeframe, updateLiveTick, updateLiveOrderBook, setWsState]);
}
