"use client";

import { useCallback } from "react";
import type { Dispatch, SetStateAction } from "react";
import type {
  ChatMessage,
  SSEEvent,
  ThinkingStep,
  UIPayload,
  FlightData,
  HotelData,
  POIData,
  WeatherData,
  TimelineDayData,
  BudgetSummary,
} from "@/lib/types";
import type { Action } from "@/lib/travel-context";
import { createItinerary } from "@/lib/api-client";

interface UseSSEHandlerOptions {
  setMessages: Dispatch<SetStateAction<ChatMessage[]>>;
  setIsProcessing: Dispatch<SetStateAction<boolean>>;
  sessionIdRef: React.RefObject<string | undefined>;
  travelDispatch: Dispatch<Action>;
}

export function useSSEHandler({
  setMessages,
  setIsProcessing,
  sessionIdRef,
  travelDispatch,
}: UseSSEHandlerOptions) {
  // Upsert a thinking step into a specific AI message
  const upsertThinkingStep = useCallback(
    (msgId: string, step: ThinkingStep) => {
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
    },
    [setMessages]
  );

  // Append text content to a streaming AI message
  const appendText = useCallback(
    (msgId: string, chunk: string) => {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === msgId
            ? { ...msg, content: msg.content + chunk }
            : msg
        )
      );
    },
    [setMessages]
  );

  // Append a UI payload to a streaming AI message
  const appendUIPayload = useCallback(
    (msgId: string, payload: UIPayload) => {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === msgId
            ? { ...msg, uiPayloads: [...(msg.uiPayloads || []), payload] }
            : msg
        )
      );
    },
    [setMessages]
  );

  // Mark a message as done streaming
  const finishMessage = useCallback(
    (msgId: string) => {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === msgId ? { ...msg, isStreaming: false } : msg
        )
      );
      setIsProcessing(false);
    },
    [setMessages, setIsProcessing]
  );

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
          upsertThinkingStep(aiMsgId, {
            agent: (data.agent as string) || "unknown",
            task: (data.task as string) || "处理中...",
            status: "running",
            timestamp: Date.now(),
          });
          break;
        }

        case "agent_result": {
          const agentName = (data.agent as string) || "unknown";
          const resultStatus = (data.status as string) === "failed" ? "error" : "done";
          setMessages((prev) =>
            prev.map((msg) => {
              if (msg.id !== aiMsgId) return msg;
              const steps = [...(msg.thinkingSteps || [])];
              for (let i = steps.length - 1; i >= 0; i--) {
                if (steps[i].agent === agentName && steps[i].status === "running") {
                  steps[i] = {
                    ...steps[i],
                    task: (data.summary as string) || steps[i].task,
                    status: resultStatus as "done" | "error",
                    timestamp: Date.now(),
                  };
                  break;
                }
              }
              return { ...msg, thinkingSteps: steps };
            })
          );

          const resultData = data.data as Record<string, unknown> | undefined;
          if (resultData) {
            dispatchAgentData(agentName, resultData);
          }
          break;
        }

        case "text": {
          const content = (data.content as string) || "";
          if (content) {
            appendText(aiMsgId, content);
          }
          break;
        }

        case "ui_component": {
          const payload: UIPayload = {
            type: data.type as UIPayload["type"],
            data: (data.data as Record<string, unknown>) || data,
            status: (data.status as UIPayload["status"]) || "loaded",
          };
          appendUIPayload(aiMsgId, payload);
          break;
        }

        case "done": {
          setMessages((prev) =>
            prev.map((msg) => {
              if (msg.id !== aiMsgId) return msg;
              const updatedSteps = (msg.thinkingSteps || []).map((s) =>
                s.status === "running" ? { ...s, status: "done" as const } : s
              );
              return { ...msg, thinkingSteps: updatedSteps };
            })
          );
          if (data.session_id) {
            const sid = data.session_id as string;
            sessionIdRef.current = sid;
            travelDispatch({
              type: "SET_SESSION",
              payload: { sessionId: sid },
            });

            // Save itinerary to API if we have itinerary data
            if (data.itinerary_id || data.destination) {
              createItinerary({
                title: (data.title as string) || `${data.destination || "旅行"}行程`,
                destination: (data.destination as string) || "",
                session_id: sid,
                days: data.days || [],
                budget_items: data.budget_items || [],
              }).catch(() => {
                // Non-critical: silently ignore save failures
              });
            }
          }
          finishMessage(aiMsgId);
          break;
        }

        case "error": {
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
    [upsertThinkingStep, appendText, appendUIPayload, finishMessage, dispatchAgentData, setMessages, travelDispatch, sessionIdRef]
  );

  return { handleSSEEvent, upsertThinkingStep, appendText, finishMessage };
}
