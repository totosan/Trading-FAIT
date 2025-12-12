"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useState } from "react";

interface MarkdownReportProps {
  content: string;
  title?: string;
  collapsible?: boolean;
  defaultExpanded?: boolean;
}

export function MarkdownReport({
  content,
  title = "Analyse Report",
  collapsible = false,
  defaultExpanded = true,
}: MarkdownReportProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  // Clean markdown content (remove code fences if present)
  const cleanContent = content
    .replace(/^```markdown\n?/, "")
    .replace(/\n?```$/, "")
    .trim();

  if (!cleanContent) {
    return (
      <div className="bg-slate-800/30 rounded-lg p-4">
        <h2 className="text-sm font-medium text-slate-400 mb-4">{title}</h2>
        <div className="text-center text-slate-500 py-8">
          <p>Kein Report verfügbar</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-800/30 rounded-lg p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-medium text-slate-400">{title}</h2>
        <div className="flex items-center gap-2">
          {/* Copy Button */}
          <button
            onClick={() => {
              navigator.clipboard.writeText(cleanContent);
            }}
            className="text-xs text-slate-500 hover:text-slate-300 transition-colors px-2 py-1 rounded hover:bg-slate-700"
            title="In Zwischenablage kopieren"
          >
            📋 Kopieren
          </button>
          
          {/* Collapse Button */}
          {collapsible && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-xs text-slate-500 hover:text-slate-300 transition-colors px-2 py-1 rounded hover:bg-slate-700"
            >
              {isExpanded ? "▼ Einklappen" : "▶ Ausklappen"}
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      {(!collapsible || isExpanded) && (
        <div className="markdown-report">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              // Custom table rendering
              table: ({ children }) => (
                <div className="overflow-x-auto my-4">
                  <table className="min-w-full">{children}</table>
                </div>
              ),
              // Custom code block rendering
              code: ({ className, children, ...props }) => {
                const match = /language-(\w+)/.exec(className || "");
                const isInline = !match;
                
                if (isInline) {
                  return (
                    <code className="bg-slate-800 px-1.5 py-0.5 rounded text-green-400 text-xs" {...props}>
                      {children}
                    </code>
                  );
                }
                
                return (
                  <div className="relative">
                    <span className="absolute top-2 right-2 text-xs text-slate-500">
                      {match[1]}
                    </span>
                    <pre className="bg-slate-900 p-4 rounded-lg overflow-x-auto">
                      <code className={className} {...props}>
                        {children}
                      </code>
                    </pre>
                  </div>
                );
              },
              // Custom link rendering
              a: ({ href, children }) => (
                <a
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-400 hover:text-blue-300 underline"
                >
                  {children}
                </a>
              ),
              // Highlight trade-relevant keywords
              strong: ({ children }) => (
                <strong className="text-white font-semibold">{children}</strong>
              ),
            }}
          >
            {cleanContent}
          </ReactMarkdown>
        </div>
      )}
    </div>
  );
}

// Loading state component
export function MarkdownReportLoading() {
  return (
    <div className="bg-slate-800/30 rounded-lg p-4">
      <h2 className="text-sm font-medium text-slate-400 mb-4">Analyse Report</h2>
      <div className="space-y-3 animate-pulse">
        <div className="h-4 bg-slate-700 rounded w-3/4"></div>
        <div className="h-4 bg-slate-700 rounded w-1/2"></div>
        <div className="h-4 bg-slate-700 rounded w-5/6"></div>
        <div className="h-20 bg-slate-700 rounded w-full mt-4"></div>
        <div className="h-4 bg-slate-700 rounded w-2/3"></div>
      </div>
    </div>
  );
}

export default MarkdownReport;
