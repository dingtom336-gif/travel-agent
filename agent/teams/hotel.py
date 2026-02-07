# Hotel Agent – accommodation specialist (stub)
from __future__ import annotations

import time
from typing import Any

from agent.models import AgentName, AgentResult, AgentTask, TaskStatus
from agent.teams.base import BaseAgent


class HotelAgent(BaseAgent):
  name = AgentName.HOTEL
  description = "Searches and recommends hotels and accommodations."

  async def execute(self, task: AgentTask, context: dict[str, Any]) -> AgentResult:
    try:
      start = time.time()
      response = await self._call_claude(
        "You are the Hotel Agent. Recommend accommodations based on the request.",
        f"Task: {task.goal}\nParams: {task.params}",
      )
      return self._make_result(
        task,
        summary=f"Hotel recommendations for {task.goal}",
        data={"response": response},
        start_time=start,
      )
    except Exception as exc:
      return self._make_result(
        task, summary="Hotel search failed",
        status=TaskStatus.FAILED, error=str(exc),
      )
