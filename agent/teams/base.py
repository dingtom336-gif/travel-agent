# Base class for all specialist agents
from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict

from agent.config.settings import get_settings
from agent.llm import llm_chat
from agent.models import AgentName, AgentResult, AgentTask, TaskStatus

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
  """Abstract base for every specialist agent.

  Subclasses must set `name` / `description` and implement `execute`.
  Provides a shared helper `_call_claude` that gracefully falls back
  to mock data when no API key is configured.
  Also provides `available_tools` and `call_tool` for tool-layer access.
  """

  name: AgentName
  description: str = ""

  # --- tool access ---

  @property
  def available_tools(self) -> Dict[str, Callable[..., Any]]:
    """Return tools registered for this agent from the global registry."""
    from agent.tools.registry import get_tools_for_agent
    return get_tools_for_agent(self.name.value)

  async def call_tool(self, tool_name: str, **kwargs: Any) -> Any:
    """Call a registered tool by name, with fault injection support.

    Args:
      tool_name: Name of the tool (e.g. "search_flights")
      **kwargs: Arguments to pass to the tool function

    Returns:
      Tool result (usually a dict)

    Raises:
      ValueError: If tool is not found or not authorised for this agent
    """
    tools = self.available_tools
    func = tools.get(tool_name)
    if func is None:
      raise ValueError(
        f"Tool '{tool_name}' not available for agent '{self.name.value}'. "
        f"Available: {list(tools.keys())}"
      )

    # Fault injection: check for simulated faults before calling
    from agent.simulator.env_simulator import get_env_simulator
    env_sim = get_env_simulator()

    if env_sim.is_fault_active("tool_timeout"):
      if env_sim.should_trigger_fault("tool_timeout"):
        config = env_sim._active_faults["tool_timeout"]
        timeout_ms = config.params.get("timeout_ms", 5000)
        affected = config.params.get("affected_tools", ["all"])
        if "all" in affected or tool_name in affected:
          import asyncio
          logger.warning(
            "FAULT INJECTED: timeout %dms for %s.%s",
            timeout_ms, self.name.value, tool_name,
          )
          await asyncio.sleep(timeout_ms / 1000.0)
          raise TimeoutError(f"Simulated timeout for {tool_name}")

    if env_sim.is_fault_active("tool_error"):
      if env_sim.should_trigger_fault("tool_error"):
        config = env_sim._active_faults["tool_error"]
        affected = config.params.get("affected_tools", ["all"])
        if "all" in affected or tool_name in affected:
          error_msg = config.params.get(
            "error_message", "Simulated tool error",
          )
          logger.warning(
            "FAULT INJECTED: error for %s.%s: %s",
            self.name.value, tool_name, error_msg,
          )
          raise RuntimeError(error_msg)

    try:
      result = await func(**kwargs)

      # Fault injection: apply price modifier to results
      if env_sim.is_fault_active("price_change"):
        modifier = env_sim.get_price_modifier()
        if modifier != 1.0:
          result = self._apply_price_modifier(result, modifier)

      logger.info(
        "Agent %s called tool %s -> success=%s",
        self.name.value, tool_name, result.get("success", "n/a"),
      )
      return result
    except Exception as exc:
      logger.error(
        "Agent %s tool %s failed: %s",
        self.name.value, tool_name, exc,
      )
      raise

  @staticmethod
  def _apply_price_modifier(result: Any, modifier: float) -> Any:
    """Apply price multiplier to tool results containing price fields."""
    if not isinstance(result, dict):
      return result
    price_keys = ("price", "price_per_night", "ticket_price", "total_price")
    for key in price_keys:
      if key in result and isinstance(result[key], (int, float)):
        result[key] = round(result[key] * modifier)
    # Handle nested results list
    for item in result.get("results", []):
      if isinstance(item, dict):
        for key in price_keys:
          if key in item and isinstance(item[key], (int, float)):
            item[key] = round(item[key] * modifier)
    return result

  # --- abstract ---

  @abstractmethod
  async def execute(self, task: AgentTask, context: dict[str, Any]) -> AgentResult:
    """Run the task and return a result."""
    ...

  # --- helpers ---

  def _build_prompt(
    self,
    task: AgentTask,
    context: dict[str, Any],
    tool_data: dict[str, Any],
  ) -> str:
    """Compose prompt from task goal + context + tool results.

    Subclasses may override to add extra sections (e.g. upstream results).
    """
    parts = [f"Task: {task.goal}"]
    if task.params:
      parts.append(f"Parameters: {task.params}")
    state_ctx = context.get("state_context", "")
    if state_ctx:
      parts.append(f"Current travel state:\n{state_ctx}")

    if tool_data:
      parts.append("=== Tool Results ===")
      for tool_name, result in tool_data.items():
        parts.append(f"--- {tool_name} ---")
        parts.append(json.dumps(result, ensure_ascii=False, default=str)[:3000])

    return "\n\n".join(parts)

  async def _call_claude(
    self,
    system_prompt: str,
    user_message: str,
    max_tokens: int | None = None,
  ) -> str:
    """Call LLM API. Falls back to a mock response when key is missing."""
    settings = get_settings()
    try:
      result = await llm_chat(
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
        max_tokens=max_tokens or settings.LLM_AGENT_TOKENS,
      )
      if result is None:
        return self._mock_response(user_message)
      return result
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
