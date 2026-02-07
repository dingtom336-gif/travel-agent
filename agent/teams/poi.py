# POI Agent – destination / attractions / restaurants / experiences specialist
from __future__ import annotations

import time
from typing import Any

from agent.models import AgentName, AgentResult, AgentTask, TaskStatus
from agent.teams.base import BaseAgent

SYSTEM_PROMPT = """You are the POI (Point of Interest) Agent of TravelMind.
Your job is to recommend attractions, restaurants, shopping spots, and experiences.

Given the user's travel parameters, provide:
1. A curated list of 3-5 must-visit places with short descriptions.
2. Hidden gems or off-the-beaten-path suggestions.
3. Practical info: opening hours, ticket prices, best visiting time.

Respond in the same language as the user's message.
Keep the answer concise and structured (use markdown)."""


class POIAgent(BaseAgent):
  name = AgentName.POI
  description = "Recommends attractions, restaurants, and local experiences."

  async def execute(self, task: AgentTask, context: dict[str, Any]) -> AgentResult:
    try:
      start = time.time()
      prompt = self._build_prompt(task, context)
      response = await self._call_claude(SYSTEM_PROMPT, prompt)
      return self._make_result(
        task,
        summary=f"POI recommendations generated for {task.goal}",
        data={"response": response},
        start_time=start,
      )
    except Exception as exc:
      return self._make_result(
        task,
        summary="POI search failed",
        status=TaskStatus.FAILED,
        error=str(exc),
      )

  def _build_prompt(self, task: AgentTask, context: dict[str, Any]) -> str:
    parts = [f"Task: {task.goal}"]
    if task.params:
      parts.append(f"Parameters: {task.params}")
    state_ctx = context.get("state_context", "")
    if state_ctx:
      parts.append(f"Current travel state:\n{state_ctx}")
    return "\n\n".join(parts)
