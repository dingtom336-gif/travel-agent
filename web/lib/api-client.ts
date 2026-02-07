import { ChatRequest, SSEEvent, SSEEventType } from "./types";

// Backend agent service base URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Callback for handling SSE events
export type SSECallback = (event: SSEEvent) => void;

/**
 * Send a chat message and handle streaming SSE response.
 * Calls onEvent for each received server-sent event.
 */
export async function chatStream(
  request: ChatRequest,
  onEvent: SSECallback,
  signal?: AbortSignal
): Promise<void> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
      signal,
    });

    if (!response.ok) {
      throw new Error(`HTTP error: ${response.status} ${response.statusText}`);
    }

    if (!response.body) {
      throw new Error("Response body is null");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");

      // Keep the last incomplete line in buffer
      buffer = lines.pop() || "";

      let currentEventType: SSEEventType = "text";

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;

        // Parse SSE event type line
        if (trimmed.startsWith("event:")) {
          currentEventType = trimmed.slice(6).trim() as SSEEventType;
          continue;
        }

        // Parse SSE data line
        if (trimmed.startsWith("data:")) {
          const dataStr = trimmed.slice(5).trim();
          try {
            const data = JSON.parse(dataStr);
            onEvent({ type: currentEventType, data });
          } catch {
            // If not valid JSON, treat as plain text
            onEvent({
              type: currentEventType,
              data: { content: dataStr },
            });
          }
          // Reset event type to default after processing
          currentEventType = "text";
        }
      }
    }
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      // Request was aborted, not an error
      return;
    }
    onEvent({
      type: "error",
      data: {
        message: error instanceof Error ? error.message : "Unknown error occurred",
      },
    });
  }
}

/**
 * Fetch itinerary list for the current user.
 */
export async function getItineraries(): Promise<unknown[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/itineraries`);
    if (!response.ok) {
      throw new Error(`HTTP error: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error("Failed to fetch itineraries:", error);
    return [];
  }
}

/**
 * Fetch a single itinerary by ID.
 */
export async function getItinerary(id: string): Promise<unknown | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/itineraries/${id}`);
    if (!response.ok) {
      throw new Error(`HTTP error: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error("Failed to fetch itinerary:", error);
    return null;
  }
}
