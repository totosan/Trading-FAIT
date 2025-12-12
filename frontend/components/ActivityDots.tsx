"use client";

import { AgentName } from "@/lib/types";

interface AgentDot {
  id: string;
  name: AgentName;
  label: string;
  active: boolean;
}

interface ActivityDotsProps {
  agentStatuses: Record<string, boolean>;
  showLabels?: boolean;
}

const AGENTS: Omit<AgentDot, "active">[] = [
  { id: "market", name: "MarketAnalyst", label: "Markt" },
  { id: "news", name: "NewsResearcher", label: "News" },
  { id: "chart", name: "ChartConfigurator", label: "Chart" },
  { id: "report", name: "ReportWriter", label: "Report" },
  { id: "indicator", name: "IndicatorCoder", label: "Indikator" },
  { id: "executor", name: "CodeExecutor", label: "Code" },
];

export function ActivityDots({ agentStatuses, showLabels = false }: ActivityDotsProps) {
  const agents: AgentDot[] = AGENTS.map((agent) => ({
    ...agent,
    active: agentStatuses[agent.name] || false,
  }));

  const activeCount = agents.filter((a) => a.active).length;

  return (
    <div className="flex items-center gap-2 px-4 py-2 bg-slate-800/50 rounded-lg">
      <span className="text-xs text-slate-500 mr-2">
        Agenten{activeCount > 0 && ` (${activeCount})`}:
      </span>
      <div className="flex items-center gap-2">
        {agents.map((agent) => (
          <div key={agent.id} className="relative group">
            <div
              className={`agent-dot ${agent.active ? "active" : ""}`}
              aria-label={agent.name}
            />
            {/* Tooltip */}
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-slate-900 text-xs text-slate-300 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10">
              {agent.name}
              {agent.active && (
                <span className="ml-1 text-green-400">●</span>
              )}
            </div>
            {showLabels && (
              <span className="text-[10px] text-slate-500 mt-0.5 block text-center">
                {agent.label}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default ActivityDots;
