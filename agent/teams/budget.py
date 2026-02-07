# Budget Agent – cost estimation specialist (stub)
from __future__ import annotations

import time
from typing import Any

from agent.models import AgentName, AgentResult, AgentTask, TaskStatus
from agent.teams.base import BaseAgent


class BudgetAgent(BaseAgent):
  name = AgentName.BUDGET
  description = "Estimates costs and manages travel budget."

  async def execute(self, task: AgentTask, context: dict[str, Any]) -> AgentResult:
    try:
      start = time.time()
      response = await self._call_claude(
        "You are the Budget Agent. Estimate costs and provide budget advice.",
        f"Task: {task.goal}\nParams: {task.params}",
      )
      return self._make_result(
        task,
        summary=f"Budget analysis for {task.goal}",
        data={"response": response},
        start_time=start,
      )
    except Exception as exc:
      return self._make_result(
        task, summary="Budget analysis failed",
        status=TaskStatus.FAILED, error=str(exc),
      )
