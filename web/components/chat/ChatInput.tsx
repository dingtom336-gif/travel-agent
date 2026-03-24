"use client";

import { useState, useRef, useEffect } from "react";
import DeepReasoningToggle from "./DeepReasoningToggle";
import { useDeepReasoning } from "@/lib/hooks/useDeepReasoning";

interface ChatInputProps {
  onSend: (message: string, deepReasoning: boolean) => void;
  disabled?: boolean;
  placeholder?: string;
}

/**
 * Chat input component with auto-resize textarea, deep reasoning toggle, and send button.
 */
export default function ChatInput({
  onSend,
  disabled = false,
  placeholder = "输入你的旅行需求...",
}: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [deepReasoning, setDeepReasoning] = useDeepReasoning();

  // Auto-resize textarea height based on content
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = `${Math.min(textarea.scrollHeight, 150)}px`;
    }
  }, [value]);

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed, deepReasoning);
    setValue("");
    // Reset height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="glass-panel border-t border-white/[0.08] p-4 sm:p-6 safe-bottom">
      {/* Toolbar row with deep reasoning toggle */}
      <div className="mx-auto max-w-4xl mb-2 flex items-center">
        <DeepReasoningToggle
          enabled={deepReasoning}
          onChange={setDeepReasoning}
        />
      </div>

      <div className="mx-auto flex max-w-4xl items-end gap-3">
        <div className="glass-panel ghost-border flex flex-1 items-end rounded-3xl px-4 py-2 transition-all focus-within:border-primary/30 focus-within:shadow-[0_0_15px_rgba(83,221,252,0.1)]">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            aria-label="输入你的旅行需求"
            className="max-h-[150px] w-full resize-none bg-transparent py-1.5 text-sm text-on-surface placeholder:text-on-surface-variant/50 focus:outline-none disabled:opacity-50"
          />
        </div>

        <button
          onPointerDown={(e) => {
            e.preventDefault();
            handleSubmit();
          }}
          className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl message-gradient text-white transition-all hover:shadow-[0_0_20px_rgba(83,221,252,0.3)] active:scale-90 touch-manipulation ${(disabled || !value.trim()) ? "opacity-40" : ""}`}
          aria-label="Send message"
        >
          {disabled ? (
            <svg className="h-5 w-5 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
          ) : (
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth="2.5" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 10.5L12 3m0 0l7.5 7.5M12 3v18" />
            </svg>
          )}
        </button>
      </div>

      <p className="mx-auto mt-2.5 max-w-4xl text-center text-xs text-on-surface-variant/50 hidden sm:block">
        按 Enter 发送，Shift + Enter 换行
      </p>
    </div>
  );
}
