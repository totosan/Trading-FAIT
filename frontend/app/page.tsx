"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { connectSocket, getSocket } from "@/lib/socket";
import { WebSocketMessage, TradeRecommendation, ChatMessage, ChartPriceLevels } from "@/lib/types";
import {
  ActivityDots,
  TradeCard,
  TradeCardEmpty,
  MarkdownReport,
  MarkdownReportLoading,
  LightweightChart,
  Chat,
} from "@/components";

export default function Home() {
  // Connection State
  const [isConnected, setIsConnected] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string>("");

  // Agent State
  const [agentStatuses, setAgentStatuses] = useState<Record<string, boolean>>({});
  const [activeAgent, setActiveAgent] = useState<string>("");

  // Data State
  const [report, setReport] = useState<string>("");
  const [tradeRecommendation, setTradeRecommendation] = useState<TradeRecommendation | null>(null);
  const [currentSymbol, setCurrentSymbol] = useState<string>("BTCUSD");
  const [priceLevels, setPriceLevels] = useState<ChartPriceLevels | undefined>(undefined);
  
  // Chat Messages State
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const sessionIdRef = useRef<string>("");
  const pendingQueryRef = useRef<string>("");

  // Handle incoming WebSocket messages
  const handleMessage = useCallback((msg: WebSocketMessage) => {
    console.log("[WS Message]", msg.type, msg);
    
    switch (msg.type) {
      case "query_start":
        setIsProcessing(true);
        setReport("");
        setError("");
        setTradeRecommendation(null);
        setPriceLevels(undefined);
        // Store session ID for follow-up messages
        if (msg.session_id) {
          sessionIdRef.current = msg.session_id;
        }
        break;
      
      case "quick_response":
        // Fast price query response - add to chat
        if (msg.message) {
          setChatMessages(prev => [...prev, {
            id: `quick-${Date.now()}`,
            type: "quick_response",
            content: msg.message!,
            timestamp: new Date(),
            symbols: msg.symbols,
          }]);
        }
        break;
      
      case "clarification_needed":
        // Agent needs clarification about which symbol
        if (msg.message) {
          setChatMessages(prev => [...prev, {
            id: `clarify-${Date.now()}`,
            type: "clarification",
            content: msg.message!,
            timestamp: new Date(),
            candidates: msg.candidates,
          }]);
        }
        break;
        
      case "agent_status":
        if (msg.agent) {
          setAgentStatuses(prev => ({
            ...prev,
            [msg.agent!]: msg.active || false,
          }));
          // Track which agent is currently active
          if (msg.active) {
            setActiveAgent(msg.agent);
          }
        }
        break;
        
      case "agent_message":
        if (msg.content) {
          console.log(`[Agent ${msg.agent}] Message length: ${msg.content.length}`);
          
          // Update report with the latest substantial content
          // Priority: ReportWriter > MagenticOneOrchestrator > any agent with long content
          const isFromReportWriter = msg.agent === "ReportWriter";
          const isFromOrchestrator = (msg.agent as unknown) === "MagenticOneOrchestrator";
          const content = msg.content ?? "";
          const hasSubstantialContent = msg.content.length > 300;
          const hasReportStructure = content.includes("#") || 
                                     content.includes("---") || 
                                     content.includes("•");
          
          // Always update if it's a substantial message with structure
          if (hasSubstantialContent && hasReportStructure) {
            // Keep the longer/better report
            setReport(prev => {
              // ReportWriter always wins
              if (isFromReportWriter) return content;
              // Orchestrator replaces if current is from other agent or shorter
              if (isFromOrchestrator && content.length > (prev?.length || 0)) {
                return content;
              }
              // Other agents only if we have nothing
              if (!prev || prev.length < 100) return content;
              return prev || "";
            });
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

          // Derive overlay levels for chart
          const entries =
            typeof trade.entry === "number"
              ? [trade.entry]
              : [trade.entry.min, trade.entry.max].filter(Boolean);
          const takeProfits = Array.isArray(trade.takeProfit)
            ? trade.takeProfit
            : [trade.takeProfit];
          setPriceLevels({
            entries,
            stopLoss: trade.stopLoss,
            takeProfits,
          });
        }
        break;

      case "chart_config":
        if (msg.data && "symbol" in msg.data) {
          setCurrentSymbol(msg.data.symbol as string);
          const cfg = msg.data as { priceLevels?: ChartPriceLevels };
          if (cfg.priceLevels) {
            setPriceLevels(cfg.priceLevels);
          }
        }
        break;
        
      case "query_complete":
        setIsProcessing(false);
        setActiveAgent("");
        // Reset all agent statuses
        setAgentStatuses({});
        break;
        
      case "error":
        setError(msg.error || "Unbekannter Fehler");
        setIsProcessing(false);
        setActiveAgent("");
        break;
    }
  }, []);

  // Setup WebSocket connection
  useEffect(() => {
    // In GitHub Codespaces, use the forwarded port URL
    let wsUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8001/ws";
    
    // Detect Codespaces environment and construct proper WebSocket URL
    if (typeof window !== "undefined") {
      const hostname = window.location.hostname;
      if (hostname.includes(".app.github.dev")) {
        // GitHub Codespaces: replace frontend port with backend port
        // Format: <codespace>-3000.app.github.dev -> <codespace>-8001.app.github.dev
        const backendHost = hostname.replace("-3000.", "-8001.");
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
      // Add user message to chat
      setChatMessages(prev => [...prev, {
        id: `user-${Date.now()}`,
        type: "user",
        content: message,
        timestamp: new Date(),
      }]);
      
      // Store pending query for clarification follow-ups
      pendingQueryRef.current = message;
      
      // Send with session ID for conversation context
      socket.send({
        type: "query",
        message: message,
        session_id: sessionIdRef.current || undefined,
      });
      
      // Try to extract symbol from query for chart
      const symbolMatch = message.match(/\b(BTC|ETH|SOL|XRP|ADA|DOGE|AAPL|MSFT|TSLA|GOOGL|NVDA)\b/i);
      if (symbolMatch) {
        setCurrentSymbol(symbolMatch[1].toUpperCase());
      }
    } else {
      setError("Nicht verbunden. Bitte warten...");
    }
  };

  // Handle clarification selection
  const handleClarificationSelect = (symbol: string) => {
    const socket = getSocket();
    if (!socket.isConnected) return;
    
    let query: string;
    if (symbol === "alle") {
      query = `Analysiere alle: ${pendingQueryRef.current}`;
    } else {
      query = `Analysiere ${symbol}`;
    }
    
    // Add user selection to chat
    setChatMessages(prev => [...prev, {
      id: `user-${Date.now()}`,
      type: "user",
      content: symbol === "alle" ? "Alle analysieren" : symbol,
      timestamp: new Date(),
    }]);
    
    socket.send({
      type: "query",
      message: query,
      session_id: sessionIdRef.current || undefined,
    });
    
    setCurrentSymbol(symbol === "alle" ? "BTCUSD" : symbol);
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
              {isProcessing && activeAgent 
                ? `${activeAgent} arbeitet...` 
                : isProcessing 
                ? "Analysiere..." 
                : isConnected 
                ? "Verbunden" 
                : "Getrennt"}
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
          <LightweightChart
            symbol={currentSymbol}
            priceLevels={priceLevels}
            height={420}
            theme="dark"
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
          messages={chatMessages}
          onClarificationSelect={handleClarificationSelect}
        />
      </div>

      {/* Footer */}
      <footer className="mt-8 text-center text-xs text-slate-600">
        Trading-FAIT v0.1.0 | Magentic-One + Azure OpenAI | Nur Empfehlungen, keine Order-Ausführung
      </footer>
    </main>
  );
}
