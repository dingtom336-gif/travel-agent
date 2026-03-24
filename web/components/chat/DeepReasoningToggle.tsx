"use client";

import React from "react";

interface DeepReasoningToggleProps {
  enabled: boolean;
  onChange: (enabled: boolean) => void;
  compact?: boolean;
}

export default function DeepReasoningToggle({
  enabled,
  onChange,
  compact = false,
}: DeepReasoningToggleProps) {
  return (
    <button
      type="button"
      onClick={() => onChange(!enabled)}
      className={`
        flex items-center gap-1.5 rounded-full px-3 py-1.5
        text-xs font-medium transition-all duration-200 select-none
        ${enabled
          ? "border border-[#53ddfc]/50 bg-[#53ddfc]/10 text-[#53ddfc] shadow-[0_0_12px_rgba(83,221,252,0.25)]"
          : "border border-white/[0.08] bg-white/[0.03] text-white/40 hover:text-white/60 hover:border-white/[0.15]"
        }
        ${compact ? "px-2 py-1" : ""}
      `}
      title={enabled ? "深度推理已开启（ReAct 模式）" : "点击开启深度推理"}
    >
      <svg
        width={compact ? 14 : 16}
        height={compact ? 14 : 16}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M12 2a7 7 0 0 1 7 7c0 2.38-1.19 4.47-3 5.74V17a1 1 0 0 1-1 1H9a1 1 0 0 1-1-1v-2.26C6.19 13.47 5 11.38 5 9a7 7 0 0 1 7-7z" />
        <path d="M9 21h6" />
        <path d="M10 21v1a1 1 0 0 0 1 1h2a1 1 0 0 0 1-1v-1" />
        {enabled && (
          <>
            <line x1="12" y1="6" x2="12" y2="10" opacity="0.6" />
            <line x1="10" y1="8" x2="14" y2="8" opacity="0.6" />
          </>
        )}
      </svg>
      {!compact && <span>深度推理</span>}
    </button>
  );
}
