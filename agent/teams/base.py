# Base class for all specialist agents
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

import anthropic

from agent.config.settings import get_settings
from agent.models import AgentName, AgentResult, AgentTask, TaskStatus


class BaseAgent(ABC):
  """Abstract base for every specialist agent.

  Subclasses must set `name` / `description` and implement `execute`.
  Provides a shared helper `_call_claude` that gracefully falls back
  to mock data when no API key is configured.
  """

  name: AgentName
  description: str = ""

  # --- abstract ---

  @abstractmethod
  async def execute(self, task: AgentTask, context: dict[str, Any]) -> AgentResult:
    """Run the task and return a result."""
    ...

  # --- helpers ---

  async def _call_claude(
    self,
    system_prompt: str,
    user_message: str,
    max_tokens: int | None = None,
  ) -> str:
    """Call Claude API. Falls back to a mock response when key is missing."""
    settings = get_settings()
    if not settings.ANTHROPIC_API_KEY:
      return self._mock_response(user_message)

    try:
      client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
      response = await client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=max_tokens or settings.CLAUDE_MAX_TOKENS,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
      )
      return response.content[0].text
    except Exception as exc:
      return self._mock_response(user_message, error=str(exc))

  def _mock_response(self, user_message: str, error: str | None = None) -> str:
    """Return a plausible mock response for development without an API key."""
    prefix = f"[MOCK - {self.name.value}]"
    if error:
      prefix += f" (API error: {error})"
    return (
      f"{prefix} This is a simulated response for: "
      f"{user_message[:120]}..."
    )

  def _make_result(
    self,
    task: AgentTask,
    summary: str,
    data: dict[str, Any] | None = None,
    status: TaskStatus = TaskStatus.SUCCESS,
    error: str | None = None,
    start_time: float | None = None,
  ) -> AgentResult:
    """Convenience builder for AgentResult."""
    duration = int((time.time() - start_time) * 1000) if start_time else 0
    return AgentResult(
      task_id=task.task_id,
      agent=self.name,
      status=status,
      summary=summary,
      data=data or {},
      error=error,
      duration_ms=duration,
    )
