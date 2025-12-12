"use client";

import { useState, useRef, useEffect } from "react";

interface ChatMessage {
  id: string;
  type: "user" | "system" | "agent";
  content: string;
  agent?: string;
  timestamp: Date;
}

interface ChatProps {
  onSendMessage: (message: string) => void;
  isConnected: boolean;
  isProcessing: boolean;
  messages?: ChatMessage[];
  placeholder?: string;
}

export function Chat({
  onSendMessage,
  isConnected,
  isProcessing,
  messages = [],
  placeholder = "Deine Frage hier eingeben... z.B. 'Analysiere BTC für Swing-Trade'",
}: ChatProps) {
  const [input, setInput] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isProcessing || !isConnected) return;
    
    onSendMessage(input.trim());
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Submit on Enter (without Shift)
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages Area (optional, for future chat history) */}
      {messages.length > 0 && (
        <div className="flex-1 overflow-y-auto mb-4 space-y-3 max-h-[300px]">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.type === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] px-4 py-2 rounded-lg ${
                  msg.type === "user"
                    ? "bg-green-600 text-white"
                    : msg.type === "agent"
                    ? "bg-slate-700 text-slate-200"
                    : "bg-slate-800 text-slate-400"
                }`}
              >
                {msg.agent && (
                  <span className="text-xs text-slate-400 block mb-1">
                    {msg.agent}
                  </span>
                )}
                <p className="text-sm">{msg.content}</p>
                <span className="text-xs opacity-50 mt-1 block">
                  {msg.timestamp.toLocaleTimeString("de-DE", {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      )}

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="flex gap-3">
        <div className="relative flex-1">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent disabled:opacity-50 pr-12"
            disabled={isProcessing || !isConnected}
          />
          {/* Character count */}
          {input.length > 100 && (
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-500">
              {input.length}/500
            </span>
          )}
        </div>
        
        <button
          type="submit"
          disabled={isProcessing || !isConnected || !input.trim()}
          className="px-6 py-3 bg-green-600 hover:bg-green-500 disabled:bg-slate-600 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors flex items-center gap-2"
        >
          {isProcessing ? (
            <>
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
              <span className="hidden sm:inline">Analysiere...</span>
            </>
          ) : (
            <>
              <span>Senden</span>
              <kbd className="hidden sm:inline-block text-xs bg-green-700 px-1.5 py-0.5 rounded">↵</kbd>
            </>
          )}
        </button>
      </form>

      {/* Status Hints */}
      {!isConnected && (
        <p className="text-xs text-red-400 mt-2">
          ⚠️ Nicht verbunden. Verbindung wird hergestellt...
        </p>
      )}
      
      {/* Quick Actions */}
      <div className="flex gap-2 mt-3 flex-wrap">
        <QuickAction
          label="BTC Analyse"
          onClick={() => onSendMessage("Analysiere BTC/USDT für einen Swing-Trade")}
          disabled={isProcessing || !isConnected}
        />
        <QuickAction
          label="ETH Analyse"
          onClick={() => onSendMessage("Analysiere ETH/USDT - aktuelle Marktlage und Einstiegspunkte")}
          disabled={isProcessing || !isConnected}
        />
        <QuickAction
          label="AAPL Aktie"
          onClick={() => onSendMessage("Analysiere Apple (AAPL) Aktie für mittelfristigen Trade")}
          disabled={isProcessing || !isConnected}
        />
      </div>
    </div>
  );
}

// Quick action button component
function QuickAction({
  label,
  onClick,
  disabled,
}: {
  label: string;
  onClick: () => void;
  disabled: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="text-xs px-3 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed text-slate-400 hover:text-slate-200 rounded-full transition-colors border border-slate-700"
    >
      {label}
    </button>
  );
}

export default Chat;
