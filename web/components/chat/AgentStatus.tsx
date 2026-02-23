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

// Map agent names to icon colors
const agentColors: Record<string, string> = {
  orchestrator: "text-blue-500",
  transport: "text-sky-500",
  hotel: "text-purple-500",
  poi: "text-green-500",
  itinerary: "text-orange-500",
  budget: "text-yellow-500",
  knowledge: "text-indigo-500",
  weather: "text-cyan-500",
  customer_service: "text-pink-500",
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
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-blue-400 to-cyan-400 text-sm font-medium text-white" aria-hidden="true">
          AI
        </div>

        {/* Status list */}
        <div className="min-w-0 space-y-2 rounded-2xl bg-bubble-ai px-3 py-2.5 sm:px-4 sm:py-3">
          {statuses.map((status, index) => (
            <div
              key={`${status.agent}-${index}`}
              className="flex min-w-0 items-center gap-2 text-sm"
            >
              {/* Spinner or checkmark */}
              {status.status === "running" ? (
                <svg
                  className={`h-4 w-4 animate-spin ${agentColors[status.agent] || "text-primary"}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
              ) : status.status === "done" ? (
                <svg
                  className="h-4 w-4 text-green-500"
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
                  className="h-4 w-4 text-red-500"
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
              <span className="truncate text-muted-foreground">{status.task}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
