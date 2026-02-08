// Types for the simulator dashboard

export interface Persona {
  name: string;
  description: string;
  style: string;
  preferences: Record<string, unknown>;
  initial_message_count: number;
  follow_up_count: number;
}

export interface Scenario {
  name: string;
  description: string;
  fault_count: number;
  fault_types: string[];
}

export interface FaultConfig {
  active_faults: Record<string, {
    fault_type: string;
    enabled: boolean;
    params: Record<string, unknown>;
    injected_at: number;
  }>;
  active_scenario: string | null;
  environment_state: Record<string, unknown>;
  fault_count: number;
}

export interface DimensionScore {
  dimension: string;
  label: string;
  score: number;
  reason: string;
  details: Record<string, unknown>;
}

export interface EvaluationResult {
  total_score: number;
  dimension_scores: DimensionScore[];
  suggestions: string[];
  best_dimension?: string;
  worst_dimension?: string;
}

export interface BattleResult {
  session_id: string;
  persona_name: string;
  scenario_name: string | null;
  turns_completed: number;
  total_duration_ms: number;
  messages: Array<{ role: string; content: string }>;
  evaluation: EvaluationResult;
  traces: TraceEntry[];
}

export interface TraceEntry {
  agent: string;
  task_id: string;
  goal: string;
  status: string;
  summary: string;
  duration_ms: number;
  error: string | null;
  timestamp: number;
}

export interface SessionSummary {
  session_id: string;
  message_count: number;
  trace_count: number;
}

export interface SessionDetail {
  session_id: string;
  messages: Array<{ role: string; content: string }>;
  traces: TraceEntry[];
  message_count: number;
  trace_count: number;
}

export interface ScenarioResult {
  scenario_name: string;
  description: string;
  faults_injected: string[];
  environment_state: Record<string, unknown>;
}
