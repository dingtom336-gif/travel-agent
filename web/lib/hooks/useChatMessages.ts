"use client";

import { useState, useRef, useCallback, type Dispatch } from "react";
import type {
  ChatMessage,
  AgentStatus as AgentStatusType,
} from "@/lib/types";
import { chatStream } from "@/lib/api-client";
import type { Action } from "@/lib/travel-context";
import { mockStreamResponse } from "@/components/chat/mockStream";
import { useSSEHandler } from "./useSSEHandler";

// Toggle this to true to use mock data when backend is unavailable
const USE_MOCK = false;

// Generate unique ID for messages
function generateId(): string {
  return `msg_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

interface UseChatMessagesOptions {
  travelDispatch: Dispatch<Action>;
}

export function useChatMessages({ travelDispatch }: UseChatMessagesOptions) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const sessionIdRef = useRef<string | undefined>(undefined);

  const { handleSSEEvent, upsertThinkingStep, appendText, finishMessage } =
    useSSEHandler({
      setMessages,
      setIsProcessing,
      sessionIdRef,
      travelDispatch,
    });

  // Send message via real backend SSE stream
  const sendViaBackend = useCallback(
    async (text: string, aiMsgId: string, signal: AbortSignal) => {
      try {
        await chatStream(
          {
            session_id: sessionIdRef.current,
            message: text,
          },
          (event) => handleSSEEvent(event, aiMsgId),
          signal
        );
      } catch {
        finishMessage(aiMsgId);
      }
    },
    [handleSSEEvent, finishMessage]
  );

  // Send message via mock stream
  const sendViaMock = useCallback(
    async (text: string, aiMsgId: string, signal: AbortSignal) => {
      const mockUpsert = (status: AgentStatusType) => {
        upsertThinkingStep(aiMsgId, {
          ...status,
          timestamp: Date.now(),
        });
      };
      try {
        await mockStreamResponse(
          text,
          mockUpsert,
          (chunk) => appendText(aiMsgId, chunk),
          () => finishMessage(aiMsgId),
          signal
        );
      } catch {
        finishMessage(aiMsgId);
      }
    },
    [upsertThinkingStep, appendText, finishMessage]
  );

  // Handle sending a message
  const handleSend = useCallback(
    async (text: string) => {
      if (isProcessing) return;

      const userMsg: ChatMessage = {
        id: generateId(),
        role: "user",
        content: text,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setIsProcessing(true);
      travelDispatch({ type: "RESET" });

      const controller = new AbortController();
      abortControllerRef.current = controller;

      const aiMsgId = generateId();
      const aiMsg: ChatMessage = {
        id: aiMsgId,
        role: "assistant",
        content: "",
        timestamp: new Date(),
        isStreaming: true,
      };
      setMessages((prev) => [...prev, aiMsg]);

      if (USE_MOCK) {
        await sendViaMock(text, aiMsgId, controller.signal);
      } else {
        await sendViaBackend(text, aiMsgId, controller.signal);
      }
    },
    [isProcessing, sendViaBackend, sendViaMock, travelDispatch]
  );

  // Cleanup: abort in-flight requests
  const cleanup = useCallback(() => {
    abortControllerRef.current?.abort();
  }, []);

  return { messages, isProcessing, handleSend, cleanup };
}
