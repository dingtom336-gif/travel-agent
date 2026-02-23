"use client";

import { useRef, useEffect, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { useTravelPlan } from "@/lib/travel-context";
import { useChatMessages } from "@/lib/hooks/useChatMessages";
import { useAutoScroll } from "@/lib/hooks/useAutoScroll";
import ChatMessage from "./ChatMessage";
import ChatInput from "./ChatInput";
import EmptyState from "./EmptyState";
import ConnectionBanner from "./ConnectionBanner";

export default function ChatContainer() {
  const searchParams = useSearchParams();
  const { dispatch: travelDispatch } = useTravelPlan();
  const initialPromptHandled = useRef(false);

  const { messages, isProcessing, connectionState, handleSend, cleanup } = useChatMessages({
    travelDispatch,
  });

  const {
    scrollContainerRef,
    messagesEndRef,
    handleScroll,
    scrollToBottom,
    forceScrollOnNext,
    showScrollBtn,
  } = useAutoScroll([messages]);

  // Wrap handleSend to force scroll when user sends a message
  const handleSendWithScroll = useCallback(
    (text: string) => {
      forceScrollOnNext();
      handleSend(text);
    },
    [forceScrollOnNext, handleSend]
  );

  // Handle initial prompt from URL query parameter
  useEffect(() => {
    if (initialPromptHandled.current) return;
    const q = searchParams.get("q");
    if (q) {
      initialPromptHandled.current = true;
      const timer = setTimeout(() => {
        forceScrollOnNext();
        handleSend(q);
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [searchParams, handleSend, forceScrollOnNext]);

  // Cleanup abort controller on unmount
  useEffect(() => {
    return () => { cleanup(); };
  }, [cleanup]);

  return (
    <div className="flex h-full flex-col">
      <ConnectionBanner state={connectionState} />

      {/* Messages area with scroll tracking */}
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="relative flex-1 overflow-y-auto overflow-x-hidden px-3 py-4 sm:px-4 sm:py-6"
      >
        <div className="mx-auto max-w-4xl space-y-6">
          {messages.length === 0 && <EmptyState />}
          {messages.map((msg) => (
            <ChatMessage key={msg.id} message={msg} />
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Scroll-to-bottom floating button */}
        {showScrollBtn && (
          <button
            onClick={() => scrollToBottom("smooth")}
            className="sticky bottom-4 left-1/2 z-10 flex h-10 w-10 -translate-x-1/2 items-center justify-center rounded-full bg-primary text-white shadow-lg transition-opacity hover:opacity-90"
            aria-label="滚动到底部"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
            </svg>
          </button>
        )}
      </div>

      <ChatInput onSend={handleSendWithScroll} disabled={isProcessing} />
    </div>
  );
}
