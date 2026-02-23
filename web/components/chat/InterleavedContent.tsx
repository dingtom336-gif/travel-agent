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

// Card types that render inline (compact) inside the bubble
const INLINE_CARD_TYPES = new Set(["flight_card", "hotel_card", "poi_card", "weather_card"]);

type ContentSegment =
  | { kind: "markdown"; text: string }
  | { kind: "cards"; marker: string };

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

// --- Compact inline card components (inside bubble) ---

function InlineFlightCard({ data }: { data: FlightData }) {
  return (
    <div className="flex items-center gap-2 rounded-xl border border-border/50 bg-background/50 px-2.5 py-2 sm:gap-3 sm:px-3 sm:py-2.5">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-sky-500/10 text-sky-500 sm:h-8 sm:w-8">
        <svg className="h-3.5 w-3.5 sm:h-4 sm:w-4" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
        </svg>
      </div>
      <div className="flex-1 min-w-0 overflow-hidden">
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-semibold text-card-foreground truncate">{data.airline}</span>
          <span className="shrink-0 text-[10px] text-muted-foreground">{data.flightNo}</span>
        </div>
        <div className="truncate text-[11px] text-muted-foreground">
          {data.departure} {data.departTime} → {data.arrival} {data.arriveTime} ({data.duration})
        </div>
      </div>
      <span className="shrink-0 text-xs font-bold text-primary sm:text-sm">{data.currency}{data.price}</span>
    </div>
  );
}

function InlineHotelCard({ data }: { data: HotelData }) {
  return (
    <div className="flex items-center gap-2 rounded-xl border border-border/50 bg-background/50 px-2.5 py-2 sm:gap-3 sm:px-3 sm:py-2.5">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-purple-500/10 text-purple-500 sm:h-8 sm:w-8">
        <svg className="h-3.5 w-3.5 sm:h-4 sm:w-4" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21M3 3h12m-.75 4.5H21m-3.75 3H21m-3.75 3H21" />
        </svg>
      </div>
      <div className="flex-1 min-w-0 overflow-hidden">
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-semibold text-card-foreground truncate">{data.name}</span>
          <span className="shrink-0 text-[10px] text-amber-500">{"★".repeat(Math.min(data.stars, 5))}</span>
        </div>
        <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
          <span className="truncate">{data.location}</span>
          {data.rating > 0 && <span className="shrink-0 text-green-500">{data.rating}分</span>}
        </div>
      </div>
      <div className="shrink-0 text-right">
        <span className="text-xs font-bold text-primary sm:text-sm">{data.currency}{data.pricePerNight}</span>
        <span className="block text-[10px] text-muted-foreground">/晚</span>
      </div>
    </div>
  );
}

function InlinePOICard({ data }: { data: POIData }) {
  const typeEmoji: Record<string, string> = {
    景点: "🏛️", 公园: "🌳", 美食: "🍜", 购物: "🛍️",
    博物馆: "🏛️", 寺庙: "⛩️", 活动: "🎯", 自然: "🏞️",
  };
  const emoji = typeEmoji[data.type] || "📍";

  return (
    <div className="flex items-center gap-2 rounded-xl border border-border/50 bg-background/50 px-2.5 py-2 sm:gap-3 sm:px-3 sm:py-2.5">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-green-500/10 text-sm sm:h-8 sm:w-8 sm:text-base">
        {emoji}
      </div>
      <div className="flex-1 min-w-0 overflow-hidden">
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-semibold text-card-foreground truncate">{data.name}</span>
          <span className="shrink-0 rounded bg-muted px-1 py-0.5 text-[10px] text-muted-foreground">{data.type}</span>
        </div>
        <div className="text-[11px] text-muted-foreground truncate">{data.description}</div>
      </div>
      <div className="shrink-0 flex flex-col items-end gap-0.5">
        {data.rating > 0 && (
          <span className="flex items-center gap-0.5 text-xs">
            <span className="text-amber-500">★</span>
            <span className="font-medium text-card-foreground">{data.rating}</span>
          </span>
        )}
        {data.ticketPrice != null && data.ticketPrice > 0 && (
          <span className="text-[10px] text-muted-foreground">{data.currency || "CNY"}{data.ticketPrice}</span>
        )}
      </div>
    </div>
  );
}

function InlineWeatherCard({ data }: { data: WeatherData }) {
  return (
    <div className="flex items-center gap-2 rounded-xl border border-border/50 bg-background/50 px-2.5 py-2 sm:gap-3 sm:px-3 sm:py-2.5">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-cyan-500/10 text-sm sm:h-8 sm:w-8 sm:text-base">
        🌤️
      </div>
      <div className="flex-1 min-w-0 overflow-hidden">
        <div className="text-xs font-semibold text-card-foreground truncate">{data.city} · {data.date}</div>
        <div className="text-[11px] text-muted-foreground truncate">{data.condition} · 湿度{data.humidity}%</div>
      </div>
      <span className="shrink-0 text-xs font-bold text-card-foreground sm:text-sm">{data.temperature.low}°~{data.temperature.high}°</span>
    </div>
  );
}

/**
 * Render an inline card inside the bubble based on payload type.
 */
function InlineCard({ payload }: { payload: UIPayload }) {
  if (payload.status === "loading") {
    return <div className="h-12 w-full animate-pulse rounded-xl bg-muted/50" />;
  }
  switch (payload.type) {
    case "flight_card":
      return <InlineFlightCard data={payload.data as unknown as FlightData} />;
    case "hotel_card":
      return <InlineHotelCard data={payload.data as unknown as HotelData} />;
    case "poi_card":
      return <InlinePOICard data={payload.data as unknown as POIData} />;
    case "weather_card":
      return <InlineWeatherCard data={payload.data as unknown as WeatherData} />;
    default:
      return null;
  }
}

/**
 * Render a standalone card outside the bubble (timeline, budget, route map).
 */
function StandaloneCard({ payload }: { payload: UIPayload }) {
  if (payload.status === "loading") {
    return <div className="h-32 w-full animate-pulse rounded-xl bg-muted" />;
  }
  switch (payload.type) {
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

function ThinkingPlaceholder() {
  const [stageIdx, setStageIdx] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const startTime = useRef(Date.now());

  useEffect(() => {
    const timer = setInterval(() => {
      const now = Date.now();
      const diff = now - startTime.current;
      setElapsed(Math.floor(diff / 1000));
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
    <div className="rounded-2xl px-3 py-2.5 text-sm leading-relaxed bg-bubble-ai text-card-foreground overflow-hidden sm:px-4 sm:py-3">
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <svg className="h-3.5 w-3.5 shrink-0 animate-spin text-amber-500" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <span className="flex-1 text-xs font-medium text-amber-600 dark:text-amber-400 transition-all duration-300">
            {stage.text}
          </span>
          <span className="text-[10px] tabular-nums text-muted-foreground">{elapsed}s</span>
        </div>
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
      onPointerDown={(e) => { e.preventDefault(); handleCopy(); }}
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

interface InterleavedContentProps {
  content: string;
  uiPayloads?: UIPayload[];
  thinkingSteps?: ChatMessageType["thinkingSteps"];
  isStreaming: boolean;
}

/**
 * Interleaved content renderer.
 * Inline cards (flight/hotel/poi/weather) are embedded inside the bubble.
 * Standalone cards (timeline/budget/route_map) render outside.
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

  const hasMarkers = segments.some((s) => s.kind === "cards");
  if (hasMarkers) {
    for (const seg of segments) {
      if (seg.kind === "cards") {
        const types = MARKER_TO_TYPES[seg.marker] || [];
        types.forEach((t) => consumedTypes.add(t));
      }
    }
  }

  const remainingPayloads = payloads.filter((p) => !consumedTypes.has(p.type));
  // Split remaining into inline vs standalone
  const remainingInline = remainingPayloads.filter((p) => INLINE_CARD_TYPES.has(p.type));
  const remainingStandalone = remainingPayloads.filter((p) => !INLINE_CARD_TYPES.has(p.type));

  let standaloneIdx = 0;

  const hasContent = segments.some((s) => s.kind === "markdown" && s.text.trim());
  const hasThinking = thinkingSteps && thinkingSteps.length > 0;
  const showPlaceholder = isStreaming && !hasContent && !hasThinking;
  const showCopy = !isStreaming && hasContent;

  // Build the bubble content: all markdown + inline cards go inside one bubble
  const bubbleSegments: React.ReactNode[] = [];
  let hasBubbleContent = false;

  segments.forEach((seg, idx) => {
    if (seg.kind === "markdown") {
      const trimmed = seg.text.trim();
      if (!trimmed) return;
      hasBubbleContent = true;
      bubbleSegments.push(
        <div key={`md-${idx}`} className="prose-sm min-w-0 overflow-hidden">
          <MarkdownRenderer content={seg.text} />
        </div>
      );
    } else {
      // Card slot
      const types = MARKER_TO_TYPES[seg.marker] || [];
      const matching = payloads.filter((p) => types.includes(p.type));
      if (matching.length === 0) return;

      // Inline cards go inside bubble, standalone cards are collected separately
      const inlineMatching = matching.filter((p) => INLINE_CARD_TYPES.has(p.type));
      const standaloneMatching = matching.filter((p) => !INLINE_CARD_TYPES.has(p.type));

      if (inlineMatching.length > 0) {
        hasBubbleContent = true;
        bubbleSegments.push(
          <div key={`inline-${idx}`} className="flex flex-col gap-2 my-1">
            {inlineMatching.map((payload, ci) => (
              <div key={`ic-${idx}-${ci}`} className="animate-card-in" style={{ animationDelay: `${ci * 0.06}s` }}>
                <InlineCard payload={payload} />
              </div>
            ))}
          </div>
        );
      }

      // Standalone cards are rendered outside the bubble (handled below)
      if (standaloneMatching.length > 0) {
        // We mark them to render after the bubble
        // (they're already in the payloads, we just skip them here)
      }
    }
  });

  // Add remaining inline cards to bubble
  if (remainingInline.length > 0) {
    hasBubbleContent = true;
    bubbleSegments.push(
      <div key="remaining-inline" className="flex flex-col gap-2 my-1">
        {remainingInline.map((payload, ci) => (
          <div key={`ri-${ci}`} className="animate-card-in" style={{ animationDelay: `${ci * 0.06}s` }}>
            <InlineCard payload={payload} />
          </div>
        ))}
      </div>
    );
  }

  // Collect standalone cards from marker slots
  const standaloneFromMarkers: UIPayload[] = [];
  segments.forEach((seg) => {
    if (seg.kind === "cards") {
      const types = MARKER_TO_TYPES[seg.marker] || [];
      const matching = payloads.filter((p) => types.includes(p.type) && !INLINE_CARD_TYPES.has(p.type));
      standaloneFromMarkers.push(...matching);
    }
  });
  const allStandalone = [...standaloneFromMarkers, ...remainingStandalone];

  return (
    <div className="group/msg flex flex-col gap-3 min-w-0">
      {showPlaceholder && <ThinkingPlaceholder />}

      {hasThinking && (
        <div className="rounded-2xl px-4 py-3 text-sm leading-relaxed bg-bubble-ai text-card-foreground overflow-hidden">
          <ThinkingSteps steps={thinkingSteps} isStreaming={isStreaming} />
        </div>
      )}

      {/* Main bubble: markdown + inline cards together */}
      {hasBubbleContent && (
        <div>
          <div
            className={`rounded-2xl px-3 py-2.5 text-sm leading-relaxed bg-bubble-ai text-card-foreground flex flex-col gap-3 overflow-hidden break-words sm:px-4 sm:py-3 ${
              isStreaming ? "cursor-blink" : ""
            }`}
          >
            {bubbleSegments}
          </div>
          {showCopy && <CopyButton text={content} />}
        </div>
      )}

      {/* Standalone cards outside bubble (timeline, budget, route map) */}
      {allStandalone.length > 0 && (
        <div className="flex flex-col gap-3 min-w-0 overflow-hidden">
          {allStandalone.map((payload, idx) => {
            const si = standaloneIdx++;
            return (
              <div key={`sa-${si}`} className="animate-card-in" style={{ animationDelay: `${si * 0.06}s` }}>
                <StandaloneCard payload={payload} />
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
