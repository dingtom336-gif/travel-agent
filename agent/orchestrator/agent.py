# Orchestrator Agent – the central brain that coordinates everything
# v0.7.0: Immediate SSE feedback, heuristic fast-path, TIMING logs
# v0.8.0: Theater mode – single mega-LLM call with three-way intent routing
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from agent.config.settings import get_settings
from agent.memory.profile import profile_manager
from agent.memory.session import session_memory
from agent.memory.state_pool import state_pool
from agent.models import SSEEventType, SSEMessage
from agent.orchestrator.constants import AGENT_REGISTRY  # noqa: F401 – re-export for tests
from agent.orchestrator.context import build_context_with_summary
from agent.orchestrator.react_loop import ReactEngine
from agent.orchestrator.router import classify_complexity, classify_intent
from agent.orchestrator.state_extractor import extract_state, heuristic_extract
from agent.orchestrator.synthesis import Synthesizer
from agent.orchestrator.theater import handle_clarify, theater_handle

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
    """Main entry point – yields SSE-formatted dicts.

    When THEATER_MODE is enabled, uses three-way intent routing:
      simple  → handle_simple (quick chat)
      clarify → handle_clarify (warm info gathering)
      plan    → theater_handle (mega single-call planning)

    When THEATER_MODE is disabled, falls back to legacy ReAct loop.
    """
    total_start = time.time()
    try:
      if not session_id:
        session_id = str(uuid.uuid4())

      # IMMEDIATE feedback – before ANY async work
      yield SSEMessage(
        event=SSEEventType.THINKING,
        data={"agent": "orchestrator", "thought": "正在分析你的需求..."},
      ).format()

      await session_memory.add_message(session_id, "user", message)

      user_id = session_id
      personalization_ctx = profile_manager.get_personalization_context(user_id)

      history = await session_memory.get_history(session_id)
      existing_state = await state_pool.get(session_id)
      has_travel_context = bool(existing_state and existing_state.destination)

      settings = get_settings()

      # ── Theater Mode path ──
      if settings.THEATER_MODE:
        # Parallel: heuristic state extraction + LLM intent classification
        t0 = time.time()
        heuristic_task = asyncio.ensure_future(
          heuristic_extract(session_id, message, existing_state)
        )
        classify_result = await classify_intent(message, history, has_travel_context)
        await heuristic_task  # Ensure heuristic completes before proceeding
        intent = classify_result["intent"]
        use_thinking = classify_result.get("thinking", False)
        logger.info(
          "TIMING stage=theater_classify intent=%s thinking=%s reason=%s duration_ms=%d session=%s",
          intent, use_thinking, classify_result.get("reason", ""),
          int((time.time() - t0) * 1000), session_id,
        )

        # Fire-and-forget LLM state extraction for enrichment
        asyncio.ensure_future(
          extract_state(session_id, message, history, existing_state)
        )

        if intent == "simple":
          async for chunk in self._synthesizer.handle_simple(
            session_id, message, history, personalization_ctx,
          ):
            yield chunk
          self._learn_from_session_safe(user_id, history)
          total_ms = int((time.time() - total_start) * 1000)
          logger.info("TIMING stage=total_theater_simple duration_ms=%d session=%s", total_ms, session_id)
          return

        state_ctx = await state_pool.to_prompt_context(session_id)

        if intent == "clarify":
          async for chunk in handle_clarify(
            session_id, message, history, state_ctx,
          ):
            yield chunk
          self._learn_from_session_safe(user_id, history)
          total_ms = int((time.time() - total_start) * 1000)
          logger.info("TIMING stage=total_theater_clarify duration_ms=%d session=%s", total_ms, session_id)
          return

        # intent == "plan" — pass thinking flag to theater
        async for chunk in theater_handle(
          session_id, message, history, state_ctx, personalization_ctx,
          use_thinking=use_thinking,
        ):
          yield chunk

        updated_history = await session_memory.get_history(session_id)
        self._learn_from_session_safe(user_id, updated_history)
        total_ms = int((time.time() - total_start) * 1000)
        logger.info("TIMING stage=total_theater_plan duration_ms=%d session=%s", total_ms, session_id)
        return

      # ── Legacy ReAct path (THEATER_MODE=false) ──
      if has_travel_context:
        complexity = "complex"
        t0 = time.time()
        _, conversation_summary = await asyncio.gather(
          extract_state(session_id, message, history, existing_state),
          build_context_with_summary(history),
        )
        logger.info(
          "TIMING stage=followup_state+context duration_ms=%d session=%s",
          int((time.time() - t0) * 1000), session_id,
        )
      else:
        t0 = time.time()
        await heuristic_extract(session_id, message, existing_state)
        complexity = classify_complexity(message, history, has_travel_context)
        if asyncio.iscoroutine(complexity):
          complexity = await complexity
        logger.info(
          "TIMING stage=heuristic_classify duration_ms=%d session=%s",
          int((time.time() - t0) * 1000), session_id,
        )
        conversation_summary = None
        asyncio.ensure_future(
          extract_state(session_id, message, history, existing_state)
        )

      if complexity == "simple":
        async for chunk in self._synthesizer.handle_simple(
          session_id, message, history, personalization_ctx,
        ):
          yield chunk
        self._learn_from_session_safe(user_id, history)
        total_ms = int((time.time() - total_start) * 1000)
        logger.info("TIMING stage=total_simple duration_ms=%d session=%s", total_ms, session_id)
        return

      # Complex → full ReAct loop
      state_ctx = await state_pool.to_prompt_context(session_id)
      if personalization_ctx:
        state_ctx += f"\n\n--- User Profile ---\n{personalization_ctx}"

      has_tasks = False
      async for chunk in self._react_engine.run(
        session_id, message, history, state_ctx,
        personalization_ctx, self._synthesizer.synthesize_stream,
        conversation_summary=conversation_summary,
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
      total_ms = int((time.time() - total_start) * 1000)
      logger.info("TIMING stage=total_complex duration_ms=%d session=%s", total_ms, session_id)

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
      asyncio.ensure_future(
        profile_manager.learn_from_session(user_id, history)
      )
    except Exception as exc:
      logger.warning("Profile learning failed (non-fatal): %s", exc)


# Singleton
orchestrator = OrchestratorAgent()
