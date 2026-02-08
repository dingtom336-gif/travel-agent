// Message roles
export type MessageRole = "user" | "assistant" | "system";

// UI component payload types for Generative UI cards
export type UIComponentType =
  | "flight_card"
  | "hotel_card"
  | "poi_card"
  | "weather_card"
  | "timeline_card"
  | "budget_chart";

// A single UI payload item attached to a message
export interface UIPayload {
  type: UIComponentType;
  data: Record<string, unknown>;
  status?: "loading" | "loaded" | "error";
}

// Single chat message
export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
  uiPayloads?: UIPayload[];
}

// Agent status during processing
export interface AgentStatus {
  agent: string;
  task: string;
  status: "running" | "done" | "error";
}

// SSE event types from backend (aligned with agent/models.py SSEEventType)
export type SSEEventType =
  | "thinking"
  | "agent_start"
  | "agent_result"
  | "text"
  | "ui_component"
  | "error"
  | "done";

// SSE event data
export interface SSEEvent {
  type: SSEEventType;
  data: Record<string, unknown>;
}

// Chat request payload
export interface ChatRequest {
  session_id?: string;
  message: string;
  attachments?: string[];
}

// Chat response metadata
export interface ChatResponseMeta {
  session_id: string;
  itinerary_id?: string;
}

// Flight card data
export interface FlightData {
  airline: string;
  flightNo: string;
  departure: string;
  arrival: string;
  departTime: string;
  arriveTime: string;
  duration: string;
  price: number;
  currency: string;
}

// Hotel card data
export interface HotelData {
  name: string;
  rating: number;
  stars: number;
  location: string;
  pricePerNight: number;
  currency: string;
  imageUrl?: string;
  amenities: string[];
}

// POI card data
export interface POIData {
  name: string;
  type: string;
  rating: number;
  description: string;
  openingHours?: string;
  ticketPrice?: number;
  currency?: string;
  imageUrl?: string;
}

// Weather card data
export interface WeatherData {
  city: string;
  date: string;
  temperature: { high: number; low: number };
  condition: string;
  humidity: number;
  suggestion: string;
}

// Geographic coordinates
export interface GeoLocation {
  lat: number;
  lng: number;
  label?: string;
}

// Timeline item data
export interface TimelineItem {
  time: string;
  title: string;
  description: string;
  type: "transport" | "attraction" | "hotel" | "food" | "activity";
  duration?: string;
  location?: GeoLocation;
}

// Timeline day data
export interface TimelineDayData {
  day: number;
  date: string;
  title: string;
  items: TimelineItem[];
}

// Budget expense category
export type BudgetCategory =
  | "transport"
  | "accommodation"
  | "food"
  | "ticket"
  | "other";

// Single budget item
export interface BudgetItem {
  id: string;
  category: BudgetCategory;
  name: string;
  amount: number;
  currency: string;
  day?: number;
  note?: string;
}

// Budget summary data
export interface BudgetSummary {
  totalBudget: number;
  totalSpent: number;
  currency: string;
  items: BudgetItem[];
}

// Full itinerary data
export interface ItineraryData {
  id: string;
  title: string;
  destination: string;
  startDate: string;
  endDate: string;
  travelers: number;
  totalBudget: number;
  currency: string;
  status: "draft" | "confirmed" | "in_progress" | "completed";
  days: TimelineDayData[];
  budget: BudgetSummary;
}
