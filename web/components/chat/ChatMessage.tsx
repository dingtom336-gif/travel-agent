"use client";

import { memo, useState, useCallback } from "react";
import { ChatMessage as ChatMessageType } from "@/lib/types";
import InterleavedContent from "./InterleavedContent";

interface ChatMessageProps {
  message: ChatMessageType;
}

/**
 * Render a single chat message bubble.
 * User messages: right-aligned, blue bubble.
 * Assistant messages: left-aligned, gray bubble with rich markdown support.
 */
function ChatMessageRaw({ message }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={`flex w-full animate-fade-in ${
        isUser ? "justify-end" : "justify-start"
      }`}
    >
      <div className={`flex max-w-[92%] gap-2 sm:max-w-[75%] sm:gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
        {/* Avatar */}
        <div
          className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-medium sm:h-8 sm:w-8 sm:text-sm ${
            isUser
              ? "bg-primary text-white"
              : "bg-gradient-to-br from-blue-400 to-cyan-400 text-white"
          }`}
        >
          {isUser ? "你" : "AI"}
        </div>

        {/* Message content */}
        {isUser ? (
          <div className="flex flex-col gap-3">
            <div className="rounded-2xl px-4 py-3 text-sm leading-relaxed bg-bubble-user text-white">
              <p className="whitespace-pre-wrap">{message.content}</p>
            </div>
          </div>
        ) : (
          <div className="group/msg flex flex-col gap-1">
            <InterleavedContent
              content={message.content}
              uiPayloads={message.uiPayloads}
              thinkingSteps={message.thinkingSteps}
              isStreaming={!!message.isStreaming}
            />
            {/* Copy button: visible on hover (desktop) or tap area (mobile) */}
            {!message.isStreaming && message.content.trim() && (
              <CopyButton text={message.content} />
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Copy-to-clipboard button for AI responses.
 */
function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [text]);

  return (
    <button
      onPointerDown={(e) => {
        e.preventDefault();
        handleCopy();
      }}
      className="mt-0.5 inline-flex items-center gap-1 self-start rounded-md px-1.5 py-1 text-[11px] text-muted-foreground opacity-60 transition-opacity hover:bg-muted hover:text-foreground touch-manipulation sm:opacity-0 sm:group-hover/msg:opacity-100"
      aria-label="复制回答"
    >
      {copied ? (
        <>
          <svg className="h-3 w-3 text-green-500" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
          </svg>
          <span className="text-green-500">已复制</span>
        </>
      ) : (
        <>
          <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9.75a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" />
          </svg>
          <span>复制</span>
        </>
      )}
    </button>
  );
}

const ChatMessage = memo(ChatMessageRaw, (prev, next) => {
  const pm = prev.message;
  const nm = next.message;
  return (
    pm.id === nm.id &&
    pm.content.length === nm.content.length &&
    pm.isStreaming === nm.isStreaming
  );
});

export default ChatMessage;
