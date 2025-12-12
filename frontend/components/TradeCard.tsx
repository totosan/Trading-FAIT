"use client";

import { TradeRecommendation } from "@/lib/types";

interface TradeCardProps {
  trade: TradeRecommendation;
  onDismiss?: () => void;
}

export function TradeCard({ trade, onDismiss }: TradeCardProps) {
  const isLong = trade.direction === "LONG";
  const directionColor = isLong ? "green" : "red";
  
  // Format entry price
  const formatEntry = () => {
    if (typeof trade.entry === "number") {
      return formatPrice(trade.entry);
    }
    return `${formatPrice(trade.entry.min)} - ${formatPrice(trade.entry.max)}`;
  };

  // Format price with appropriate decimals
  const formatPrice = (price: number) => {
    if (price < 1) return price.toFixed(6);
    if (price < 100) return price.toFixed(4);
    if (price < 10000) return price.toFixed(2);
    return price.toLocaleString("de-DE", { maximumFractionDigits: 2 });
  };

  // Format take profit(s)
  const formatTakeProfit = () => {
    if (Array.isArray(trade.takeProfit)) {
      return trade.takeProfit.map((tp, i) => (
        <span key={i} className="block">
          TP{i + 1}: {formatPrice(tp)}
        </span>
      ));
    }
    return formatPrice(trade.takeProfit);
  };

  // Calculate potential profit/loss percentages
  const entryPrice = typeof trade.entry === "number" 
    ? trade.entry 
    : (trade.entry.min + trade.entry.max) / 2;
  
  const slPercent = ((trade.stopLoss - entryPrice) / entryPrice * 100).toFixed(2);
  const tpPrice = Array.isArray(trade.takeProfit) ? trade.takeProfit[0] : trade.takeProfit;
  const tpPercent = ((tpPrice - entryPrice) / entryPrice * 100).toFixed(2);

  return (
    <div className={`trade-card ${isLong ? "long" : "short"}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="text-lg font-bold text-white">{trade.symbol}</span>
          <span
            className={`px-2 py-0.5 text-xs font-medium rounded ${
              isLong 
                ? "bg-green-900/50 text-green-400" 
                : "bg-red-900/50 text-red-400"
            }`}
          >
            {trade.direction}
          </span>
          {trade.confidence && (
            <span
              className={`px-2 py-0.5 text-xs rounded ${
                trade.confidence === "HIGH"
                  ? "bg-green-900/30 text-green-500"
                  : trade.confidence === "MEDIUM"
                  ? "bg-yellow-900/30 text-yellow-500"
                  : "bg-slate-700 text-slate-400"
              }`}
            >
              {trade.confidence}
            </span>
          )}
        </div>
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="text-slate-500 hover:text-slate-300 transition-colors"
            aria-label="Schließen"
          >
            ✕
          </button>
        )}
      </div>

      {/* Price Levels */}
      <div className="space-y-3">
        {/* Entry */}
        <div className="flex justify-between items-center">
          <span className="text-sm text-slate-400">Einstieg</span>
          <span className="text-sm font-medium text-white">{formatEntry()}</span>
        </div>

        {/* Stop Loss */}
        <div className="flex justify-between items-center">
          <span className="text-sm text-slate-400">Stop Loss</span>
          <div className="text-right">
            <span className="text-sm font-medium text-red-400">
              {formatPrice(trade.stopLoss)}
            </span>
            <span className="text-xs text-red-400/70 ml-2">
              ({slPercent}%)
            </span>
          </div>
        </div>

        {/* Take Profit */}
        <div className="flex justify-between items-center">
          <span className="text-sm text-slate-400">Take Profit</span>
          <div className="text-right">
            <span className="text-sm font-medium text-green-400">
              {formatTakeProfit()}
            </span>
            <span className="text-xs text-green-400/70 ml-2">
              (+{tpPercent}%)
            </span>
          </div>
        </div>

        {/* Risk/Reward */}
        <div className="pt-3 border-t border-slate-700">
          <div className="flex justify-between items-center">
            <span className="text-sm text-slate-400">Risk/Reward</span>
            <span className="text-sm font-bold text-white">{trade.riskReward}</span>
          </div>
        </div>
      </div>

      {/* Validity */}
      {trade.validity && (
        <div className="mt-3 pt-3 border-t border-slate-700">
          <div className="text-xs text-slate-500">
            <span className="text-slate-400">Gültigkeit:</span> {trade.validity}
          </div>
        </div>
      )}

      {/* Reasoning */}
      {trade.reasoning && (
        <div className="mt-3 pt-3 border-t border-slate-700">
          <p className="text-xs text-slate-400 leading-relaxed">
            {trade.reasoning}
          </p>
        </div>
      )}
    </div>
  );
}

// Empty state component
export function TradeCardEmpty() {
  return (
    <div className="trade-card">
      <div className="text-center py-8">
        <div className="text-3xl mb-2">📊</div>
        <p className="text-slate-500">Keine aktive Empfehlung</p>
        <p className="text-xs text-slate-600 mt-2">
          Stelle eine Frage um eine Analyse zu starten
        </p>
      </div>
    </div>
  );
}

export default TradeCard;
