# Reflection engine – validates agent results and triggers corrections
# Layer 1: Rule-based preflight validation (0 LLM cost)
# Layer 2: LLM-powered consistency check (conditional, 1 LLM call)
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Optional

from agent.config.settings import get_settings
from agent.llm import llm_chat
from agent.models import AgentName, AgentResult, SessionState, TaskStatus

logger = logging.getLogger(__name__)


@dataclass
class ReflectionIssue:
  """A single issue found during reflection."""
  field: str          # "destination" / "budget" / "dates" / "agent_failure"
  severity: str       # "error" / "warning"
  message: str
  suggested_fix: dict = field(default_factory=dict)


@dataclass
class ReflectionResult:
  """Result of LLM consistency check."""
  passed: bool = True
  issues: list[dict] = field(default_factory=list)
  state_corrections: dict = field(default_factory=dict)


# Agents affected when a specific state field changes
FIELD_TO_AGENTS: dict[str, list[str]] = {
  "destination": ["transport", "hotel", "poi", "weather", "knowledge"],
  "origin": ["transport"],
  "start_date": ["transport", "hotel", "weather"],
  "end_date": ["transport", "hotel", "weather"],
  "duration_days": ["itinerary", "hotel"],
  "budget": ["budget"],
}


class PreflightValidator:
  """Layer 1: Rule-based validation, zero LLM cost."""

  def validate(
    self,
    results: dict[str, AgentResult],
    state: SessionState,
  ) -> list[ReflectionIssue]:
    issues: list[ReflectionIssue] = []
    issues.extend(self._check_agent_failures(results))
    issues.extend(self._check_destination_consistency(results, state))
    return issues

  def _check_agent_failures(
    self, results: dict[str, AgentResult],
  ) -> list[ReflectionIssue]:
    """Check if too many agents failed."""
    issues: list[ReflectionIssue] = []
    total = len(results)
    if total == 0:
      return issues

    failed = sum(1 for r in results.values() if r.status == TaskStatus.FAILED)
    critical_agents = {AgentName.TRANSPORT, AgentName.HOTEL, AgentName.POI}
    critical_failed = [
      r.agent.value for r in results.values()
      if r.status == TaskStatus.FAILED and r.agent in critical_agents
    ]

    if failed > total / 2:
      issues.append(ReflectionIssue(
        field="agent_failure",
        severity="error",
        message=f"{failed}/{total} agents failed",
      ))

    if len(critical_failed) == len(critical_agents):
      issues.append(ReflectionIssue(
        field="agent_failure",
        severity="error",
        message=f"All critical agents failed: {critical_failed}",
      ))

    return issues

  def _check_destination_consistency(
    self,
    results: dict[str, AgentResult],
    state: SessionState,
  ) -> list[ReflectionIssue]:
    """Check if agent responses use a different destination name than state."""
    issues: list[ReflectionIssue] = []
    if not state.destination:
      return issues

    dest = state.destination
    suspicious_names: dict[str, int] = {}

    for result in results.values():
      if result.status == TaskStatus.FAILED:
        continue
      response = result.data.get("response", "")
      if not isinstance(response, str):
        continue
      # Find destination-like names that are similar but not equal
      self._scan_for_variants(response, dest, suspicious_names)

    # If a variant appears in 2+ agent responses, flag it
    for variant, count in suspicious_names.items():
      if count >= 2:
        issues.append(ReflectionIssue(
          field="destination",
          severity="error",
          message=f"Agents used '{variant}' instead of '{dest}' ({count} occurrences)",
          suggested_fix={"destination": dest},
        ))

    return issues

  def _scan_for_variants(
    self,
    text: str,
    target: str,
    variants: dict[str, int],
  ) -> None:
    """Find strings similar to target in text using sliding window."""
    tlen = len(target)
    if tlen < 2:
      return

    # Find positions where target appears exactly (to exclude overlaps)
    exact_positions: set[int] = set()
    start = 0
    while True:
      idx = text.find(target, start)
      if idx == -1:
        break
      for p in range(idx, idx + tlen):
        exact_positions.add(p)
      start = idx + 1

    # Slide a window of same length as target
    seen: set[str] = set()
    for i in range(len(text) - tlen + 1):
      # Skip windows that overlap with exact target matches
      if any(p in exact_positions for p in range(i, i + tlen)):
        continue
      candidate = text[i : i + tlen]
      if candidate in seen:
        continue
      seen.add(candidate)
      ratio = SequenceMatcher(None, candidate, target).ratio()
      if ratio >= 0.5 and ratio < 1.0:
        variants[candidate] = variants.get(candidate, 0) + 1


REFLECTION_PROMPT = """You are a quality checker for a travel planning system.

User's original request: {user_message}
Extracted travel state: {state_ctx}

Agent results summary:
{results_summary}

Check for these issues:
1. DESTINATION: Is the destination name in state correct? Did the user make a typo that was not corrected? Are agents using the wrong name?
2. CONSISTENCY: Do agent results contradict each other (dates, locations, prices)?
3. COMPLETENESS: Did agents address all parts of the user's request?
4. FEASIBILITY: Is the total cost within the user's budget?

Return ONLY valid JSON (no markdown fences):
{{
  "passed": true,
  "issues": [],
  "state_corrections": {{}}
}}

If problems found, set passed=false and provide corrections:
{{
  "passed": false,
  "issues": [{{"field": "destination", "problem": "User typed X but meant Y"}}],
  "state_corrections": {{"destination": "corrected_name"}}
}}"""


class ConsistencyChecker:
  """Layer 2: LLM-powered cross-agent consistency check."""

  async def check(
    self,
    user_message: str,
    results: dict[str, AgentResult],
    state_ctx: str,
  ) -> ReflectionResult:
    """Run LLM consistency check. Returns ReflectionResult."""
    try:
      results_summary = self._build_summary(results)
      prompt = REFLECTION_PROMPT.format(
        user_message=user_message,
        state_ctx=state_ctx,
        results_summary=results_summary,
      )

      text = await llm_chat(
        system="You are a precise quality checker. Return only valid JSON.",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=256,
        temperature=0.1,
        model=get_settings().DEEPSEEK_REASONER_MODEL,
      )

      if text is None:
        logger.info("No API key for reflection – skipping")
        return ReflectionResult(passed=True)

      return self._parse_result(text)
    except Exception as exc:
      logger.warning("Consistency check failed: %s – skipping", exc)
      return ReflectionResult(passed=True)

  def _build_summary(self, results: dict[str, AgentResult]) -> str:
    """Build a compact summary of all agent results."""
    parts: list[str] = []
    for result in results.values():
      status = result.status.value
      response = result.data.get("response", result.summary)
      # Truncate long responses
      if isinstance(response, str) and len(response) > 300:
        response = response[:300] + "..."
      parts.append(f"[{result.agent.value}] ({status}): {response}")
    return "\n\n".join(parts)

  def _parse_result(self, text: str) -> ReflectionResult:
    """Parse LLM JSON response into ReflectionResult."""
    text = text.strip()
    if text.startswith("```"):
      text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
      data = json.loads(text)
      return ReflectionResult(
        passed=data.get("passed", True),
        issues=data.get("issues", []),
        state_corrections=data.get("state_corrections", {}),
      )
    except (json.JSONDecodeError, KeyError) as exc:
      logger.warning("Failed to parse reflection result: %s", exc)
      return ReflectionResult(passed=True)


def identify_affected_agents(
  reflection: ReflectionResult,
  results: dict[str, AgentResult],
) -> list[tuple[str, AgentResult]]:
  """Determine which agents need to be re-run based on state corrections."""
  affected_agent_names: set[str] = set()

  for field_name in reflection.state_corrections:
    agents = FIELD_TO_AGENTS.get(field_name, [])
    affected_agent_names.update(agents)

  # Return (agent_name, original_result) pairs for agents that were executed
  to_rerun: list[tuple[str, AgentResult]] = []
  for result in results.values():
    if result.agent.value in affected_agent_names and result.status != TaskStatus.FAILED:
      to_rerun.append((result.agent.value, result))

  return to_rerun


# Singletons
preflight_validator = PreflightValidator()
consistency_checker = ConsistencyChecker()
