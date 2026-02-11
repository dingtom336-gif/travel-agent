"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import type {
  ChatMessage as ChatMessageType,
  UIPayload,
  FlightData,
  HotelData,
  POIData,
  WeatherData,
  TimelineDayData,
  BudgetSummary,
} from "@/lib/types";
import FlightCard from "@/components/cards/FlightCard";
import HotelCard from "@/components/cards/HotelCard";
import POICard from "@/components/cards/POICard";
import WeatherCard from "@/components/cards/WeatherCard";
import TimelineCard from "@/components/cards/TimelineCard";
import BudgetChart from "@/components/cards/BudgetChart";
import RouteMapCard from "@/components/cards/RouteMapCard";
import type { RouteMapData } from "@/components/cards/RouteMapCard";
import ThinkingSteps from "./ThinkingSteps";
import MarkdownRenderer from "./MarkdownRenderer";

// Map placeholder markers to UI payload types
const MARKER_TO_TYPES: Record<string, string[]> = {
  flight_cards: ["flight_card"],
  hotel_cards: ["hotel_card"],
  poi_cards: ["poi_card"],
  weather_cards: ["weather_card"],
  timeline: ["timeline_card"],
  budget_chart: ["budget_chart"],
  route_map: ["route_map"],
};

type ContentSegment =
  | { kind: "markdown"; text: string }
  | { kind: "cards"; marker: string };

/**
 * Parse content string into alternating markdown and card-slot segments.
 */
function parseContentSegments(content: string): ContentSegment[] {
  const regex = /\{\{(flight_cards|hotel_cards|poi_cards|weather_cards|timeline|budget_chart|route_map)\}\}/g;
  const segments: ContentSegment[] = [];
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(content)) !== null) {
    if (match.index > lastIndex) {
      segments.push({ kind: "markdown", text: content.slice(lastIndex, match.index) });
    }
    segments.push({ kind: "cards", marker: match[1] });
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < content.length) {
    segments.push({ kind: "markdown", text: content.slice(lastIndex) });
  }

  return segments;
}

/**
 * Render a single UI card based on payload type.
 */
function UICard({ payload }: { payload: UIPayload }) {
  if (payload.status === "loading") {
    return (
      <div className="h-32 w-full animate-pulse rounded-xl bg-muted" />
    );
  }

  switch (payload.type) {
    case "flight_card":
      return <FlightCard data={payload.data as unknown as FlightData} />;
    case "hotel_card":
      return <HotelCard data={payload.data as unknown as HotelData} />;
    case "poi_card":
      return <POICard data={payload.data as unknown as POIData} />;
    case "weather_card":
      return <WeatherCard data={payload.data as unknown as WeatherData} />;
    case "timeline_card":
      return <TimelineCard data={payload.data as unknown as TimelineDayData} />;
    case "budget_chart":
      return <BudgetChart data={payload.data as unknown as BudgetSummary} />;
    case "route_map":
      return <RouteMapCard data={payload.data as unknown as RouteMapData} />;
    default:
      return null;
  }
}

// Progressive stages for the thinking placeholder
const THINKING_STAGES = [
  { text: "正在连接 AI 引擎...", delay: 0 },
  { text: "正在分析你的需求...", delay: 1500 },
  { text: "正在调动专家团队...", delay: 4000 },
  { text: "专家协作中，请稍候...", delay: 8000 },
  { text: "正在整合分析结果...", delay: 15000 },
];

/**
 * Progressive thinking placeholder with staged messages and elapsed timer.
 */
function ThinkingPlaceholder() {
  const [stageIdx, setStageIdx] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const startTime = useRef(Date.now());

  useEffect(() => {
    const timer = setInterval(() => {
      const now = Date.now();
      const diff = now - startTime.current;
      setElapsed(Math.floor(diff / 1000));
      // Advance stage based on elapsed time
      for (let i = THINKING_STAGES.length - 1; i >= 0; i--) {
        if (diff >= THINKING_STAGES[i].delay) {
          setStageIdx(i);
          break;
        }
      }
    }, 500);
    return () => clearInterval(timer);
  }, []);

  const stage = THINKING_STAGES[stageIdx];
  const progress = Math.min((stageIdx + 1) / THINKING_STAGES.length * 100, 95);

  return (
    <div className="rounded-2xl px-4 py-3 text-sm leading-relaxed bg-bubble-ai text-card-foreground">
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <svg
            className="h-3.5 w-3.5 shrink-0 animate-spin text-amber-500"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <span className="flex-1 text-xs font-medium text-amber-600 dark:text-amber-400 transition-all duration-300">
            {stage.text}
          </span>
          <span className="text-[10px] tabular-nums text-muted-foreground">
            {elapsed}s
          </span>
        </div>
        {/* Progress bar */}
        <div className="h-1 w-full overflow-hidden rounded-full bg-amber-500/10">
          <div
            className="h-full rounded-full bg-amber-500/50 transition-all duration-700 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>
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
      className="group/copy mt-0.5 inline-flex items-center gap-1 self-start rounded-md px-1.5 py-1 text-[11px] text-muted-foreground opacity-60 transition-opacity hover:bg-muted hover:text-foreground touch-manipulation sm:opacity-0 sm:group-hover/msg:opacity-100"
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

interface InterleavedContentProps {
  content: string;
  uiPayloads?: UIPayload[];
  thinkingSteps?: ChatMessageType["thinkingSteps"];
  isStreaming: boolean;
}

/**
 * Interleaved content renderer: splits markdown by {{placeholder}} markers
 * and inserts UI cards at the marked positions.
 * Cards not consumed by any marker are rendered at the bottom.
 */
export default function InterleavedContent({
  content,
  uiPayloads,
  thinkingSteps,
  isStreaming,
}: InterleavedContentProps) {
  const segments = parseContentSegments(content);
  const payloads = uiPayloads || [];
  const consumedTypes = new Set<string>();

  // Track which payloads are consumed by markers
  const hasMarkers = segments.some((s) => s.kind === "cards");
  if (hasMarkers) {
    for (const seg of segments) {
      if (seg.kind === "cards") {
        const types = MARKER_TO_TYPES[seg.marker] || [];
        types.forEach((t) => consumedTypes.add(t));
      }
    }
  }

  // Remaining payloads not placed by markers
  const remainingPayloads = payloads.filter(
    (p) => !consumedTypes.has(p.type),
  );

  let cardIdx = 0;

  const hasContent = segments.some((s) => s.kind === "markdown" && s.text.trim());
  const hasThinking = thinkingSteps && thinkingSteps.length > 0;
  const showPlaceholder = isStreaming && !hasContent && !hasThinking;

  // Find index of first non-empty markdown segment (for copy button placement)
  const firstMdIdx = segments.findIndex((s) => s.kind === "markdown" && s.text.trim());
  const showCopy = !isStreaming && hasContent;

  return (
    <div className="group/msg flex flex-col gap-3">
      {/* Progressive thinking placeholder: shown before SSE events arrive */}
      {showPlaceholder && <ThinkingPlaceholder />}

      {/* Thinking steps bubble */}
      {hasThinking && (
        <div className="rounded-2xl px-4 py-3 text-sm leading-relaxed bg-bubble-ai text-card-foreground">
          <ThinkingSteps steps={thinkingSteps} isStreaming={isStreaming} />
        </div>
      )}

      {segments.map((seg, idx) => {
        if (seg.kind === "markdown") {
          const trimmed = seg.text.trim();
          if (!trimmed) return null;
          const isFirstMd = idx === firstMdIdx;
          return (
            <div key={`md-${idx}`}>
              <div
                className={`rounded-2xl px-4 py-3 text-sm leading-relaxed bg-bubble-ai text-card-foreground ${
                  isStreaming && idx === segments.length - 1 ? "cursor-blink" : ""
                }`}
              >
                <div className="prose-sm">
                  <MarkdownRenderer content={seg.text} />
                </div>
              </div>
              {/* Copy button: right after the first text bubble */}
              {isFirstMd && showCopy && <CopyButton text={content} />}
            </div>
          );
        }
        // Card slot
        const types = MARKER_TO_TYPES[seg.marker] || [];
        const matching = payloads.filter((p) => types.includes(p.type));
        if (matching.length === 0) return null;
        return (
          <div key={`cards-${idx}`} className="flex flex-col gap-3">
            {matching.map((payload) => {
              const ci = cardIdx++;
              return (
                <div key={`ui-${ci}`} className="animate-card-in" style={{ animationDelay: `${ci * 0.06}s` }}>
                  <UICard payload={payload} />
                </div>
              );
            })}
          </div>
        );
      })}

      {/* Remaining cards not consumed by markers */}
      {remainingPayloads.length > 0 && (
        <div className="flex flex-col gap-3">
          {remainingPayloads.map((payload, idx) => (
            <div key={`rem-${idx}`} className="animate-card-in" style={{ animationDelay: `${(cardIdx + idx) * 0.06}s` }}>
              <UICard payload={payload} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
