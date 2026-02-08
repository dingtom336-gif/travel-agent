import type {
  BattleResult,
  EvaluationResult,
  FaultConfig,
  Persona,
  Scenario,
  ScenarioResult,
  SessionDetail,
  SessionSummary,
} from "./simulator-types";
import { ChatRequest, SSEEvent, SSEEventType } from "./types";

// Backend agent service base URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Connection timeout for SSE requests (ms)
const STREAM_TIMEOUT_MS = 120_000;

// Callback for handling SSE events
export type SSECallback = (event: SSEEvent) => void;

/**
 * Check if the backend service is reachable.
 * Returns true if /health responds within 3s, false otherwise.
 */
export async function checkBackendHealth(): Promise<boolean> {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 3000);
    const res = await fetch(`${API_BASE_URL}/health`, {
      signal: controller.signal,
    });
    clearTimeout(timer);
    return res.ok;
  } catch {
    return false;
  }
}

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
    // Combine user-provided abort signal with a timeout signal
    const timeoutController = new AbortController();
    const timeoutId = setTimeout(
      () => timeoutController.abort(),
      STREAM_TIMEOUT_MS
    );

    const combinedSignal = signal
      ? combineAbortSignals(signal, timeoutController.signal)
      : timeoutController.signal;

    const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
      signal: combinedSignal,
    });

    // Clear timeout once we get a response header
    clearTimeout(timeoutId);

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

/**
 * Combine multiple AbortSignals into one.
 * The combined signal aborts when any of the input signals aborts.
 */
// ====================================================================== //
// Simulator / Debug API functions
// ====================================================================== //

const DEBUG_HEADERS = {
  "Content-Type": "application/json",
};

export async function getPersonas(): Promise<Persona[]> {
  const res = await fetch(`${API_BASE_URL}/api/debug/personas`);
  const data = await res.json();
  return data.personas ?? [];
}

export async function getScenarios(): Promise<Scenario[]> {
  const res = await fetch(`${API_BASE_URL}/api/debug/scenarios`);
  const data = await res.json();
  return data.scenarios ?? [];
}

export async function runBattle(
  persona: string,
  turns: number,
  scenario?: string
): Promise<BattleResult> {
  const res = await fetch(`${API_BASE_URL}/api/debug/battle`, {
    method: "POST",
    headers: DEBUG_HEADERS,
    body: JSON.stringify({ persona, turns, scenario: scenario || null }),
  });
  if (!res.ok) throw new Error(`Battle failed: ${res.status}`);
  return res.json();
}

export async function activateScenario(
  scenario: string
): Promise<ScenarioResult> {
  const res = await fetch(`${API_BASE_URL}/api/debug/activate-scenario`, {
    method: "POST",
    headers: DEBUG_HEADERS,
    body: JSON.stringify({ scenario }),
  });
  if (!res.ok) throw new Error(`Activate scenario failed: ${res.status}`);
  return res.json();
}

export async function resetFaults(): Promise<{ status: string; faults_cleared: number }> {
  const res = await fetch(`${API_BASE_URL}/api/debug/reset`, {
    method: "POST",
    headers: DEBUG_HEADERS,
  });
  return res.json();
}

export async function getFaultConfig(): Promise<FaultConfig> {
  const res = await fetch(`${API_BASE_URL}/api/debug/fault-config`);
  return res.json();
}

export async function injectFault(
  faultType: string,
  params?: Record<string, unknown>
): Promise<unknown> {
  const res = await fetch(`${API_BASE_URL}/api/debug/inject-fault`, {
    method: "POST",
    headers: DEBUG_HEADERS,
    body: JSON.stringify({ fault_type: faultType, params: params ?? {} }),
  });
  if (!res.ok) throw new Error(`Inject fault failed: ${res.status}`);
  return res.json();
}

export async function evaluateSession(
  sessionId: string
): Promise<{ session_id: string; evaluation: EvaluationResult }> {
  const res = await fetch(`${API_BASE_URL}/api/debug/evaluate`, {
    method: "POST",
    headers: DEBUG_HEADERS,
    body: JSON.stringify({ session_id: sessionId }),
  });
  if (!res.ok) throw new Error(`Evaluate failed: ${res.status}`);
  return res.json();
}

export async function listSessions(): Promise<SessionSummary[]> {
  const res = await fetch(`${API_BASE_URL}/api/debug/sessions`);
  const data = await res.json();
  return data.sessions ?? [];
}

export async function getSessionDetail(
  sessionId: string
): Promise<SessionDetail> {
  const res = await fetch(`${API_BASE_URL}/api/debug/sessions/${sessionId}`);
  if (!res.ok) throw new Error(`Session not found: ${res.status}`);
  return res.json();
}

// ====================================================================== //
// Internal helpers
// ====================================================================== //

function combineAbortSignals(...signals: AbortSignal[]): AbortSignal {
  const controller = new AbortController();
  for (const sig of signals) {
    if (sig.aborted) {
      controller.abort(sig.reason);
      return controller.signal;
    }
    sig.addEventListener("abort", () => controller.abort(sig.reason), {
      once: true,
    });
  }
  return controller.signal;
}
