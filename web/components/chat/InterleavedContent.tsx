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
