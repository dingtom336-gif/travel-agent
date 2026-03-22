"use client";

import { AgentStatus as AgentStatusType } from "@/lib/types";

interface AgentStatusProps {
  statuses: AgentStatusType[];
}

// Map agent names to Chinese display names
const agentDisplayNames: Record<string, string> = {
  orchestrator: "主控大脑",
  transport: "交通专家",
  hotel: "住宿专家",
  poi: "目的地专家",
  itinerary: "行程编排师",
  budget: "预算管家",
  knowledge: "知识顾问",
  weather: "天气助手",
  customer_service: "客服专家",
};

// Agent colors — unified to primary/secondary for Aurora theme
const agentColors: Record<string, string> = {
  orchestrator: "text-primary",
  transport: "text-primary",
  hotel: "text-secondary",
  poi: "text-primary",
  itinerary: "text-secondary",
  budget: "text-primary",
  knowledge: "text-secondary",
  weather: "text-primary",
  customer_service: "text-secondary",
};

/**
 * Display a list of agent thinking/processing statuses with animations.
 */
export default function AgentStatus({ statuses }: AgentStatusProps) {
  if (statuses.length === 0) return null;

  return (
    <div className="flex w-full justify-start animate-fade-in" role="status" aria-live="polite">
      <div className="flex max-w-[85%] gap-3 sm:max-w-[75%]">
        {/* AI Avatar */}
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full message-gradient text-sm font-medium text-white" aria-hidden="true">
          AI
        </div>

        {/* Status list */}
        <div className="min-w-0 space-y-2 rounded-2xl glass-panel ghost-border px-3 py-2.5 sm:px-4 sm:py-3">
          {statuses.map((status, index) => (
            <div
              key={`${status.agent}-${index}`}
              className="flex min-w-0 items-center gap-2 text-sm"
            >
              {/* Pulsing dot or checkmark */}
              {status.status === "running" ? (
                <div className="h-2 w-2 shrink-0 rounded-full bg-primary animate-aurora-pulse" aria-hidden="true" />
              ) : status.status === "done" ? (
                <svg
                  className="h-4 w-4 text-primary"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth="2"
                  stroke="currentColor"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              ) : (
                <svg
                  className="h-4 w-4 text-error"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth="2"
                  stroke="currentColor"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"
                  />
                </svg>
              )}

              {/* Agent name + task */}
              <span className={`shrink-0 font-medium ${agentColors[status.agent] || "text-primary"}`}>
                {agentDisplayNames[status.agent] || status.agent}
              </span>
              <span className="truncate text-on-surface-variant">{status.task}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
