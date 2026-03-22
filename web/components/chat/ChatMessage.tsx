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
      <div className={`flex max-w-[92%] gap-2 sm:max-w-[80%] sm:gap-3 min-w-0 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
        {/* Avatar */}
        <div
          className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-medium sm:h-8 sm:w-8 sm:text-sm ${
            isUser
              ? "bg-surface-container-highest text-on-surface"
              : "message-gradient text-white"
          }`}
        >
          {isUser ? "你" : "AI"}
        </div>

        {/* Message content: user = plain text, AI = interleaved markdown + cards */}
        {isUser ? (
          <div className="flex min-w-0 flex-col gap-3">
            <div className="message-gradient rounded-2xl rounded-tr-sm px-4 py-3 text-sm leading-relaxed text-white shadow-lg shadow-primary/10 sm:px-5 sm:py-3.5">
              <p className="whitespace-pre-wrap break-words font-medium">{message.content}</p>
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
