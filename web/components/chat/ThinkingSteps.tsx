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
 * Claude-style collapsible thinking steps panel.
 * Collapsed: one-line summary with chevron.
 * Expanded: full list of agent steps with spinner/checkmark.
 */
export default function ThinkingSteps({ steps, isStreaming }: ThinkingStepsProps) {
  const [isOpen, setIsOpen] = useState(isStreaming);
  const userToggled = useRef(false);

  // Auto-collapse after streaming ends (unless user manually toggled)
  useEffect(() => {
    if (!isStreaming && steps.length > 0 && !userToggled.current) {
      const timer = setTimeout(() => setIsOpen(false), 800);
      return () => clearTimeout(timer);
    }
    if (isStreaming && !userToggled.current) {
      setIsOpen(true);
    }
  }, [isStreaming, steps.length]);

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
        className="flex w-full items-center gap-2 rounded-xl bg-surface-container-low ghost-border px-3 py-2 text-left transition-colors hover:bg-surface-container-high/50"
      >
        {/* Icon: pulsing dot when streaming, sparkle when done */}
        {isStreaming && runningSteps.length > 0 ? (
          <div className="h-2 w-2 shrink-0 rounded-full bg-primary animate-aurora-pulse" />
        ) : (
          <svg
            className="h-3.5 w-3.5 shrink-0 text-primary"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth="2"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
          </svg>
        )}

        {/* Summary text */}
        <span className="flex-1 truncate text-xs font-medium text-primary">
          {summaryText}
        </span>

        {/* Chevron */}
        <svg
          className={`h-3.5 w-3.5 shrink-0 text-on-surface-variant transition-transform duration-200 ${
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
        <div className="mt-1.5 space-y-1 border-l border-primary/20 pl-3 ml-3">
          {steps.map((step, i) => (
            <div
              key={`${step.agent}-${i}`}
              className="flex items-center gap-2 py-0.5 text-xs animate-fade-in"
            >
              {/* Status icon */}
              {step.status === "running" ? (
                <div className="h-1.5 w-1.5 shrink-0 rounded-full bg-primary animate-aurora-pulse" />
              ) : step.status === "done" ? (
                <svg
                  className="h-3.5 w-3.5 shrink-0 text-primary"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth="2"
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
              ) : (
                <svg
                  className="h-3.5 w-3.5 shrink-0 text-error"
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
              <span className="text-on-surface-variant truncate">{step.task}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
