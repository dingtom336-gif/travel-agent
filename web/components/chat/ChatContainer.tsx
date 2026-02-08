"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import {
  ChatMessage as ChatMessageType,
  AgentStatus as AgentStatusType,
  ThinkingStep,
  UIPayload,
  SSEEvent,
  FlightData,
  HotelData,
  POIData,
  WeatherData,
  TimelineDayData,
  BudgetSummary,
} from "@/lib/types";
import { chatStream } from "@/lib/api-client";
import { useTravelPlan } from "@/lib/travel-context";
import { mockStreamResponse } from "./mockStream";
import ChatMessage from "./ChatMessage";
import ChatInput from "./ChatInput";

// Toggle this to true to use mock data when backend is unavailable
const USE_MOCK = false;

// Generate unique ID for messages
function generateId(): string {
  return `msg_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

export default function ChatContainer() {
  const searchParams = useSearchParams();
  const { dispatch: travelDispatch } = useTravelPlan();
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const initialPromptHandled = useRef(false);
  // Persist session_id across messages for multi-turn conversation
  const sessionIdRef = useRef<string | undefined>(undefined);

  // Auto-scroll to bottom when messages change
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Upsert a thinking step into a specific AI message
  const upsertThinkingStep = useCallback((msgId: string, step: ThinkingStep) => {
    setMessages((prev) =>
      prev.map((msg) => {
        if (msg.id !== msgId) return msg;
        const steps = msg.thinkingSteps || [];
        const existing = steps.findIndex(
          (s) => s.agent === step.agent && s.task === step.task
        );
        if (existing >= 0) {
          const updated = [...steps];
          updated[existing] = step;
          return { ...msg, thinkingSteps: updated };
        }
        return { ...msg, thinkingSteps: [...steps, step] };
      })
    );
  }, []);

  // Append text content to a streaming AI message
  const appendText = useCallback((msgId: string, chunk: string) => {
    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === msgId
          ? { ...msg, content: msg.content + chunk }
          : msg
      )
    );
  }, []);

  // Append a UI payload to a streaming AI message
  const appendUIPayload = useCallback((msgId: string, payload: UIPayload) => {
    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === msgId
          ? { ...msg, uiPayloads: [...(msg.uiPayloads || []), payload] }
          : msg
      )
    );
  }, []);

  // Mark a message as done streaming
  const finishMessage = useCallback((msgId: string) => {
    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === msgId ? { ...msg, isStreaming: false } : msg
      )
    );
    setIsProcessing(false);
  }, []);

  // Dispatch structured agent data to travel plan context
  const dispatchAgentData = useCallback(
    (agentName: string, resultData: Record<string, unknown>) => {
      const toolData = resultData.tool_data as Record<string, unknown> | undefined;
      if (!toolData) return;

      try {
        if (agentName === "transport") {
          const transit = toolData.transit as Record<string, unknown> | undefined;
          const flightsObj = transit || (toolData.flights as Record<string, unknown> | undefined);
          const results = (flightsObj?.results as FlightData[]) || [];
          if (results.length > 0) {
            travelDispatch({ type: "ADD_FLIGHTS", payload: results.slice(0, 3) as FlightData[] });
          }
        } else if (agentName === "hotel") {
          const hotelsObj = toolData.hotels as Record<string, unknown> | undefined;
          const results = (hotelsObj?.results as HotelData[]) || [];
          if (results.length > 0) {
            travelDispatch({ type: "ADD_HOTELS", payload: results.slice(0, 3) as HotelData[] });
          }
        } else if (agentName === "poi") {
          const poisObj = toolData.pois as Record<string, unknown> | undefined;
          const results = (poisObj?.results as POIData[]) || [];
          if (results.length > 0) {
            travelDispatch({ type: "ADD_POIS", payload: results.slice(0, 4) as POIData[] });
          }
        } else if (agentName === "weather") {
          const forecastObj = toolData.forecast as Record<string, unknown> | undefined;
          const forecasts = (forecastObj?.forecast as WeatherData[]) || [];
          if (forecasts.length > 0) {
            travelDispatch({ type: "SET_WEATHER", payload: forecasts.slice(0, 5) as WeatherData[] });
          }
        } else if (agentName === "itinerary") {
          const itinObj = toolData.optimized_itinerary as Record<string, unknown> | undefined;
          const days = (itinObj?.days as TimelineDayData[]) || [];
          if (days.length > 0) {
            travelDispatch({ type: "SET_ITINERARY", payload: days as TimelineDayData[] });
          }
        } else if (agentName === "budget") {
          const allocObj = toolData.budget_allocation as Record<string, unknown> | undefined;
          if (allocObj) {
            travelDispatch({ type: "SET_BUDGET", payload: allocObj as unknown as BudgetSummary });
          }
        }
      } catch {
        // Silently ignore malformed data
      }
    },
    [travelDispatch]
  );

  // Handle SSE events from the real backend
  const handleSSEEvent = useCallback(
    (event: SSEEvent, aiMsgId: string) => {
      const { type, data } = event;

      switch (type) {
        case "thinking": {
          // Show orchestrator thinking process as a thinking step
          const thought = (data.thought as string) || "正在思考...";
          upsertThinkingStep(aiMsgId, {
            agent: (data.agent as string) || "orchestrator",
            task: thought,
            status: "running",
            timestamp: Date.now(),
          });
          break;
        }

        case "agent_start": {
          // A sub-agent starts working
          upsertThinkingStep(aiMsgId, {
            agent: (data.agent as string) || "unknown",
            task: (data.task as string) || "处理中...",
            status: "running",
            timestamp: Date.now(),
          });
          break;
        }

        case "agent_result": {
          // A sub-agent finished
          const agentName = (data.agent as string) || "unknown";
          upsertThinkingStep(aiMsgId, {
            agent: agentName,
            task: (data.task as string) || (data.summary as string) || "完成",
            status: (data.status as string) === "failed" ? "error" : "done",
            timestamp: Date.now(),
          });

          // Extract structured data and dispatch to travel context
          const resultData = data.data as Record<string, unknown> | undefined;
          if (resultData) {
            dispatchAgentData(agentName, resultData);
          }
          break;
        }

        case "text": {
          // Incremental text content
          const content = (data.content as string) || "";
          if (content) {
            appendText(aiMsgId, content);
          }
          break;
        }

        case "ui_component": {
          // A rich UI card to render
          const payload: UIPayload = {
            type: data.type as UIPayload["type"],
            data: (data.data as Record<string, unknown>) || data,
            status: (data.status as UIPayload["status"]) || "loaded",
          };
          appendUIPayload(aiMsgId, payload);
          break;
        }

        case "done": {
          // Stream finished; save session_id for future messages
          if (data.session_id) {
            const sid = data.session_id as string;
            sessionIdRef.current = sid;
            travelDispatch({
              type: "SET_SESSION",
              payload: { sessionId: sid },
            });
          }
          finishMessage(aiMsgId);
          break;
        }

        case "error": {
          // Show error in the message content
          const errMsg =
            (data.message as string) ||
            (data.error as string) ||
            "发生错误，请重试";
          appendText(aiMsgId, `\n\n**错误**: ${errMsg}`);
          finishMessage(aiMsgId);
          break;
        }

        default:
          break;
      }
    },
    [upsertThinkingStep, appendText, appendUIPayload, finishMessage, dispatchAgentData, travelDispatch]
  );

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
      // Wrap upsertThinkingStep to match mockStream's AgentStatus callback
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

  // Handle sending a message (both user-initiated and auto from URL param)
  const handleSend = useCallback(
    async (text: string) => {
      if (isProcessing) return;

      // Add user message
      const userMsg: ChatMessageType = {
        id: generateId(),
        role: "user",
        content: text,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setIsProcessing(true);
      travelDispatch({ type: "RESET" });

      // Create abort controller for this request
      const controller = new AbortController();
      abortControllerRef.current = controller;

      // Create placeholder for AI response
      const aiMsgId = generateId();
      const aiMsg: ChatMessageType = {
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

  // Handle initial prompt from URL query parameter
  useEffect(() => {
    if (initialPromptHandled.current) return;
    const q = searchParams.get("q");
    if (q) {
      initialPromptHandled.current = true;
      // Small delay to ensure component is mounted
      const timer = setTimeout(() => {
        handleSend(q);
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [searchParams, handleSend]);

  // Cleanup abort controller on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  return (
    <div className="flex h-full flex-col">
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

/**
 * Empty state shown when no messages yet.
 */
function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
        <svg className="h-8 w-8 text-primary" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
        </svg>
      </div>
      <h3 className="mb-2 text-lg font-semibold text-foreground">
        开始规划你的旅行
      </h3>
      <p className="max-w-md text-sm text-muted-foreground">
        告诉我你想去哪里、什么时候出发、几个人同行，
        <br />
        我会为你规划最佳旅行方案。
      </p>
    </div>
  );
}
