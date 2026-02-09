"use client";

import { useRef, useEffect, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { useTravelPlan } from "@/lib/travel-context";
import { useChatMessages } from "@/lib/hooks/useChatMessages";
import ChatMessage from "./ChatMessage";
import ChatInput from "./ChatInput";
import EmptyState from "./EmptyState";
import ConnectionBanner from "./ConnectionBanner";

export default function ChatContainer() {
  const searchParams = useSearchParams();
  const { dispatch: travelDispatch } = useTravelPlan();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const initialPromptHandled = useRef(false);

  const { messages, isProcessing, connectionState, handleSend, cleanup } = useChatMessages({
    travelDispatch,
  });

  // Auto-scroll to bottom when messages change
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Handle initial prompt from URL query parameter
  useEffect(() => {
    if (initialPromptHandled.current) return;
    const q = searchParams.get("q");
    if (q) {
      initialPromptHandled.current = true;
      const timer = setTimeout(() => {
        handleSend(q);
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [searchParams, handleSend]);

  // Cleanup abort controller on unmount
  useEffect(() => {
    return () => {
      cleanup();
    };
  }, [cleanup]);

  return (
    <div className="flex h-full flex-col">
      {/* Connection status banner */}
      <ConnectionBanner state={connectionState} />

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="mx-auto max-w-4xl space-y-6">
          {messages.length === 0 && <EmptyState />}

          {messages.map((msg) => (
            <ChatMessage key={msg.id} message={msg} />
          ))}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input area */}
      <ChatInput onSend={handleSend} disabled={isProcessing} />
    </div>
  );
}
