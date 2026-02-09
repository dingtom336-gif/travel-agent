# Hotel Agent – accommodation specialist
from __future__ import annotations

from typing import Any

from agent.models import AgentName, AgentTask
from agent.teams.base import BaseAgent


class HotelAgent(BaseAgent):
  name = AgentName.HOTEL
  description = "Searches and recommends hotels and accommodations."
  _success_label = "Hotel recommendations"
  _failure_label = "Hotel search failed"

  system_prompt = """You are the Hotel Agent of TravelMind.
Your job is to recommend accommodations (hotels, resorts, B&Bs) based on the user's needs.

Given the user's travel parameters AND real hotel search results, provide:
1. Top 2-3 hotel options with key highlights.
2. Comparison of price, location, facilities.
3. A clear recommendation with reasons.

Respond in the same language as the user's message.
Keep the answer concise and structured (use markdown)."""

  async def _run_tools(
    self, task: AgentTask, context: dict[str, Any],
  ) -> dict[str, Any]:
    params = task.params or {}
    city = params.get("city") or params.get("destination", "")
    checkin = params.get("checkin") or params.get("start_date", "")
    checkout = params.get("checkout") or params.get("end_date", "")
    guests = params.get("guests") or params.get("travelers", 1)
    stars_min = params.get("stars_min")
    price_max = params.get("price_max")

    tool_data: dict[str, Any] = {}

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

    return tool_data
