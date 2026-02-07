# Knowledge Agent – visa / tips / culture specialist (stub)
from __future__ import annotations

import time
from typing import Any

from agent.models import AgentName, AgentResult, AgentTask, TaskStatus
from agent.teams.base import BaseAgent


class KnowledgeAgent(BaseAgent):
  name = AgentName.KNOWLEDGE
  description = "Provides visa info, travel tips, cultural advice."

  async def execute(self, task: AgentTask, context: dict[str, Any]) -> AgentResult:
    try:
      start = time.time()
      response = await self._call_claude(
        "You are the Knowledge Agent. Provide visa, cultural, and safety info.",
        f"Task: {task.goal}\nParams: {task.params}",
      )
      return self._make_result(
        task,
        summary=f"Knowledge lookup for {task.goal}",
        data={"response": response},
        start_time=start,
      )
    except Exception as exc:
      return self._make_result(
        task, summary="Knowledge lookup failed",
        status=TaskStatus.FAILED, error=str(exc),
      )
