"use client";

import { useEffect, useRef, memo } from "react";

interface TradingViewWidgetProps {
  symbol?: string;
  interval?: string;
  theme?: "dark" | "light";
  height?: number;
  autosize?: boolean;
  showToolbar?: boolean;
}

// TradingView Free Widget - Advanced Chart
function TradingViewWidgetComponent({
  symbol = "BTCUSD",
  interval = "D",
  theme = "dark",
  height = 400,
  autosize = true,
  showToolbar = true,
}: TradingViewWidgetProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const scriptRef = useRef<HTMLScriptElement | null>(null);

  useEffect(() => {
    // Clean up previous widget
    if (containerRef.current) {
      containerRef.current.innerHTML = "";
    }
    if (scriptRef.current) {
      scriptRef.current.remove();
    }

    // Create widget container
    const widgetContainer = document.createElement("div");
    widgetContainer.className = "tradingview-widget-container__widget";
    widgetContainer.style.height = autosize ? "100%" : `${height}px`;
    widgetContainer.style.width = "100%";

    if (containerRef.current) {
      containerRef.current.appendChild(widgetContainer);
    }

    // Create and load TradingView script
    const script = document.createElement("script");
    script.src = "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
    script.type = "text/javascript";
    script.async = true;
    
    // Convert symbol to TradingView format
    const tvSymbol = convertToTradingViewSymbol(symbol);
    
    script.innerHTML = JSON.stringify({
      autosize: autosize,
      symbol: tvSymbol,
      interval: interval,
      timezone: "Europe/Berlin",
      theme: theme,
      style: "1", // Candlestick
      locale: "de_DE",
      enable_publishing: false,
      hide_top_toolbar: !showToolbar,
      hide_legend: false,
      save_image: false,
      calendar: false,
      hide_volume: false,
      support_host: "https://www.tradingview.com",
      container_id: widgetContainer.id,
    });

    if (containerRef.current) {
      containerRef.current.appendChild(script);
      scriptRef.current = script;
    }

    return () => {
      if (scriptRef.current) {
        scriptRef.current.remove();
      }
    };
  }, [symbol, interval, theme, height, autosize, showToolbar]);

  return (
    <div className="tradingview-widget-container h-full w-full" ref={containerRef}>
      <div className="tradingview-widget-container__widget h-full w-full"></div>
    </div>
  );
}

// Convert symbol formats to TradingView format
function convertToTradingViewSymbol(symbol: string): string {
  // Handle crypto pairs (e.g., "BTC/USDT" -> "BINANCE:BTCUSDT")
  if (symbol.includes("/")) {
    const [base, quote] = symbol.split("/");
    return `BINANCE:${base}${quote}`;
  }
  
  // Handle crypto symbols without slash (e.g., "BTC" -> "BINANCE:BTCUSD")
  const cryptoSymbols = ["BTC", "ETH", "SOL", "XRP", "ADA", "DOGE", "AVAX", "DOT", "MATIC", "LINK"];
  if (cryptoSymbols.includes(symbol.toUpperCase())) {
    return `BINANCE:${symbol.toUpperCase()}USDT`;
  }
  
  // Handle stock symbols (e.g., "AAPL" -> "NASDAQ:AAPL")
  // Default to NASDAQ for US stocks
  if (/^[A-Z]{1,5}$/.test(symbol)) {
    return `NASDAQ:${symbol}`;
  }
  
  // Return as-is if already in correct format
  return symbol;
}

// Memoize to prevent unnecessary re-renders
export const TradingViewWidget = memo(TradingViewWidgetComponent);

// Mini chart widget for trade cards
export function TradingViewMiniChart({
  symbol = "BTCUSD",
  theme = "dark",
}: {
  symbol?: string;
  theme?: "dark" | "light";
}) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    
    containerRef.current.innerHTML = "";
    
    const script = document.createElement("script");
    script.src = "https://s3.tradingview.com/external-embedding/embed-widget-mini-symbol-overview.js";
    script.type = "text/javascript";
    script.async = true;
    
    const tvSymbol = convertToTradingViewSymbol(symbol);
    
    script.innerHTML = JSON.stringify({
      symbol: tvSymbol,
      width: "100%",
      height: "100%",
      locale: "de_DE",
      dateRange: "1D",
      colorTheme: theme,
      isTransparent: true,
      autosize: true,
      largeChartUrl: "",
    });

    containerRef.current.appendChild(script);

    return () => {
      if (containerRef.current) {
        containerRef.current.innerHTML = "";
      }
    };
  }, [symbol, theme]);

  return (
    <div className="tradingview-widget-container h-24" ref={containerRef}>
      <div className="tradingview-widget-container__widget h-full"></div>
    </div>
  );
}

export default TradingViewWidget;
