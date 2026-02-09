# Hotel Agent – accommodation specialist
from __future__ import annotations

import time
from typing import Any

from agent.models import AgentName, AgentResult, AgentTask, TaskStatus
from agent.teams.base import BaseAgent

SYSTEM_PROMPT = """You are the Hotel Agent of TravelMind.
Your job is to recommend accommodations (hotels, resorts, B&Bs) based on the user's needs.

Given the user's travel parameters AND real hotel search results, provide:
1. Top 2-3 hotel options with key highlights.
2. Comparison of price, location, facilities.
3. A clear recommendation with reasons.

Respond in the same language as the user's message.
Keep the answer concise and structured (use markdown)."""


class HotelAgent(BaseAgent):
  name = AgentName.HOTEL
  description = "Searches and recommends hotels and accommodations."

  async def execute(self, task: AgentTask, context: dict[str, Any]) -> AgentResult:
    try:
      start = time.time()

      # Extract parameters
      params = task.params or {}
      city = params.get("city") or params.get("destination", "")
      checkin = params.get("checkin") or params.get("start_date", "")
      checkout = params.get("checkout") or params.get("end_date", "")
      guests = params.get("guests") or params.get("travelers", 1)
      stars_min = params.get("stars_min")
      price_max = params.get("price_max")

      tool_data = {}

      # Call hotel search tool
      if city and checkin and checkout:
        try:
          kwargs: dict[str, Any] = {
            "city": city,
            "checkin": checkin,
            "checkout": checkout,
            "guests": guests,
          }
          if stars_min:
            kwargs["stars_min"] = stars_min
          if price_max:
            kwargs["price_max"] = price_max

          hotel_result = await self.call_tool("search_hotels", **kwargs)
          tool_data["hotels"] = hotel_result
        except Exception:
          pass

      # Build prompt with tool results
      prompt = self._build_prompt(task, context, tool_data)
      response = await self._call_claude(SYSTEM_PROMPT, prompt)

      return self._make_result(
        task,
        summary=f"Hotel recommendations for {task.goal}",
        data={"response": response, "tool_data": tool_data},
        start_time=start,
      )
    except Exception as exc:
      return self._make_result(
        task, summary="Hotel search failed",
        status=TaskStatus.FAILED, error=str(exc),
      )

