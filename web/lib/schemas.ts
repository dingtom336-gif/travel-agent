import { z } from "zod";

// ====================================================================== //
// SSE Event schemas
// ====================================================================== //

export const SSEEventTypeSchema = z.enum([
  "thinking",
  "agent_start",
  "agent_result",
  "text",
  "ui_component",
  "error",
  "done",
]);

export const SSEEventSchema = z.object({
  type: SSEEventTypeSchema,
  data: z.record(z.string(), z.unknown()),
});

// ====================================================================== //
// Card data schemas (used by dispatchAgentData / UI cards)
// ====================================================================== //

export const FlightDataSchema = z.object({
  airline: z.string(),
  flightNo: z.string(),
  departure: z.string(),
  arrival: z.string(),
  departTime: z.string(),
  arriveTime: z.string(),
  duration: z.string(),
  price: z.number(),
  currency: z.string(),
});

export const HotelDataSchema = z.object({
  name: z.string(),
  rating: z.number(),
  stars: z.number(),
  location: z.string(),
  pricePerNight: z.number(),
  currency: z.string(),
  imageUrl: z.string().optional(),
  amenities: z.array(z.string()),
});

export const POIDataSchema = z.object({
  name: z.string(),
  type: z.string(),
  rating: z.number(),
  description: z.string(),
  openingHours: z.string().optional(),
  ticketPrice: z.number().optional(),
  currency: z.string().optional(),
  imageUrl: z.string().optional(),
});

export const WeatherDataSchema = z.object({
  city: z.string(),
  date: z.string(),
  temperature: z.object({
    high: z.number(),
    low: z.number(),
  }),
  condition: z.string(),
  humidity: z.number(),
  suggestion: z.string(),
});

export const GeoLocationSchema = z.object({
  lat: z.number(),
  lng: z.number(),
  label: z.string().optional(),
});

export const TimelineItemSchema = z.object({
  time: z.string(),
  title: z.string(),
  description: z.string(),
  type: z.enum(["transport", "attraction", "hotel", "food", "activity"]),
  duration: z.string().optional(),
  location: GeoLocationSchema.optional(),
});

export const TimelineDayDataSchema = z.object({
  day: z.number(),
  date: z.string(),
  title: z.string(),
  items: z.array(TimelineItemSchema),
});

export const BudgetCategorySchema = z.enum([
  "transport",
  "accommodation",
  "food",
  "ticket",
  "other",
]);

export const BudgetItemSchema = z.object({
  id: z.string(),
  category: BudgetCategorySchema,
  name: z.string(),
  amount: z.number(),
  currency: z.string(),
  day: z.number().optional(),
  note: z.string().optional(),
});

export const BudgetSummarySchema = z.object({
  totalBudget: z.number(),
  totalSpent: z.number(),
  currency: z.string(),
  items: z.array(BudgetItemSchema),
});

// ====================================================================== //
// Simulator / Debug schemas
// ====================================================================== //

export const DimensionScoreSchema = z.object({
  dimension: z.string(),
  label: z.string(),
  score: z.number(),
  reason: z.string(),
  details: z.record(z.string(), z.unknown()),
});

export const EvaluationResultSchema = z.object({
  total_score: z.number(),
  dimension_scores: z.array(DimensionScoreSchema),
  suggestions: z.array(z.string()),
  best_dimension: z.string().optional(),
  worst_dimension: z.string().optional(),
});

export const SessionSummarySchema = z.object({
  session_id: z.string(),
  message_count: z.number(),
  trace_count: z.number(),
});

// ====================================================================== //
// Helper: safeParse SSE event with warning on failure
// ====================================================================== //

/**
 * Validate an SSE event at runtime. Returns the parsed event on success,
 * or null on failure (with a console.warn).
 */
export function safeParseSSEEvent(
  raw: unknown
): { type: string; data: Record<string, unknown> } | null {
  const result = SSEEventSchema.safeParse(raw);
  if (result.success) {
    return result.data;
  }
  console.warn("[SSE] Invalid event dropped:", result.error.format(), raw);
  return null;
}
