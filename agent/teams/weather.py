# Weather Agent – weather forecast specialist (stub)
from __future__ import annotations

import time
from typing import Any

from agent.models import AgentName, AgentResult, AgentTask, TaskStatus
from agent.teams.base import BaseAgent


class WeatherAgent(BaseAgent):
  name = AgentName.WEATHER
  description = "Queries weather forecasts for travel destinations."

  async def execute(self, task: AgentTask, context: dict[str, Any]) -> AgentResult:
    try:
      start = time.time()
      response = await self._call_claude(
        "You are the Weather Agent. Provide weather forecasts and clothing advice.",
        f"Task: {task.goal}\nParams: {task.params}",
      )
      return self._make_result(
        task,
        summary=f"Weather forecast for {task.goal}",
        data={"response": response},
        start_time=start,
      )
    except Exception as exc:
      return self._make_result(
        task, summary="Weather query failed",
        status=TaskStatus.FAILED, error=str(exc),
      )
