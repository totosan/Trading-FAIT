"use client";

import { useState, useEffect, useCallback } from "react";
import { connectSocket, getSocket } from "@/lib/socket";
import { WebSocketMessage, TradeRecommendation } from "@/lib/types";
import {
  ActivityDots,
  TradeCard,
  TradeCardEmpty,
  MarkdownReport,
  MarkdownReportLoading,
  TradingViewWidget,
  Chat,
} from "@/components";

export default function Home() {
  // Connection State
  const [isConnected, setIsConnected] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string>("");

  // Agent State
  const [agentStatuses, setAgentStatuses] = useState<Record<string, boolean>>({});

  // Data State
  const [report, setReport] = useState<string>("");
  const [tradeRecommendation, setTradeRecommendation] = useState<TradeRecommendation | null>(null);
  const [currentSymbol, setCurrentSymbol] = useState<string>("BTCUSD");

  // Handle incoming WebSocket messages
  const handleMessage = useCallback((msg: WebSocketMessage) => {
    console.log("[WS Message]", msg.type, msg);
    
    switch (msg.type) {
      case "query_start":
        setIsProcessing(true);
        setReport("");
        setError("");
        setTradeRecommendation(null);
        break;
        
      case "agent_status":
        if (msg.agent) {
          setAgentStatuses(prev => ({
            ...prev,
            [msg.agent!]: msg.active || false,
          }));
        }
        break;
        
      case "agent_message":
        if (msg.content) {
          // Check if this is a report from ReportWriter or final Orchestrator response
          const isReport = 
            (msg.agent === "ReportWriter" && msg.content.includes("#")) ||
            (msg.agent === "MagenticOneOrchestrator" && 
             msg.content.includes("##") && 
             msg.content.length > 500);
          
          if (isReport) {
            setReport(msg.content);
          }
        }
        break;
      
      case "trade_recommendation":
        if (msg.data && "symbol" in msg.data) {
          const trade = msg.data as TradeRecommendation;
          setTradeRecommendation(trade);
          // Update chart symbol
          if (trade.symbol) {
            setCurrentSymbol(trade.symbol);
          }
        }
        break;

      case "chart_config":
        if (msg.data && "symbol" in msg.data) {
          setCurrentSymbol(msg.data.symbol as string);
        }
        break;
        
      case "query_complete":
        setIsProcessing(false);
        // Reset all agent statuses
        setAgentStatuses({});
        break;
        
      case "error":
        setError(msg.error || "Unbekannter Fehler");
        setIsProcessing(false);
        break;
    }
  }, []);

  // Setup WebSocket connection
  useEffect(() => {
    // In GitHub Codespaces, use the forwarded port URL
    let wsUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws";
    
    // Detect Codespaces environment and construct proper WebSocket URL
    if (typeof window !== "undefined") {
      const hostname = window.location.hostname;
      if (hostname.includes(".app.github.dev")) {
        // GitHub Codespaces: replace frontend port with backend port
        // Format: <codespace>-3000.app.github.dev -> <codespace>-8000.app.github.dev
        const backendHost = hostname.replace("-3000.", "-8000.");
        wsUrl = `wss://${backendHost}/ws`;
        console.log("[WS] Codespaces detected, using:", wsUrl);
      }
    }
    
    const socket = connectSocket({ url: wsUrl });
    
    const unsubConnection = socket.onConnection((connected) => {
      setIsConnected(connected);
      if (!connected) {
        setAgentStatuses({});
      }
    });
    
    const unsubMessage = socket.onMessage(handleMessage);
    
    return () => {
      unsubConnection();
      unsubMessage();
    };
  }, [handleMessage]);

  // Send message handler
  const handleSendMessage = (message: string) => {
    if (!message.trim() || isProcessing) return;
    
    const socket = getSocket();
    if (socket.isConnected) {
      socket.sendQuery(message);
      
      // Try to extract symbol from query for chart
      const symbolMatch = message.match(/\b(BTC|ETH|SOL|XRP|ADA|DOGE|AAPL|MSFT|TSLA|GOOGL|NVDA)\b/i);
      if (symbolMatch) {
        setCurrentSymbol(symbolMatch[1].toUpperCase());
      }
    } else {
      setError("Nicht verbunden. Bitte warten...");
    }
  };

  return (
    <main className="min-h-screen p-6">
      {/* Header */}
      <header className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-white">
          Trading-FAIT
          <span className="text-sm font-normal text-slate-500 ml-2">
            AI Trading Assistant
          </span>
        </h1>
        <div className="flex items-center gap-4">
          <ActivityDots agentStatuses={agentStatuses} />
          <div className="flex items-center gap-2">
            <div
              className={`w-2 h-2 rounded-full ${
                isConnected ? "bg-green-500" : "bg-red-500"
              } ${isProcessing ? "animate-pulse" : ""}`}
            />
            <span className="text-xs text-slate-500">
              {isProcessing ? "Analysiere..." : isConnected ? "Verbunden" : "Getrennt"}
            </span>
          </div>
        </div>
      </header>

      {/* Error Banner */}
      {error && (
        <div className="mb-4 p-3 bg-red-900/50 border border-red-700 rounded-lg text-red-300 text-sm flex items-center justify-between">
          <span>⚠️ {error}</span>
          <button
            onClick={() => setError("")}
            className="text-red-400 hover:text-red-200"
          >
            ✕
          </button>
        </div>
      )}

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chart Area */}
        <div className="lg:col-span-2 bg-slate-800/30 rounded-lg overflow-hidden min-h-[400px]">
          <TradingViewWidget
            symbol={currentSymbol}
            interval="D"
            theme="dark"
            height={400}
          />
        </div>

        {/* Trade Card Area */}
        <div>
          <h2 className="text-sm font-medium text-slate-400 mb-4">
            Trade Empfehlung
          </h2>
          {tradeRecommendation ? (
            <TradeCard
              trade={tradeRecommendation}
              onDismiss={() => setTradeRecommendation(null)}
            />
          ) : (
            <TradeCardEmpty />
          )}
        </div>
      </div>

      {/* Report Area */}
      <div className="mt-6">
        {isProcessing && !report ? (
          <MarkdownReportLoading />
        ) : (
          <MarkdownReport
            content={report}
            title="Analyse Report"
            collapsible={report.length > 1000}
          />
        )}
      </div>

      {/* Chat Input */}
      <div className="mt-6">
        <Chat
          onSendMessage={handleSendMessage}
          isConnected={isConnected}
          isProcessing={isProcessing}
        />
      </div>

      {/* Footer */}
      <footer className="mt-8 text-center text-xs text-slate-600">
        Trading-FAIT v0.1.0 | Magentic-One + Azure OpenAI | Nur Empfehlungen, keine Order-Ausführung
      </footer>
    </main>
  );
}
