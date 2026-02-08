"use client";

import { useState, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import type { Components } from "react-markdown";
import {
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

interface ChatMessageProps {
  message: ChatMessageType;
}

/**
 * Render a single chat message bubble.
 * User messages: right-aligned, blue bubble.
 * Assistant messages: left-aligned, gray bubble with rich markdown support.
 */
export default function ChatMessage({ message }: ChatMessageProps) {
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

/**
 * Render a single UI card based on payload type.
 */
function UICard({ payload }: { payload: UIPayload }) {
  // Show loading skeleton if status is loading
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

/**
 * Rich markdown renderer using react-markdown with GFM tables,
 * raw HTML support, and custom Tailwind-styled elements.
 */
const markdownComponents: Components = {
  // Table styling
  table: ({ children }) => (
    <div className="my-3 overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-sm">{children}</table>
    </div>
  ),
  thead: ({ children }) => (
    <thead className="bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
      {children}
    </thead>
  ),
  th: ({ children }) => (
    <th className="px-3 py-2 text-left font-medium">{children}</th>
  ),
  td: ({ children }) => (
    <td className="border-t border-border/50 px-3 py-2">{children}</td>
  ),
  // Image with error fallback
  img: ({ src, alt }) => (
    <ImageWithFallback src={String(src || "")} alt={String(alt || "")} />
  ),
  // Link styling
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-primary underline decoration-primary/30 hover:decoration-primary transition-colors"
    >
      {children}
    </a>
  ),
  // Blockquote
  blockquote: ({ children }) => (
    <blockquote className="my-2 border-l-3 border-primary/40 pl-3 text-muted-foreground italic">
      {children}
    </blockquote>
  ),
  // Code blocks + inline code
  code: ({ className, children }) => {
    const isBlock = className?.includes("language-");
    if (isBlock) {
      return (
        <pre className="my-2 overflow-x-auto rounded-lg bg-foreground/5 p-3 text-xs">
          <code className={className}>{children}</code>
        </pre>
      );
    }
    return (
      <code className="rounded bg-foreground/10 px-1.5 py-0.5 text-xs font-mono">
        {children}
      </code>
    );
  },
  pre: ({ children }) => <>{children}</>,
  // Headings
  h1: ({ children }) => <h2 className="mt-4 mb-1.5 text-base font-bold">{children}</h2>,
  h2: ({ children }) => <h3 className="mt-3 mb-1 text-base font-bold">{children}</h3>,
  h3: ({ children }) => <h4 className="mt-3 mb-1 text-sm font-semibold">{children}</h4>,
  h4: ({ children }) => <h5 className="mt-2 mb-1 text-sm font-medium">{children}</h5>,
  // Lists
  ul: ({ children }) => <ul className="my-1 space-y-0.5 pl-4 list-disc marker:text-muted-foreground">{children}</ul>,
  ol: ({ children }) => <ol className="my-1 space-y-0.5 pl-4 list-decimal marker:text-muted-foreground">{children}</ol>,
  li: ({ children }) => <li className="text-sm leading-relaxed">{children}</li>,
  // Paragraphs
  p: ({ children }) => <p className="my-1.5 leading-relaxed">{children}</p>,
  // Horizontal rule as visual divider
  hr: () => <hr className="my-3 border-border/60" />,
  // Strong / emphasis
  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,
};

function MarkdownRenderer({ content }: { content: string }) {
  if (!content) return null;
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeRaw]}
      components={markdownComponents}
    >
      {content}
    </ReactMarkdown>
  );
}

/**
 * Image component with gradient fallback on load error.
 */
function ImageWithFallback({ src, alt }: { src: string; alt: string }) {
  const [failed, setFailed] = useState(false);
  const handleError = useCallback(() => setFailed(true), []);

  if (failed) {
    return (
      <div className="my-2 flex h-40 w-full items-center justify-center rounded-xl bg-gradient-to-br from-blue-50 to-cyan-50 text-sm text-muted-foreground">
        {alt || "Image"}
      </div>
    );
  }

  return (
    <img
      src={src}
      alt={alt}
      className="my-2 max-w-full rounded-xl shadow-sm"
      loading="lazy"
      onError={handleError}
    />
  );
}

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
 * Interleaved content renderer: splits markdown by {{placeholder}} markers
 * and inserts UI cards at the marked positions.
 * Cards not consumed by any marker are rendered at the bottom.
 */
function InterleavedContent({
  content,
  uiPayloads,
  thinkingSteps,
  isStreaming,
}: {
  content: string;
  uiPayloads?: UIPayload[];
  thinkingSteps?: ChatMessageType["thinkingSteps"];
  isStreaming: boolean;
}) {
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

  return (
    <div className="flex flex-col gap-3">
      {/* Thinking steps bubble */}
      {thinkingSteps && thinkingSteps.length > 0 && (
        <div className="rounded-2xl px-4 py-3 text-sm leading-relaxed bg-bubble-ai text-card-foreground">
          <ThinkingSteps steps={thinkingSteps} isStreaming={isStreaming} />
        </div>
      )}

      {segments.map((seg, idx) => {
        if (seg.kind === "markdown") {
          const trimmed = seg.text.trim();
          if (!trimmed) return null;
          return (
            <div
              key={`md-${idx}`}
              className={`rounded-2xl px-4 py-3 text-sm leading-relaxed bg-bubble-ai text-card-foreground ${
                isStreaming && idx === segments.length - 1 ? "cursor-blink" : ""
              }`}
            >
              <div className="prose-sm">
                <MarkdownRenderer content={seg.text} />
              </div>
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
