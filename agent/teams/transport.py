# Transport Agent – flight / train / bus / driving route specialist
from __future__ import annotations

from typing import Any

from agent.models import AgentName, AgentTask
from agent.teams.base import BaseAgent


class TransportAgent(BaseAgent):
  name = AgentName.TRANSPORT
  description = "Searches and recommends flights, trains, and other transport."
  _success_label = "Transport recommendations generated"
  _failure_label = "Transport search failed"

  system_prompt = """You are the Transport Agent of TravelMind.
Your job is to recommend transportation options (flights, trains, buses, driving routes).

Given the user's travel parameters AND real tool results, provide:
1. Top 2-3 transport options with estimated price, duration, and convenience rating.
2. Pros and cons for each option.
3. A clear recommendation.

Respond in the same language as the user's message.
Keep the answer concise and structured (use markdown).
If information is insufficient, state what assumptions you made."""

  async def _run_tools(
    self, task: AgentTask, context: dict[str, Any],
  ) -> dict[str, Any]:
    params = task.params or {}
    departure = params.get("departure") or params.get("origin", "")
    arrival = params.get("arrival") or params.get("destination", "")
    date = params.get("date") or params.get("start_date", "")
    passengers = params.get("passengers", 1)
    preference = params.get("preference", "balanced")

    tool_data: dict[str, Any] = {}

    if departure and arrival and date:
      try:
        transit_result = await self.call_tool(
          "optimize_transit",
          departure=departure,
          arrival=arrival,
          date=date,
          preferences=preference,
          passengers=passengers,
        )
        tool_data["transit"] = transit_result
      except Exception:
        # Fallback: try individual tools
        try:
          flight_result = await self.call_tool(
            "search_flights",
            departure=departure,
            arrival=arrival,
            date=date,
            passengers=passengers,
          )
          tool_data["flights"] = flight_result
        except Exception:
          pass

        try:
          distance_result = await self.call_tool(
            "get_distance",
            origin=departure,
            destination=arrival,
          )
          tool_data["distance"] = distance_result
        except Exception:
          pass

    return tool_data
