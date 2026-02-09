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

// Max retry attempts for transient network errors
const MAX_RETRIES = 3;

// Base delay for exponential backoff (ms)
const BASE_RETRY_DELAY_MS = 1_000;

// Callback for handling SSE events
export type SSECallback = (event: SSEEvent) => void;

// Connection state for UI feedback
export type ConnectionState = "idle" | "connecting" | "connected" | "reconnecting" | "failed";
export type ConnectionStateCallback = (state: ConnectionState) => void;

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
 * Retries up to MAX_RETRIES times on transient network errors with exponential backoff.
 */
export async function chatStream(
  request: ChatRequest,
  onEvent: SSECallback,
  signal?: AbortSignal,
  onConnectionStateChange?: ConnectionStateCallback
): Promise<void> {
  const notifyState = (state: ConnectionState) => {
    onConnectionStateChange?.(state);
  };

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    // On first attempt: "connecting"; on retry: "reconnecting"
    notifyState(attempt === 0 ? "connecting" : "reconnecting");

    try {
      await chatStreamOnce(request, onEvent, signal);
      // Stream completed successfully
      notifyState("idle");
      return;
    } catch (error) {
      // User-initiated abort — stop immediately
      if (error instanceof DOMException && error.name === "AbortError") {
        notifyState("idle");
        return;
      }

      // Non-retryable HTTP errors (4xx) — stop immediately
      if (error instanceof HttpError && error.status >= 400 && error.status < 500) {
        notifyState("failed");
        onEvent({
          type: "error",
          data: { message: error.message },
        });
        return;
      }

      // Last attempt exhausted
      if (attempt === MAX_RETRIES) {
        notifyState("failed");
        onEvent({
          type: "error",
          data: {
            message: error instanceof Error ? error.message : "Unknown error occurred",
          },
        });
        return;
      }

      // Wait with exponential backoff before retrying
      const delay = BASE_RETRY_DELAY_MS * Math.pow(2, attempt);
      await sleep(delay, signal);
    }
  }
}

/**
 * Single attempt to stream chat SSE. Throws on error.
 */
async function chatStreamOnce(
  request: ChatRequest,
  onEvent: SSECallback,
  signal?: AbortSignal
): Promise<void> {
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

  clearTimeout(timeoutId);

  if (!response.ok) {
    throw new HttpError(response.status, response.statusText);
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

      if (trimmed.startsWith("event:")) {
        currentEventType = trimmed.slice(6).trim() as SSEEventType;
        continue;
      }

      if (trimmed.startsWith("data:")) {
        const dataStr = trimmed.slice(5).trim();
        try {
          const data = JSON.parse(dataStr);
          onEvent({ type: currentEventType, data });
        } catch {
          onEvent({
            type: currentEventType,
            data: { content: dataStr },
          });
        }
        currentEventType = "text";
      }
    }
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

class HttpError extends Error {
  constructor(public status: number, statusText: string) {
    super(`HTTP error: ${status} ${statusText}`);
  }
}

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(resolve, ms);
    signal?.addEventListener("abort", () => {
      clearTimeout(timer);
      reject(new DOMException("Aborted", "AbortError"));
    }, { once: true });
  });
}

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
