# Customer Service Agent – after-sales / emergency specialist (stub)
from __future__ import annotations

import time
from typing import Any

from agent.models import AgentName, AgentResult, AgentTask, TaskStatus
from agent.teams.base import BaseAgent


class CustomerServiceAgent(BaseAgent):
  name = AgentName.CUSTOMER_SERVICE
  description = "Handles after-sales support, complaints, and emergencies."

  async def execute(self, task: AgentTask, context: dict[str, Any]) -> AgentResult:
    try:
      start = time.time()
      response = await self._call_claude(
        "You are the Customer Service Agent. Handle support and emergency requests.",
        f"Task: {task.goal}\nParams: {task.params}",
      )
      return self._make_result(
        task,
        summary=f"Customer service for {task.goal}",
        data={"response": response},
        start_time=start,
      )
    except Exception as exc:
      return self._make_result(
        task, summary="Customer service failed",
        status=TaskStatus.FAILED, error=str(exc),
      )
