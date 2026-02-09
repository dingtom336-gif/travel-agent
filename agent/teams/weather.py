# Weather Agent – weather forecast specialist
from __future__ import annotations

from typing import Any

from agent.models import AgentName, AgentTask
from agent.teams.base import BaseAgent


class WeatherAgent(BaseAgent):
  name = AgentName.WEATHER
  description = "Queries weather forecasts for travel destinations."
  _success_label = "Weather forecast"
  _failure_label = "Weather query failed"

  system_prompt = """You are the Weather Agent of TravelMind.
Your job is to provide weather forecasts and travel-related weather advice.

Given the user's travel parameters AND real weather data, provide:
1. Weather overview for the travel period.
2. Clothing and packing suggestions.
3. Weather impact on planned activities and tips.

Respond in the same language as the user's message.
Keep the answer concise and structured (use markdown)."""

  async def _run_tools(
    self, task: AgentTask, context: dict[str, Any],
  ) -> dict[str, Any]:
    params = task.params or {}
    city = params.get("city") or params.get("destination", "")
    date = params.get("date") or params.get("start_date", "")
    days = params.get("days") or params.get("duration_days", 5)

    tool_data: dict[str, Any] = {}

    if city and date:
      try:
        forecast_result = await self.call_tool(
          "get_weather_forecast",
          city=city,
          start_date=date,
          days=days,
        )
        tool_data["forecast"] = forecast_result
      except Exception:
        # Fallback to single-day weather
        try:
          weather_result = await self.call_tool(
            "get_weather",
            city=city,
            date=date,
          )
          tool_data["weather"] = weather_result
        except Exception:
          pass

    return tool_data
