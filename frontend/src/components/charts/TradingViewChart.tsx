import React, { useEffect, useRef, useState } from 'react';
import {
  createChart,
  IChartApi,
  ISeriesApi,
  ColorType,
  CandlestickData,
  LineData,
  HistogramData,
  CandlestickSeries,
  LineSeries,
  HistogramSeries,
} from 'lightweight-charts';
import { useMarketStore } from '../../stores/useMarketStore';
import { formatPrice } from '../../lib/formatters/formatters';

interface TooltipData {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  ema8?: number;
  ema21?: number;
}

export const TradingViewChart: React.FC<{ className?: string }> = ({ className }) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  const candles = useMarketStore((s) => s.candles);
  const activeSymbol = useMarketStore((s) => s.activeSymbol);
  const indicators = useMarketStore((s) => s.indicators);

  const [hoverData, setHoverData] = useState<TooltipData | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    // Clean up existing chart if any
    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
    }

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: chartContainerRef.current.clientHeight || 450,
      layout: {
        background: { type: ColorType.Solid, color: '#080a0f' },
        textColor: '#8b949e',
        fontSize: 11,
        fontFamily: '"JetBrains Mono", monospace',
      },
      grid: {
        vertLines: { color: 'rgba(33, 38, 45, 0.45)' },
        horzLines: { color: 'rgba(33, 38, 45, 0.45)' },
      },
      crosshair: {
        mode: 1, // Magnet
        vertLine: {
          color: '#06b6d4',
          width: 1,
          style: 3,
          labelBackgroundColor: '#161b22',
        },
        horzLine: {
          color: '#06b6d4',
          width: 1,
          style: 3,
          labelBackgroundColor: '#161b22',
        },
      },
      rightPriceScale: {
        borderColor: '#21262d',
        autoScale: true,
      },
      timeScale: {
        borderColor: '#21262d',
        timeVisible: true,
        secondsVisible: false,
      },
    });

    chartRef.current = chart;

    // 1. Candlestick Series
    let candleSeries: any;
    try {
      // lightweight-charts v5 syntax
      if ((chart as any).addSeries && CandlestickSeries) {
        candleSeries = (chart as any).addSeries(CandlestickSeries, {
          upColor: '#10b981',
          downColor: '#f43f5e',
          borderVisible: false,
          wickUpColor: '#10b981',
          wickDownColor: '#f43f5e',
        });
      } else if ((chart as any).addCandlestickSeries) {
        candleSeries = (chart as any).addCandlestickSeries({
          upColor: '#10b981',
          downColor: '#f43f5e',
          borderVisible: false,
          wickUpColor: '#10b981',
          wickDownColor: '#f43f5e',
        });
      }
    } catch {
      // fallback
      candleSeries = (chart as any).addCandlestickSeries?.({
        upColor: '#10b981',
        downColor: '#f43f5e',
        borderVisible: false,
        wickUpColor: '#10b981',
        wickDownColor: '#f43f5e',
      });
    }

    if (candleSeries && candles.length > 0) {
      const candleData: CandlestickData[] = candles.map((c) => ({
        time: c.time as any,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      }));
      candleSeries.setData(candleData);
    }

    // 2. Volume Histogram Series
    let volumeSeries: any;
    try {
      if ((chart as any).addSeries && HistogramSeries) {
        volumeSeries = (chart as any).addSeries(HistogramSeries, {
          color: '#21262d',
          priceFormat: { type: 'volume' },
          priceScaleId: 'volume',
        });
      } else if ((chart as any).addHistogramSeries) {
        volumeSeries = (chart as any).addHistogramSeries({
          color: '#21262d',
          priceFormat: { type: 'volume' },
          priceScaleId: 'volume',
        });
      }
    } catch {}

    if (volumeSeries && candles.length > 0) {
      chart.priceScale('volume').applyOptions({
        scaleMargins: { top: 0.82, bottom: 0 },
      });
      const volData: HistogramData[] = candles.map((c) => ({
        time: c.time as any,
        value: c.volume,
        color: c.close >= c.open ? 'rgba(16, 185, 129, 0.25)' : 'rgba(244, 63, 94, 0.25)',
      }));
      volumeSeries.setData(volData);
    }

    // Helper for adding lines
    const addLine = (color: string, width: number = 1, lineStyle: number = 0) => {
      try {
        if ((chart as any).addSeries && LineSeries) {
          return (chart as any).addSeries(LineSeries, {
            color,
            lineWidth: width as any,
            lineStyle,
            crosshairMarkerVisible: false,
          });
        } else if ((chart as any).addLineSeries) {
          return (chart as any).addLineSeries({
            color,
            lineWidth: width,
            lineStyle,
            crosshairMarkerVisible: false,
          });
        }
      } catch {
        return null;
      }
    };

    // 3. Indicators lines
    if (indicators.ema8) {
      const s = addLine('#06b6d4', 1.5);
      if (s) s.setData(candles.filter(c => c.ema8).map(c => ({ time: c.time as any, value: c.ema8! })));
    }
    if (indicators.ema21) {
      const s = addLine('#f59e0b', 1.5);
      if (s) s.setData(candles.filter(c => c.ema21).map(c => ({ time: c.time as any, value: c.ema21! })));
    }
    if (indicators.ema55) {
      const s = addLine('#8b5cf6', 1.5);
      if (s) s.setData(candles.filter(c => c.ema55).map(c => ({ time: c.time as any, value: c.ema55! })));
    }
    if (indicators.ema200) {
      const s = addLine('#ec4899', 2);
      if (s) s.setData(candles.filter(c => c.ema200).map(c => ({ time: c.time as any, value: c.ema200! })));
    }

    // Bollinger Bands
    if (indicators.bollinger) {
      const upper = addLine('rgba(6, 182, 212, 0.6)', 1, 2);
      const lower = addLine('rgba(6, 182, 212, 0.6)', 1, 2);
      const middle = addLine('rgba(6, 182, 212, 0.3)', 1, 3);
      if (upper) upper.setData(candles.filter(c => c.bbUpper).map(c => ({ time: c.time as any, value: c.bbUpper! })));
      if (lower) lower.setData(candles.filter(c => c.bbLower).map(c => ({ time: c.time as any, value: c.bbLower! })));
      if (middle) middle.setData(candles.filter(c => c.bbMiddle).map(c => ({ time: c.time as any, value: c.bbMiddle! })));
    }

    // Supertrend
    if (indicators.supertrend) {
      const stBull = addLine('#10b981', 2);
      const stBear = addLine('#f43f5e', 2);
      if (stBull) stBull.setData(candles.filter(c => c.supertrend && c.supertrendDirection === 'bull').map(c => ({ time: c.time as any, value: c.supertrend! })));
      if (stBear) stBear.setData(candles.filter(c => c.supertrend && c.supertrendDirection === 'bear').map(c => ({ time: c.time as any, value: c.supertrend! })));
    }

    // Set initial latest candle tooltip
    if (candles.length > 0) {
      const latest = candles[candles.length - 1];
      const d = new Date(latest.time * 1000);
      setHoverData({
        time: d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        open: latest.open,
        high: latest.high,
        low: latest.low,
        close: latest.close,
        volume: latest.volume,
        ema8: latest.ema8,
        ema21: latest.ema21,
      });
    }

    // Crosshair move handler
    chart.subscribeCrosshairMove((param) => {
      if (!param.time || !param.point) {
        if (candles.length > 0) {
          const latest = candles[candles.length - 1];
          const d = new Date(latest.time * 1000);
          setHoverData({
            time: d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            open: latest.open,
            high: latest.high,
            low: latest.low,
            close: latest.close,
            volume: latest.volume,
            ema8: latest.ema8,
            ema21: latest.ema21,
          });
        }
        return;
      }

      const candle = candles.find((c) => c.time === param.time);
      if (candle) {
        const d = new Date(candle.time * 1000);
        setHoverData({
          time: d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          open: candle.open,
          high: candle.high,
          low: candle.low,
          close: candle.close,
          volume: candle.volume,
          ema8: candle.ema8,
          ema21: candle.ema21,
        });
      }
    });

    // Resize Observer
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight || 450,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, [candles, indicators, activeSymbol]);

  return (
    <div className={`relative w-full h-full flex flex-col ${className || ''}`}>
      {/* Dynamic Bloomberg Bar Header (OHLCV + Active Indicators) */}
      <div className="absolute top-2 left-3 z-10 flex flex-wrap items-center gap-x-4 gap-y-1 font-mono text-2xs bg-terminal-panel/90 px-2.5 py-1 rounded border border-terminal-border/80 backdrop-blur-xs pointer-events-none select-none">
        {hoverData && (
          <>
            <span className="text-terminal-muted">{hoverData.time}</span>
            <span>
              O: <span className="text-terminal-text font-semibold">{formatPrice(hoverData.open, activeSymbol)}</span>
            </span>
            <span>
              H: <span className="text-terminal-bull font-semibold">{formatPrice(hoverData.high, activeSymbol)}</span>
            </span>
            <span>
              L: <span className="text-terminal-bear font-semibold">{formatPrice(hoverData.low, activeSymbol)}</span>
            </span>
            <span>
              C:{' '}
              <span
                className={`font-semibold ${
                  hoverData.close >= hoverData.open ? 'text-terminal-bull' : 'text-terminal-bear'
                }`}
              >
                {formatPrice(hoverData.close, activeSymbol)}
              </span>
            </span>
            <span>
              Vol: <span className="text-terminal-cyan">{hoverData.volume.toLocaleString()}</span>
            </span>
            {indicators.ema8 && hoverData.ema8 && (
              <span className="text-terminal-cyan">EMA(8): {formatPrice(hoverData.ema8, activeSymbol)}</span>
            )}
            {indicators.ema21 && hoverData.ema21 && (
              <span className="text-terminal-amber">EMA(21): {formatPrice(hoverData.ema21, activeSymbol)}</span>
            )}
          </>
        )}
      </div>

      <div ref={chartContainerRef} className="w-full flex-1 min-h-[380px]" />
    </div>
  );
};
