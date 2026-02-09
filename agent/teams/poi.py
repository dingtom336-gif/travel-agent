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

CRITICAL RULES:
- ONLY recommend places that ACTUALLY EXIST in the real world.
- Use their official names (e.g., "东京国立博物馆" not "日本博物馆", "故宫博物院" not "北京博物馆").
- If tool search results are empty, use your own knowledge to recommend real places.
- For each place provide: name, category, rating (estimated), opening hours, ticket price, and a brief description.
- When tool results are empty, append a JSON block at the end of your response in this format:
```json
[{"name": "地点名", "category": "scenic|restaurant|shopping|activity|museum|park", "rating": 4.5, "hours": "09:00-17:00", "price": 0, "desc": "简短描述"}]
```

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

      # If tool returned no POIs, try to extract structured data from LLM response
      pois_result = tool_data.get("pois", {})
      has_pois = (
        isinstance(pois_result, dict)
        and pois_result.get("results")
        and len(pois_result["results"]) > 0
      )
      if not has_pois and response:
        extracted = self._extract_pois_from_response(response)
        if extracted:
          tool_data["pois"] = {
            "success": True,
            "results": extracted,
            "total_count": len(extracted),
            "query": {"city": city, "source": "llm"},
          }

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

  @staticmethod
  def _extract_pois_from_response(response: str) -> list[dict[str, Any]]:
    """Extract structured POI data from LLM response JSON block."""
    try:
      # Find JSON array in the response (between ```json and ```)
      import re
      match = re.search(r"```json\s*(\[[\s\S]*?\])\s*```", response)
      if not match:
        # Try bare JSON array
        match = re.search(r"(\[\s*\{[\s\S]*?\}\s*\])", response)
      if match:
        pois = json.loads(match.group(1))
        if isinstance(pois, list) and len(pois) > 0:
          return pois
    except (json.JSONDecodeError, AttributeError):
      pass
    return []
