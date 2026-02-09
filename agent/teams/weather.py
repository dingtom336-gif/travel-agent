# Weather Agent – weather forecast specialist
from __future__ import annotations

import time
from typing import Any

from agent.models import AgentName, AgentResult, AgentTask, TaskStatus
from agent.teams.base import BaseAgent

SYSTEM_PROMPT = """You are the Weather Agent of TravelMind.
Your job is to provide weather forecasts and travel-related weather advice.

Given the user's travel parameters AND real weather data, provide:
1. Weather overview for the travel period.
2. Clothing and packing suggestions.
3. Weather impact on planned activities and tips.

Respond in the same language as the user's message.
Keep the answer concise and structured (use markdown)."""


class WeatherAgent(BaseAgent):
  name = AgentName.WEATHER
  description = "Queries weather forecasts for travel destinations."

  async def execute(self, task: AgentTask, context: dict[str, Any]) -> AgentResult:
    try:
      start = time.time()

      # Extract parameters
      params = task.params or {}
      city = params.get("city") or params.get("destination", "")
      date = params.get("date") or params.get("start_date", "")
      days = params.get("days") or params.get("duration_days", 5)

      tool_data = {}

      # Call weather tools
      if city and date:
        try:
          # Get multi-day forecast
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

      # Build prompt with tool results
      prompt = self._build_prompt(task, context, tool_data)
      response = await self._call_claude(SYSTEM_PROMPT, prompt)

      return self._make_result(
        task,
        summary=f"Weather forecast for {task.goal}",
        data={"response": response, "tool_data": tool_data},
        start_time=start,
      )
    except Exception as exc:
      return self._make_result(
        task, summary="Weather query failed",
        status=TaskStatus.FAILED, error=str(exc),
      )

