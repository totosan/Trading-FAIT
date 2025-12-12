"use client";

import { useEffect, useRef } from "react";
import { createChart, ColorType, Time } from "lightweight-charts";
import { ChartPriceLevels } from "@/lib/types";

interface LightweightChartProps {
  symbol: string;
  priceLevels?: ChartPriceLevels;
  height?: number;
  theme?: "dark" | "light";
}

type Candle = { time: Time; open: number; high: number; low: number; close: number };

async function fetchCrypto(symbol: string): Promise<Candle[]> {
  // Example: BTC/USDT -> BTCUSDT
  const pair = symbol.replace("/", "");
  const url = `https://api.binance.com/api/v3/klines?symbol=${pair.toUpperCase()}&interval=1h&limit=200`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Binance fetch failed (${res.status})`);
  const data = (await res.json()) as any[];
  return data.map((candle) => ({
    time: (candle[0] / 1000) as Time,
    open: parseFloat(candle[1]),
    high: parseFloat(candle[2]),
    low: parseFloat(candle[3]),
    close: parseFloat(candle[4]),
  }));
}

async function fetchStock(symbol: string): Promise<Candle[]> {
  // Yahoo finance style endpoint
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${symbol}?interval=1h&range=3mo`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Yahoo fetch failed (${res.status})`);
  const json = await res.json();
  const result = json?.chart?.result?.[0];
  const timestamps: number[] = result?.timestamp || [];
  const quotes = result?.indicators?.quote?.[0];
  if (!timestamps.length || !quotes) throw new Error("Yahoo data missing");
  const opens = quotes.open || [];
  const highs = quotes.high || [];
  const lows = quotes.low || [];
  const closes = quotes.close || [];
  const candles: Candle[] = [];
  for (let i = 0; i < timestamps.length; i++) {
    if (opens[i] == null || highs[i] == null || lows[i] == null || closes[i] == null) continue;
    candles.push({
      time: timestamps[i] as Time,
      open: opens[i],
      high: highs[i],
      low: lows[i],
      close: closes[i],
    });
  }
  return candles;
}

function isCrypto(symbol: string): boolean {
  return symbol.includes("/") || ["BTC", "ETH", "SOL", "XRP", "ADA", "DOGE", "AVAX", "DOT", "MATIC", "LINK"].includes(symbol.toUpperCase());
}

export function LightweightChart({ symbol, priceLevels, height = 420, theme = "dark" }: LightweightChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let chartDisposed = false;
    const chart = createChart(container, {
      height,
      layout: {
        background: { type: ColorType.Solid, color: theme === "dark" ? "#0f172a" : "#ffffff" },
        textColor: theme === "dark" ? "#cbd5e1" : "#0f172a",
      },
      grid: {
        vertLines: { color: theme === "dark" ? "#1e293b" : "#e2e8f0" },
        horzLines: { color: theme === "dark" ? "#1e293b" : "#e2e8f0" },
      },
      rightPriceScale: {
        borderColor: theme === "dark" ? "#334155" : "#cbd5e1",
      },
      timeScale: { borderColor: theme === "dark" ? "#334155" : "#cbd5e1" },
      crosshair: { mode: 1 },
    });

    const candleSeries = chart.addCandlestickSeries({
      upColor: "#10b981",
      downColor: "#ef4444",
      wickUpColor: "#10b981",
      wickDownColor: "#ef4444",
      borderUpColor: "#10b981",
      borderDownColor: "#ef4444",
    });

    const loadData = async () => {
      try {
        const candles = isCrypto(symbol)
          ? await fetchCrypto(symbol)
          : await fetchStock(symbol);
        if (!chartDisposed) {
          candleSeries.setData(candles);
          if (candles.length > 0) {
            const last = candles[candles.length - 1];
            chart.timeScale().setVisibleRange({ from: candles[Math.max(0, candles.length - 120)].time, to: last.time });
          }
        }
      } catch (err) {
        console.warn("Chart data fetch failed", err);
      }

      // Add price lines if available
      if (priceLevels && !chartDisposed) {
        if (priceLevels.entries && priceLevels.entries.length > 0) {
          priceLevels.entries.forEach((lvl) => {
            candleSeries.createPriceLine({
              price: lvl,
              color: "#22c55e",
              lineWidth: 2,
              lineStyle: 0,
              axisLabelVisible: true,
              title: "Entry",
            });
          });
        }
        if (priceLevels.stopLoss) {
          candleSeries.createPriceLine({
            price: priceLevels.stopLoss,
            color: "#ef4444",
            lineWidth: 2,
            lineStyle: 2,
            axisLabelVisible: true,
            title: "Stop",
          });
        }
        if (priceLevels.takeProfits && priceLevels.takeProfits.length > 0) {
          priceLevels.takeProfits.forEach((lvl, idx) => {
            candleSeries.createPriceLine({
              price: lvl,
              color: "#38bdf8",
              lineWidth: 2,
              lineStyle: 1,
              axisLabelVisible: true,
              title: `TP${idx + 1}`,
            });
          });
        }
      }
    };

    loadData();

    return () => {
      chartDisposed = true;
      chart.remove();
    };
  }, [symbol, priceLevels, height, theme]);

  return <div className="w-full" ref={containerRef} />;
}

export default LightweightChart;
