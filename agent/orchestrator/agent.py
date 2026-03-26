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
from agent.orchestrator.context import build_context_with_summary, update_running_summary
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

  async def _update_summary_safe(
    self,
    session_id: str,
    message: str,
  ) -> None:
    """Update running conversation summary – non-critical, never raises."""
    try:
      existing_summary = await session_memory.get_summary(session_id)
      latest_hist = await session_memory.get_history(session_id)
      assistant_msgs = [m["content"] for m in latest_hist if m["role"] == "assistant"]
      last_assistant = assistant_msgs[-1] if assistant_msgs else ""
      new_summary = update_running_summary(existing_summary, message, last_assistant)
      await session_memory.update_summary(session_id, new_summary)
    except Exception:
      pass  # Non-critical, don't block response

  async def handle_message(
    self,
    session_id: str | None,
    message: str,
    deep_reasoning: bool = False,
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

      # Early unsafe check — works regardless of Theater/ReAct mode
      from agent.orchestrator.synthesis import _smart_fallback, _UNSAFE_REQUEST_KW
      msg_lower = message.strip().lower()
      if any(w in msg_lower for w in _UNSAFE_REQUEST_KW):
        refusal = _smart_fallback(message)
        yield SSEMessage(
          event=SSEEventType.TEXT,
          data={"content": refusal},
        ).format()
        await session_memory.add_message(session_id, "assistant", refusal)
        yield SSEMessage(
          event=SSEEventType.DONE,
          data={"session_id": session_id},
        ).format()
        total_ms = int((time.time() - total_start) * 1000)
        logger.info("TIMING stage=total_unsafe_early duration_ms=%d session=%s", total_ms, session_id)
        return

      user_id = session_id
      personalization_ctx = profile_manager.get_personalization_context(user_id)

      history = await session_memory.get_history(session_id)
      existing_state = await state_pool.get(session_id)
      has_travel_context = bool(existing_state and existing_state.destination)

      settings = get_settings()

      # ── Theater Mode path (skipped when deep_reasoning=True) ──
      use_theater = settings.THEATER_MODE and not deep_reasoning
      if use_theater:
        # Parallel: heuristic state extraction + LLM intent classification
        t0 = time.time()
        heuristic_task = asyncio.create_task(
          heuristic_extract(session_id, message, existing_state)
        )
        classify_result = await classify_intent(message, history, has_travel_context)
        await heuristic_task  # Ensure heuristic completes before proceeding
        intent = classify_result["intent"]
        use_thinking = classify_result.get("thinking", False)
        reason = classify_result.get("reason", "")
        logger.info(
          "TIMING stage=theater_classify intent=%s thinking=%s reason=%s duration_ms=%d session=%s",
          intent, use_thinking, reason,
          int((time.time() - t0) * 1000), session_id,
        )

        # Unsafe requests: direct refusal without LLM call
        if reason == "unsafe_request":
          from agent.orchestrator.synthesis import _smart_fallback
          refusal = _smart_fallback(message)
          yield SSEMessage(
            event=SSEEventType.TEXT,
            data={"content": refusal},
          ).format()
          await session_memory.add_message(session_id, "assistant", refusal)
          yield SSEMessage(
            event=SSEEventType.DONE,
            data={"session_id": session_id},
          ).format()
          total_ms = int((time.time() - total_start) * 1000)
          logger.info("TIMING stage=total_theater_unsafe duration_ms=%d session=%s", total_ms, session_id)
          return

        # Fire-and-forget LLM state extraction for enrichment
        asyncio.create_task(
          extract_state(session_id, message, history, existing_state)
        )

        if intent == "simple":
          async for chunk in self._synthesizer.handle_simple(
            session_id, message, history, personalization_ctx,
          ):
            yield chunk
          await self._update_summary_safe(session_id, message)
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
          await self._update_summary_safe(session_id, message)
          self._learn_from_session_safe(user_id, history)
          total_ms = int((time.time() - total_start) * 1000)
          logger.info("TIMING stage=total_theater_clarify duration_ms=%d session=%s", total_ms, session_id)
          return

        if intent == "search":
          from agent.orchestrator.search_handler import handle_search
          async for chunk in handle_search(
            session_id, message, history, state_ctx,
          ):
            yield chunk
          await self._update_summary_safe(session_id, message)
          self._learn_from_session_safe(user_id, history)
          total_ms = int((time.time() - total_start) * 1000)
          logger.info("TIMING stage=total_theater_search duration_ms=%d session=%s", total_ms, session_id)
          return

        # intent == "plan" — pass thinking flag to theater
        async for chunk in theater_handle(
          session_id, message, history, state_ctx, personalization_ctx,
          use_thinking=use_thinking,
        ):
          yield chunk

        await self._update_summary_safe(session_id, message)
        updated_history = await session_memory.get_history(session_id)
        self._learn_from_session_safe(user_id, updated_history)
        total_ms = int((time.time() - total_start) * 1000)
        logger.info("TIMING stage=total_theater_plan duration_ms=%d session=%s", total_ms, session_id)
        return

      # ── Deep reasoning: pre-filter before ReAct ──
      # When deep_reasoning=True, skip all fast paths — force full ReAct loop.
      # Only booking/after-sales bypass in non-deep mode.
      if not deep_reasoning:
        _BOOKING_KW = (
          "取消政策", "免费取消", "退款", "退差价", "改签", "退票",
          "订单查询", "订单号", "已预订", "已下单", "客服电话",
          "投诉电话", "退酒店", "退房", "退机票", "赔偿标准",
        )
        if any(k in msg_lower for k in _BOOKING_KW):
          async for chunk in self._synthesizer.handle_simple(
            session_id, message, history, personalization_ctx,
          ):
            yield chunk
          await self._update_summary_safe(session_id, message)
          total_ms = int((time.time() - total_start) * 1000)
          logger.info("TIMING stage=total_dr_booking duration_ms=%d session=%s", total_ms, session_id)
          return

      # ── Legacy ReAct path ──
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
        asyncio.create_task(
          extract_state(session_id, message, history, existing_state)
        )

      # When deep_reasoning=True, force complex path regardless of classify result
      if deep_reasoning:
        complexity = "complex"

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

      has_text = False
      had_error = False
      async for chunk in self._react_engine.run(
        session_id, message, history, state_ctx,
        personalization_ctx, self._synthesizer.synthesize_stream,
        conversation_summary=conversation_summary,
      ):
        event_type = chunk.get("event")
        if event_type == "text":
          has_text = True
        elif event_type == "error":
          had_error = True
        yield chunk

      # Safety net: if ReAct produced no text and no error, fallback to direct LLM
      if not has_text and not had_error:
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
      asyncio.create_task(
        profile_manager.learn_from_session(user_id, history)
      )
    except Exception as exc:
      logger.warning("Profile learning failed (non-fatal): %s", exc)


# Singleton
orchestrator = OrchestratorAgent()
