// Message roles
export type MessageRole = "user" | "assistant" | "system";

// Single chat message
export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
}

// Agent status during processing
export interface AgentStatus {
  agent: string;
  task: string;
  status: "running" | "done" | "error";
}

// SSE event types from backend
export type SSEEventType =
  | "thinking"
  | "agent_start"
  | "agent_done"
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

// Timeline item data
export interface TimelineItem {
  time: string;
  title: string;
  description: string;
  type: "transport" | "attraction" | "hotel" | "food" | "activity";
  duration?: string;
}

// Timeline day data
export interface TimelineDayData {
  day: number;
  date: string;
  title: string;
  items: TimelineItem[];
}
