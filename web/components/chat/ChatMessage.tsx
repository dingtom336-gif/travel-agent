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
      <div className={`flex max-w-[85%] gap-3 sm:max-w-[75%] ${isUser ? "flex-row-reverse" : "flex-row"}`}>
        {/* Avatar */}
        <div
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-medium ${
            isUser
              ? "bg-primary text-white"
              : "bg-gradient-to-br from-blue-400 to-cyan-400 text-white"
          }`}
        >
          {isUser ? "你" : "AI"}
        </div>

        {/* Message content: user = plain text, AI = interleaved markdown + cards */}
        {isUser ? (
          <div className="flex flex-col gap-3">
            <div className="rounded-2xl px-4 py-3 text-sm leading-relaxed bg-bubble-user text-white">
              <p className="whitespace-pre-wrap">{message.content}</p>
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
