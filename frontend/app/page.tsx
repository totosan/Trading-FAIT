"use client";

import { useState, useEffect, useCallback } from "react";
import { connectSocket, getSocket } from "@/lib/socket";
import { AgentName, WebSocketMessage } from "@/lib/types";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface AgentDot {
  id: string;
  name: AgentName;
  active: boolean;
}

function ActivityDots({ agentStatuses }: { agentStatuses: Record<string, boolean> }) {
  const agents: AgentDot[] = [
    { id: "market", name: "MarketAnalyst", active: agentStatuses["MarketAnalyst"] || false },
    { id: "news", name: "NewsResearcher", active: agentStatuses["NewsResearcher"] || false },
    { id: "chart", name: "ChartConfigurator", active: agentStatuses["ChartConfigurator"] || false },
    { id: "report", name: "ReportWriter", active: agentStatuses["ReportWriter"] || false },
    { id: "indicator", name: "IndicatorCoder", active: agentStatuses["IndicatorCoder"] || false },
    { id: "executor", name: "CodeExecutor", active: agentStatuses["CodeExecutor"] || false },
  ];

  return (
    <div className="flex items-center gap-2 px-4 py-2 bg-slate-800/50 rounded-lg">
      <span className="text-xs text-slate-500 mr-2">Agenten:</span>
      {agents.map((agent) => (
        <div
          key={agent.id}
          className={`agent-dot ${agent.active ? "active" : ""}`}
          title={agent.name}
        />
      ))}
    </div>
  );
}

export default function Home() {
  const [message, setMessage] = useState("");
  const [isConnected, setIsConnected] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [agentStatuses, setAgentStatuses] = useState<Record<string, boolean>>({});
  const [report, setReport] = useState<string>("");
  const [lastAgentMessage, setLastAgentMessage] = useState<string>("");
  const [error, setError] = useState<string>("");

  // Handle incoming WebSocket messages
  const handleMessage = useCallback((msg: WebSocketMessage) => {
    console.log("[WS Message]", msg.type, msg);
    
    switch (msg.type) {
      case "query_start":
        setIsProcessing(true);
        setReport("");
        setError("");
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
          // Update last agent message (for sidebar)
          setLastAgentMessage(msg.content.slice(0, 500));
          
          // Check if this is a report - from ReportWriter or final Orchestrator response
          // Reports typically contain markdown headers (#) or structured content
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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim() || isProcessing) return;
    
    const socket = getSocket();
    if (socket.isConnected) {
      socket.sendQuery(message);
      setMessage("");
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
        <div className="mb-4 p-3 bg-red-900/50 border border-red-700 rounded-lg text-red-300 text-sm">
          ⚠️ {error}
        </div>
      )}

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chart Area */}
        <div className="lg:col-span-2 bg-slate-800/30 rounded-lg p-4 min-h-[400px] flex items-center justify-center">
          <div className="text-center text-slate-500">
            <p className="text-lg">📈 TradingView Chart</p>
            <p className="text-sm mt-2">Wird in Phase 7 implementiert</p>
          </div>
        </div>

        {/* Trade Card Area */}
        <div className="bg-slate-800/30 rounded-lg p-4">
          <h2 className="text-sm font-medium text-slate-400 mb-4">
            Trade Empfehlung
          </h2>
          {lastAgentMessage ? (
            <div className="prose prose-invert prose-sm max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {lastAgentMessage.slice(0, 500)}
              </ReactMarkdown>
            </div>
          ) : (
            <div className="text-center text-slate-500 py-8">
              <p>Keine aktive Empfehlung</p>
              <p className="text-xs mt-2">Stelle eine Frage um zu starten</p>
            </div>
          )}
        </div>
      </div>

      {/* Report Area */}
      <div className="mt-6 bg-slate-800/30 rounded-lg p-4 min-h-[200px]">
        <h2 className="text-sm font-medium text-slate-400 mb-4">
          Analyse Report
        </h2>
        {report ? (
          <div className="prose prose-invert prose-sm max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {report.replace(/^```markdown\n?/, "").replace(/\n?```$/, "")}
            </ReactMarkdown>
          </div>
        ) : (
          <div className="text-center text-slate-500 py-8">
            <p>{isProcessing ? "Agenten analysieren..." : "Kein Report verfügbar"}</p>
          </div>
        )}
      </div>

      {/* Chat Input */}
      <form onSubmit={handleSubmit} className="mt-6">
        <div className="flex gap-3">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Deine Frage hier eingeben... z.B. 'Analysiere BTC für Swing-Trade'"
            className="flex-1 px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent disabled:opacity-50"
            disabled={isProcessing}
          />
          <button
            type="submit"
            disabled={isProcessing || !isConnected}
            className="px-6 py-3 bg-green-600 hover:bg-green-500 disabled:bg-slate-600 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors"
          >
            {isProcessing ? "..." : "Senden"}
          </button>
        </div>
      </form>

      {/* Footer */}
      <footer className="mt-8 text-center text-xs text-slate-600">
        Trading-FAIT v0.1.0 | Magentic-One + Azure OpenAI | Nur Empfehlungen, keine Order-Ausführung
      </footer>
    </main>
  );
}
