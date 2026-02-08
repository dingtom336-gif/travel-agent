"use client";

import { useState, useEffect, useRef } from "react";
import { ThinkingStep } from "@/lib/types";

interface ThinkingStepsProps {
  steps: ThinkingStep[];
  isStreaming: boolean;
}

// Agent display names (migrated from AgentStatus.tsx)
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

// Agent colors for visual distinction
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
 * Claude-style collapsible thinking steps panel.
 * Collapsed: one-line summary with chevron.
 * Expanded: full list of agent steps with spinner/checkmark.
 */
export default function ThinkingSteps({ steps, isStreaming }: ThinkingStepsProps) {
  const [isOpen, setIsOpen] = useState(true);
  const userToggled = useRef(false);

  // Auto-collapse after streaming ends (unless user manually toggled)
  useEffect(() => {
    if (!isStreaming && steps.length > 0 && !userToggled.current) {
      const timer = setTimeout(() => setIsOpen(false), 800);
      return () => clearTimeout(timer);
    }
  }, [isStreaming, steps.length]);

  // Auto-expand when streaming starts
  useEffect(() => {
    if (isStreaming && !userToggled.current) {
      setIsOpen(true);
    }
  }, [isStreaming]);

  if (steps.length === 0) return null;

  const runningSteps = steps.filter((s) => s.status === "running");
  const doneCount = steps.filter((s) => s.status === "done").length;

  // Collapsed summary text
  const summaryText = isStreaming && runningSteps.length > 0
    ? `${agentDisplayNames[runningSteps[runningSteps.length - 1].agent] || runningSteps[runningSteps.length - 1].agent} ${runningSteps[runningSteps.length - 1].task}`
    : `已完成 ${doneCount} 个推理步骤`;

  const handleToggle = () => {
    userToggled.current = true;
    setIsOpen((prev) => !prev);
  };

  return (
    <div className="mb-2">
      {/* Collapsed header bar */}
      <button
        onClick={handleToggle}
        className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left transition-colors hover:bg-amber-500/5"
      >
        {/* Icon: spinner when streaming, sparkle when done */}
        {isStreaming && runningSteps.length > 0 ? (
          <svg
            className="h-3.5 w-3.5 shrink-0 animate-spin text-amber-500"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        ) : (
          <svg
            className="h-3.5 w-3.5 shrink-0 text-amber-500"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth="2"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
          </svg>
        )}

        {/* Summary text */}
        <span className="flex-1 truncate text-xs font-medium text-amber-600 dark:text-amber-400">
          {summaryText}
        </span>

        {/* Chevron */}
        <svg
          className={`h-3.5 w-3.5 shrink-0 text-amber-500/60 transition-transform duration-200 ${
            isOpen ? "rotate-90" : ""
          }`}
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth="2.5"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
        </svg>
      </button>

      {/* Expanded step list */}
      {isOpen && (
        <div className="mt-1 space-y-1 border-l-2 border-amber-500/20 pl-3 ml-2">
          {steps.map((step, i) => (
            <div
              key={`${step.agent}-${i}`}
              className="flex items-center gap-2 py-0.5 text-xs animate-fade-in"
            >
              {/* Status icon */}
              {step.status === "running" ? (
                <svg
                  className={`h-3.5 w-3.5 shrink-0 animate-spin ${agentColors[step.agent] || "text-primary"}`}
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
              ) : step.status === "done" ? (
                <svg
                  className="h-3.5 w-3.5 shrink-0 text-green-500"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth="2"
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
              ) : (
                <svg
                  className="h-3.5 w-3.5 shrink-0 text-red-500"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth="2"
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                </svg>
              )}

              {/* Agent name */}
              <span className={`font-medium ${agentColors[step.agent] || "text-primary"}`}>
                {agentDisplayNames[step.agent] || step.agent}
              </span>

              {/* Task description */}
              <span className="text-muted-foreground truncate">{step.task}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
