# POI Agent – destination / attractions / restaurants / experiences specialist
from __future__ import annotations

import json
import time
from typing import Any

from agent.models import AgentName, AgentResult, AgentTask, TaskStatus
from agent.teams.base import BaseAgent

SYSTEM_PROMPT = """You are the POI (Point of Interest) Agent of TravelMind.
Your job is to recommend attractions, restaurants, shopping spots, and experiences.

Given the user's travel parameters AND real POI search results, provide:
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

      # Extract parameters
      params = task.params or {}
      city = params.get("city") or params.get("destination", "")
      category = params.get("category")
      limit = params.get("limit", 10)

      tool_data = {}

      # Call POI search tool
      if city:
        try:
          kwargs: dict[str, Any] = {"city": city, "limit": limit}
          if category:
            kwargs["category"] = category
          poi_result = await self.call_tool("search_pois", **kwargs)
          tool_data["pois"] = poi_result
        except Exception:
          pass

      # Build prompt with tool results
      prompt = self._build_prompt(task, context, tool_data)
      response = await self._call_claude(SYSTEM_PROMPT, prompt)

      return self._make_result(
        task,
        summary=f"POI recommendations generated for {task.goal}",
        data={"response": response, "tool_data": tool_data},
        start_time=start,
      )
    except Exception as exc:
      return self._make_result(
        task,
        summary="POI search failed",
        status=TaskStatus.FAILED,
        error=str(exc),
      )

  def _build_prompt(
    self,
    task: AgentTask,
    context: dict[str, Any],
    tool_data: dict[str, Any],
  ) -> str:
    """Compose prompt from task goal + context + tool results."""
    parts = [f"Task: {task.goal}"]
    if task.params:
      parts.append(f"Parameters: {task.params}")
    state_ctx = context.get("state_context", "")
    if state_ctx:
      parts.append(f"Current travel state:\n{state_ctx}")

    if tool_data:
      parts.append("=== Tool Results ===")
      for tool_name, result in tool_data.items():
        parts.append(f"--- {tool_name} ---")
        parts.append(json.dumps(result, ensure_ascii=False, default=str)[:3000])

    return "\n\n".join(parts)
