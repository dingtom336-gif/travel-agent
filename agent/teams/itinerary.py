# Itinerary Agent – trip schedule orchestration specialist
from __future__ import annotations

import time
from typing import Any

from agent.models import AgentName, AgentResult, AgentTask, TaskStatus
from agent.teams.base import BaseAgent

SYSTEM_PROMPT = """You are the Itinerary Agent of TravelMind.
Your job is to compile results from other agents into a coherent day-by-day travel plan.

Given upstream results (transport, POI, hotel, weather, etc.), produce:
1. A day-by-day schedule with timeline (morning / afternoon / evening).
2. Estimated time and distance between stops.
3. Tips for each day.

Respond in the same language as the user's message.
Format the itinerary in clear markdown with headers per day."""


class ItineraryAgent(BaseAgent):
  name = AgentName.ITINERARY
  description = "Compiles a day-by-day travel itinerary from upstream agent results."

  async def execute(self, task: AgentTask, context: dict[str, Any]) -> AgentResult:
    try:
      start = time.time()
      prompt = self._build_prompt(task, context)
      response = await self._call_claude(SYSTEM_PROMPT, prompt)
      return self._make_result(
        task,
        summary=f"Itinerary compiled for {task.goal}",
        data={"response": response},
        start_time=start,
      )
    except Exception as exc:
      return self._make_result(
        task,
        summary="Itinerary generation failed",
        status=TaskStatus.FAILED,
        error=str(exc),
      )

  def _build_prompt(self, task: AgentTask, context: dict[str, Any]) -> str:
    parts = [f"Task: {task.goal}"]
    if task.params:
      parts.append(f"Parameters: {task.params}")
    # Include upstream agent results
    upstream = context.get("upstream_results", {})
    if upstream:
      parts.append("Upstream agent results:")
      for agent_name, result_data in upstream.items():
        parts.append(f"--- {agent_name} ---\n{result_data}")
    state_ctx = context.get("state_context", "")
    if state_ctx:
      parts.append(f"Current travel state:\n{state_ctx}")
    return "\n\n".join(parts)
