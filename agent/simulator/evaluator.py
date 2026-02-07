# AI Evaluator – rule-based multi-dimension scoring for conversations
from __future__ import annotations

import statistics
from enum import Enum
from typing import Any, Dict, List, Optional

from agent.simulator.scoring_rules import (
  score_coherence,
  score_completeness,
  score_intent_understanding,
  score_personalization,
  score_response_quality,
  score_tool_usage,
)


class EvaluationDimension(str, Enum):
  """Dimensions for evaluating agent conversation quality."""

  INTENT_UNDERSTANDING = "intent_understanding"
  TOOL_USAGE = "tool_usage"
  RESPONSE_QUALITY = "response_quality"
  PERSONALIZATION = "personalization"
  COMPLETENESS = "completeness"
  COHERENCE = "coherence"


# Human-readable labels for each dimension
DIMENSION_LABELS: Dict[EvaluationDimension, str] = {
  EvaluationDimension.INTENT_UNDERSTANDING: "Intent Understanding Accuracy",
  EvaluationDimension.TOOL_USAGE: "Tool Usage Compliance",
  EvaluationDimension.RESPONSE_QUALITY: "Response Quality",
  EvaluationDimension.PERSONALIZATION: "Personalization Level",
  EvaluationDimension.COMPLETENESS: "Plan Completeness",
  EvaluationDimension.COHERENCE: "Multi-turn Coherence",
}

# Map dimensions to their scoring functions and argument signatures
_SCORING_FUNCTIONS = {
  EvaluationDimension.INTENT_UNDERSTANDING: {
    "fn": score_intent_understanding,
    "args": ("messages", "traces"),
    "suggestion": (
      "Improve key info extraction: ensure destination, dates, "
      "travelers, and budget are identified early in the conversation."
    ),
  },
  EvaluationDimension.TOOL_USAGE: {
    "fn": score_tool_usage,
    "args": ("messages", "traces"),
    "suggestion": (
      "Optimize tool usage: ensure correct agents are dispatched "
      "and tool calls complete successfully."
    ),
  },
  EvaluationDimension.RESPONSE_QUALITY: {
    "fn": score_response_quality,
    "args": ("messages",),
    "suggestion": (
      "Enhance response quality: provide more structured information, "
      "adequate detail level, and directly address user questions."
    ),
  },
  EvaluationDimension.PERSONALIZATION: {
    "fn": score_personalization,
    "args": ("messages", "traces"),
    "suggestion": (
      "Increase personalization: reference user preferences, "
      "past history, and tailor recommendations to the user profile."
    ),
  },
  EvaluationDimension.COMPLETENESS: {
    "fn": score_completeness,
    "args": ("messages", "traces"),
    "suggestion": (
      "Improve plan completeness: ensure the itinerary covers "
      "transport, accommodation, attractions, and budget breakdown."
    ),
  },
  EvaluationDimension.COHERENCE: {
    "fn": score_coherence,
    "args": ("messages",),
    "suggestion": (
      "Strengthen coherence: maintain consistent context across "
      "turns and avoid contradicting earlier information."
    ),
  },
}


class DimensionScore:
  """Score for a single evaluation dimension."""

  def __init__(
    self,
    dimension: EvaluationDimension,
    score: int,
    reason: str,
    details: Optional[Dict[str, Any]] = None,
  ) -> None:
    self.dimension = dimension
    self.score = max(1, min(5, score))  # clamp 1-5
    self.reason = reason
    self.details = details or {}

  def to_dict(self) -> Dict[str, Any]:
    """Serialize to dict."""
    return {
      "dimension": self.dimension.value,
      "label": DIMENSION_LABELS[self.dimension],
      "score": self.score,
      "reason": self.reason,
      "details": self.details,
    }


class EvaluationReport:
  """Full evaluation report for a conversation."""

  def __init__(
    self,
    scores: List[DimensionScore],
    suggestions: List[str],
  ) -> None:
    self.scores = scores
    self.suggestions = suggestions

  @property
  def total_score(self) -> float:
    """Average score across all dimensions (1-5 scale)."""
    if not self.scores:
      return 0.0
    return round(
      sum(s.score for s in self.scores) / len(self.scores), 2
    )

  @property
  def max_dimension(self) -> Optional[DimensionScore]:
    """Dimension with the highest score."""
    if not self.scores:
      return None
    return max(self.scores, key=lambda s: s.score)

  @property
  def min_dimension(self) -> Optional[DimensionScore]:
    """Dimension with the lowest score."""
    if not self.scores:
      return None
    return min(self.scores, key=lambda s: s.score)

  def to_dict(self) -> Dict[str, Any]:
    """Serialize to dict for API responses."""
    result: Dict[str, Any] = {
      "total_score": self.total_score,
      "dimension_scores": [s.to_dict() for s in self.scores],
      "suggestions": self.suggestions,
    }
    if self.max_dimension:
      result["best_dimension"] = self.max_dimension.dimension.value
    if self.min_dimension:
      result["worst_dimension"] = self.min_dimension.dimension.value
    return result


class Evaluator:
  """Rule-based evaluator for agent conversation quality.

  Uses heuristic rules to score conversations across six dimensions,
  without requiring LLM calls.
  """

  def evaluate_conversation(
    self,
    messages: List[Dict[str, Any]],
    agent_traces: Optional[List[Dict[str, Any]]] = None,
  ) -> EvaluationReport:
    """Evaluate a full conversation.

    Args:
      messages: List of message dicts with 'role' and 'content' keys
      agent_traces: Optional list of agent execution trace dicts

    Returns:
      EvaluationReport with per-dimension scores and suggestions
    """
    traces = agent_traces or []
    scores: List[DimensionScore] = []
    suggestions: List[str] = []

    for dimension, config in _SCORING_FUNCTIONS.items():
      # Build args based on what the scoring function needs
      if config["args"] == ("messages", "traces"):
        raw_score, reason, details = config["fn"](messages, traces)
      else:
        raw_score, reason, details = config["fn"](messages)

      ds = DimensionScore(
        dimension=dimension,
        score=raw_score,
        reason=reason,
        details=details,
      )
      scores.append(ds)

      if ds.score < 4:
        suggestions.append(config["suggestion"])

    return EvaluationReport(scores=scores, suggestions=suggestions)

  def evaluate_single_turn(
    self,
    user_message: str,
    assistant_response: str,
    agent_trace: Optional[Dict[str, Any]] = None,
  ) -> EvaluationReport:
    """Evaluate a single turn (one user message + one response)."""
    messages = [
      {"role": "user", "content": user_message},
      {"role": "assistant", "content": assistant_response},
    ]
    traces = [agent_trace] if agent_trace else []
    return self.evaluate_conversation(messages, traces)

  def generate_report(
    self,
    evaluations: List[EvaluationReport],
  ) -> Dict[str, Any]:
    """Generate an aggregated report from multiple evaluations.

    Args:
      evaluations: List of EvaluationReport objects

    Returns:
      Dict with average scores, best/worst dimensions, and analysis
    """
    if not evaluations:
      return {"count": 0, "message": "No evaluations to aggregate"}

    dim_scores: Dict[str, List[int]] = {
      d.value: [] for d in EvaluationDimension
    }
    total_scores: List[float] = []

    for ev in evaluations:
      total_scores.append(ev.total_score)
      for ds in ev.scores:
        dim_scores[ds.dimension.value].append(ds.score)

    dim_averages: Dict[str, float] = {}
    for dim_name, scores_list in dim_scores.items():
      dim_averages[dim_name] = (
        round(statistics.mean(scores_list), 2)
        if scores_list else 0.0
      )

    avg_total = round(statistics.mean(total_scores), 2)
    best_dim = max(dim_averages, key=dim_averages.get)  # type: ignore[arg-type]
    worst_dim = min(dim_averages, key=dim_averages.get)  # type: ignore[arg-type]

    # Deduplicated suggestions
    all_suggestions: List[str] = []
    seen: set[str] = set()
    for ev in evaluations:
      for sug in ev.suggestions:
        if sug not in seen:
          seen.add(sug)
          all_suggestions.append(sug)

    problem_dims = [
      dim for dim, avg in dim_averages.items() if avg < 3.0
    ]

    return {
      "count": len(evaluations),
      "average_total_score": avg_total,
      "max_total_score": round(max(total_scores), 2),
      "min_total_score": round(min(total_scores), 2),
      "dimension_averages": dim_averages,
      "best_dimension": best_dim,
      "worst_dimension": worst_dim,
      "problem_dimensions": problem_dims,
      "suggestions": all_suggestions,
    }
