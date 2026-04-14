"use client";


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
          ? "border border-primary/50 bg-primary/10 text-primary shadow-[0_0_12px_rgba(var(--primary),0.15)]"
          : "ghost-border text-on-surface-variant/50 hover:text-on-surface-variant hover:border-outline-variant"
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
