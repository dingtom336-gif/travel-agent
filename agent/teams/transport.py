# Transport Agent – flight / train / bus / driving route specialist
from __future__ import annotations

import time
from typing import Any

from agent.models import AgentName, AgentResult, AgentTask, TaskStatus
from agent.teams.base import BaseAgent

SYSTEM_PROMPT = """You are the Transport Agent of TravelMind.
Your job is to recommend transportation options (flights, trains, buses, driving routes).

Given the user's travel parameters, provide:
1. Top 2-3 transport options with estimated price, duration, and convenience rating.
2. Pros and cons for each option.
3. A clear recommendation.

Respond in the same language as the user's message.
Keep the answer concise and structured (use markdown).
If information is insufficient, state what assumptions you made."""


class TransportAgent(BaseAgent):
  name = AgentName.TRANSPORT
  description = "Searches and recommends flights, trains, and other transport."

  async def execute(self, task: AgentTask, context: dict[str, Any]) -> AgentResult:
    try:
      start = time.time()
      prompt = self._build_prompt(task, context)
      response = await self._call_claude(SYSTEM_PROMPT, prompt)
      return self._make_result(
        task,
        summary=f"Transport recommendations generated for {task.goal}",
        data={"response": response},
        start_time=start,
      )
    except Exception as exc:
      return self._make_result(
        task,
        summary="Transport search failed",
        status=TaskStatus.FAILED,
        error=str(exc),
      )

  def _build_prompt(self, task: AgentTask, context: dict[str, Any]) -> str:
    """Compose prompt from task goal + context state."""
    parts = [f"Task: {task.goal}"]
    if task.params:
      parts.append(f"Parameters: {task.params}")
    state_ctx = context.get("state_context", "")
    if state_ctx:
      parts.append(f"Current travel state:\n{state_ctx}")
    return "\n\n".join(parts)
