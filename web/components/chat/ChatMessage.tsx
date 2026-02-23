"use client";

import { memo } from "react";
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
      <div className={`flex max-w-[92%] gap-2 sm:max-w-[75%] sm:gap-3 min-w-0 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
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

        {/* Message content: user = plain text, AI = interleaved markdown + cards */}
        {isUser ? (
          <div className="flex min-w-0 flex-col gap-3">
            <div className="rounded-2xl px-3 py-2.5 text-sm leading-relaxed bg-bubble-user text-white sm:px-4 sm:py-3">
              <p className="whitespace-pre-wrap break-words">{message.content}</p>
            </div>
          </div>
        ) : (
          <InterleavedContent
            content={message.content}
            uiPayloads={message.uiPayloads}
            thinkingSteps={message.thinkingSteps}
            isStreaming={!!message.isStreaming}
          />
        )}
      </div>
    </div>
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
