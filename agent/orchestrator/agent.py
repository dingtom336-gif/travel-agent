# Orchestrator Agent – the central brain that coordinates everything
from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from agent.memory.profile import profile_manager
from agent.memory.session import session_memory
from agent.memory.state_pool import state_pool
from agent.models import SSEEventType, SSEMessage
from agent.orchestrator.constants import AGENT_REGISTRY  # noqa: F401 – re-export for tests
from agent.orchestrator.react_loop import ReactEngine
from agent.orchestrator.router import classify_complexity
from agent.orchestrator.state_extractor import extract_state
from agent.orchestrator.synthesis import Synthesizer

logger = logging.getLogger(__name__)

# Backwards-compat aliases used by tests that patch these names
agentDisplayNames = None  # kept for import compat; real data in constants.py


class OrchestratorAgent:
  """Central agent that drives the ReAct loop and coordinates specialist agents."""

  def __init__(self) -> None:
    self._react_engine = ReactEngine()
    self._synthesizer = Synthesizer()

  async def handle_message(
    self,
    session_id: str | None,
    message: str,
  ) -> AsyncGenerator[dict, None]:
    """Main entry point – yields SSE-formatted dicts."""
    try:
      if not session_id:
        session_id = str(uuid.uuid4())

      await session_memory.add_message(session_id, "user", message)

      user_id = session_id
      personalization_ctx = profile_manager.get_personalization_context(user_id)

      history = await session_memory.get_history(session_id)
      existing_state = await state_pool.get(session_id)
      has_travel_context = bool(existing_state and existing_state.destination)

      _, complexity = await asyncio.gather(
        extract_state(session_id, message, history, existing_state),
        classify_complexity(message, history, has_travel_context),
      )

      if complexity == "simple":
        async for chunk in self._synthesizer.handle_simple(
          session_id, message, history, personalization_ctx,
        ):
          yield chunk
        self._learn_from_session_safe(user_id, history)
        return

      # Complex → full ReAct loop
      state_ctx = await state_pool.to_prompt_context(session_id)
      if personalization_ctx:
        state_ctx += f"\n\n--- User Profile ---\n{personalization_ctx}"

      # Check if planner returns empty → fallback to simple
      has_tasks = False
      async for chunk in self._react_engine.run(
        session_id, message, history, state_ctx,
        personalization_ctx, self._synthesizer.synthesize_stream,
      ):
        has_tasks = True
        yield chunk

      if not has_tasks:
        async for chunk in self._synthesizer.handle_simple(
          session_id, message, history, personalization_ctx,
        ):
          yield chunk

      updated_history = await session_memory.get_history(session_id)
      self._learn_from_session_safe(user_id, updated_history)

    except Exception as exc:
      logger.exception("Orchestrator error")
      yield SSEMessage(
        event=SSEEventType.ERROR,
        data={"error": str(exc)},
      ).format()
      yield SSEMessage(
        event=SSEEventType.DONE,
        data={"session_id": session_id or ""},
      ).format()

  # Expose internal methods for test compatibility
  async def _execute_single_task(self, task: Any, context: Any) -> Any:
    """Delegate to ReactEngine for backward compatibility with tests."""
    return await self._react_engine._execute_single_task(task, context)

  def _learn_from_session_safe(
    self,
    user_id: str,
    history: list[dict[str, Any]],
  ) -> None:
    """Learn user preferences from session – never raises."""
    try:
      # learn_from_session is async but we fire-and-forget here
      asyncio.ensure_future(
        profile_manager.learn_from_session(user_id, history)
      )
    except Exception as exc:
      logger.warning("Profile learning failed (non-fatal): %s", exc)


# Singleton
orchestrator = OrchestratorAgent()
