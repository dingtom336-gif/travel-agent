# Theater Orchestrator – compressed ReAct: Think → Act → Observe → Reflect
# Single mega-LLM call replaces N agent calls. "Theater" steps give UX feedback
# while the LLM streams section-by-section output.
from __future__ import annotations

import asyncio
import logging
from collections import OrderedDict
from collections.abc import AsyncGenerator
from typing import Any, Optional

from agent.config.mega_prompt import (
  CLARIFY_SYSTEM_PROMPT,
  INCREMENTAL_PROMPT_TEMPLATE,
  MEGA_SYSTEM_PROMPT,
)
from agent.config.settings import get_settings
from agent.llm import llm_chat_stream
from agent.memory.session import session_memory
from agent.memory.state_pool import state_pool
from agent.models import SSEEventType, SSEMessage
from agent.orchestrator.prefetch import (
  _detect_state_changes,
  _format_state_changes,
  _guess_affected_sections,
  _snapshot_state,
  gather_tool_data,
)
from agent.orchestrator.section_parser import SectionDetector, StreamBuffer
from agent.orchestrator.state_extractor import heuristic_extract
from agent.orchestrator.synthesis import _smart_fallback
from agent.orchestrator.synthesis_prompt import (
  _stream_fix,
  _stream_llm_to_buffer,
  build_mega_prompt,
  quality_gate,
)
from agent.orchestrator.ui_mapper import extract_ui_components

logger = logging.getLogger(__name__)

# Session-level cache: session_id → last mega output text (bounded LRU)
_MEGA_CACHE_MAX = 500
_mega_cache: OrderedDict[str, str] = OrderedDict()


def _mega_cache_set(session_id: str, text: str) -> None:
  """Write to _mega_cache with LRU eviction."""
  _mega_cache[session_id] = text
  _mega_cache.move_to_end(session_id)
  while len(_mega_cache) > _MEGA_CACHE_MAX:
    _mega_cache.popitem(last=False)


# Theater performance steps: (section_name, display_text, delay_seconds)
THEATER_STEPS = [
  ("knowledge", "查询签证政策和旅行贴士", 0.5),
  ("weather", "分析旅行期间天气状况", 0.8),
  ("transport", "搜索最优交通方案", 1.2),
  ("hotel", "筛选高性价比住宿", 1.6),
  ("poi", "发掘目的地精彩体验", 2.0),
]

# Required sections for a complete plan
REQUIRED_SECTIONS = {"knowledge", "weather", "transport", "hotel", "poi", "itinerary"}


# ------------------------------------------------------------------ #
# SSE event helpers
# ------------------------------------------------------------------ #

def _thinking(thought: str) -> dict:
  """Build a THINKING SSE event dict."""
  return SSEMessage(
    event=SSEEventType.THINKING,
    data={"agent": "orchestrator", "thought": thought},
  ).format()


def _agent_start(agent: str, task: str) -> dict:
  """Build an AGENT_START SSE event dict."""
  return SSEMessage(
    event=SSEEventType.AGENT_START,
    data={"agent": agent, "task": task},
  ).format()


def _agent_result(agent: str, summary: str, data: dict) -> dict:
  """Build an AGENT_RESULT SSE event dict."""
  return SSEMessage(
    event=SSEEventType.AGENT_RESULT,
    data={
      "agent": agent,
      "status": "success",
      "summary": summary,
      "data": data,
    },
  ).format()


def _text(content: str) -> dict:
  """Build a TEXT SSE event dict."""
  return SSEMessage(
    event=SSEEventType.TEXT,
    data={"content": content},
  ).format()


def _done(session_id: str) -> dict:
  """Build a DONE SSE event dict."""
  return SSEMessage(
    event=SSEEventType.DONE,
    data={"session_id": session_id},
  ).format()


def _error(msg: str) -> dict:
  """Build an ERROR SSE event dict."""
  return SSEMessage(
    event=SSEEventType.ERROR,
    data={"error": msg},
  ).format()


# ------------------------------------------------------------------ #
# Main entry: theater_handle
# ------------------------------------------------------------------ #

async def theater_handle(
  session_id: str,
  message: str,
  history: list[dict[str, Any]],
  state_ctx: str,
  personalization_ctx: str = "",
  use_thinking: bool = False,
) -> AsyncGenerator[dict, None]:
  """Theater Mode main entry – compressed ReAct: Think → Act → Observe → Reflect.

  Args:
    use_thinking: Whether Stage 1 should use deep thinking (set by LLM classifier).
  Yields SSE dicts compatible with existing frontend.
  """
  try:
    # -- Think: immediate feedback + state extraction --
    yield _thinking("正在分析你的需求...")

    # Snapshot old state before extraction for incremental diff
    existing_state = await state_pool.get(session_id)
    old_state_snapshot = _snapshot_state(existing_state)
    await heuristic_extract(session_id, message, existing_state)
    state = await state_pool.get(session_id)
    state_ctx = await state_pool.to_prompt_context(session_id)

    # -- Incremental mode: if cached output exists and changes are small --
    previous_output = _mega_cache.get(session_id)
    state_changes = _detect_state_changes(old_state_snapshot, state)
    is_incremental = (
      previous_output
      and len(state_changes) <= 3  # relaxed from 2 to allow more follow-ups
      and "destination" not in state_changes  # destination change -> full replan
    )

    if is_incremental:
      logger.info(
        "THEATER incremental mode: %d state changes session=%s",
        len(state_changes), session_id[:8],
      )
      yield _thinking("正在增量更新方案...")

      # Only show affected agent steps (2-3 at most)
      affected_sections = _guess_affected_sections(state_changes)
      for section in affected_sections:
        display = next(
          (d for n, d, _ in THEATER_STEPS if n == section),
          f"正在更新 {section}...",
        )
        yield _agent_start(section, display)

      # Single LLM call with incremental prompt
      inc_prompt = INCREMENTAL_PROMPT_TEMPLATE.format(
        previous_output=previous_output[:4000],
        user_message=message,
        state_changes=_format_state_changes(state_changes),
      )
      settings = get_settings()
      full_text = ""
      try:
        async for chunk in llm_chat_stream(
          system=MEGA_SYSTEM_PROMPT,
          messages=[{"role": "user", "content": inc_prompt}],
          max_tokens=settings.LLM_MAX_TOKENS,
          model=settings.WRITING_MODEL,
        ):
          if chunk:
            full_text += chunk
            yield _text(chunk)
      except Exception as inc_exc:
        logger.warning("Incremental stream failed: %s, falling back to full", inc_exc)
        is_incremental = False  # Fall through to full mode below

      if is_incremental and full_text:
        _mega_cache_set(session_id, full_text)
        await session_memory.add_message(session_id, "assistant", full_text)
        yield _done(session_id)
        return

    # -- Full mode: Act -> parallel LLM + theater performance --
    yield _thinking("正在分解你的需求为子任务...")

    # Emit all AGENT_START events upfront so user sees agents "activating"
    # during Stage1 wait. theater_with_sections will skip re-emitting these.
    early_started: set[str] = set()
    for section, goal, _ in THEATER_STEPS:
      yield _agent_start(section, goal)
      early_started.add(section)

    # Gather tool data in parallel (mock tools, fast)
    tool_data = await gather_tool_data(state)

    # Emit UI component cards from tool data (same format as old ReAct path)
    if tool_data:
      ui_tool_map = {}
      # transport: ui_mapper looks for "flights" or "transit"
      if "flights" in tool_data:
        ui_tool_map["transport"] = {"flights": tool_data["flights"]}
      # hotel: ui_mapper looks for "hotels" with {results:[...]}
      if "hotels" in tool_data:
        ui_tool_map["hotel"] = {"hotels": tool_data["hotels"]}
      # poi: ui_mapper looks for "pois" with {results:[...]}
      if "pois" in tool_data:
        ui_tool_map["poi"] = {"pois": tool_data["pois"]}
      # weather: ui_mapper looks for "forecast" with {forecast:[...], query:{city}}
      if "weather" in tool_data:
        w = tool_data["weather"]
        ui_tool_map["weather"] = {"forecast": {
          "forecast": w.get("forecasts", []),
          "query": w.get("query", {}),
        }}

      for agent_name, mapped_data in ui_tool_map.items():
        wrapped = {"tool_data": mapped_data}
        for ui_event in extract_ui_components(agent_name, wrapped):
          yield ui_event

    # Build the mega prompt
    conversation_summary = await session_memory.get_summary(session_id)
    mega_prompt = build_mega_prompt(message, state_ctx, history, tool_data, personalization_ctx, conversation_summary=conversation_summary)

    # Start two-stage pipeline streaming into a buffer
    stream_buffer = StreamBuffer()
    llm_task = asyncio.create_task(
      _stream_llm_to_buffer(mega_prompt, stream_buffer, use_thinking=use_thinking, user_message=message)
    )

    # Run theater steps + stream text simultaneously
    # Pass early_started so theater_with_sections skips duplicate AGENT_START
    async for event in theater_with_sections(llm_task, stream_buffer, early_started):
      yield event

    # -- Observe: quality gate --
    logger.info("THEATER entering quality_gate")
    full_text = stream_buffer.full_text
    logger.info("THEATER full_text length=%d", len(full_text))
    issues = quality_gate(full_text, state)
    logger.info("THEATER quality_gate issues=%s", issues)

    # -- Reflect: fix only on failure (1 retry) --
    if issues:
      logger.info("Quality gate found issues: %s", issues)
      yield _thinking("发现内容问题，正在修正...")
      fix_text = ""
      try:
        async for chunk in _stream_fix(full_text, issues):
          fix_text += chunk
          yield _text(chunk)
      except Exception as fix_exc:
        logger.warning("Fix stream failed: %s", fix_exc)
      if fix_text:
        full_text = fix_text

    # Guard: if full_text is still empty after all stages, use smart fallback
    if not full_text.strip():
      logger.warning("THEATER full_text empty after all stages, using _smart_fallback")
      full_text = _smart_fallback(message)
      yield _text(full_text)

    # Cache output for potential incremental follow-ups
    _mega_cache_set(session_id, full_text)

    # Save assistant response
    await session_memory.add_message(session_id, "assistant", full_text)

    yield _done(session_id)

  except Exception as exc:
    logger.exception("Theater handle error")
    yield _error(str(exc))
    yield _done(session_id)


# ------------------------------------------------------------------ #
# Clarify handler
# ------------------------------------------------------------------ #

async def handle_clarify(
  session_id: str,
  message: str,
  history: list[dict[str, Any]],
  state_ctx: str = "",
) -> AsyncGenerator[dict, None]:
  """Handle clarify intent – one streaming LLM call with CLARIFY_SYSTEM_PROMPT."""
  try:
    yield _thinking("正在理解你的需求...")

    # Build clarify messages with context
    messages: list[dict[str, str]] = []
    # Include recent history for context
    for msg in history[-6:]:
      role = msg.get("role", "user")
      content = msg.get("content", "")
      if role in ("user", "assistant"):
        messages.append({"role": role, "content": content[:500]})

    context_prefix = ""
    if state_ctx:
      context_prefix = f"[当前已知信息]\n{state_ctx}\n\n"

    messages.append({
      "role": "user",
      "content": f"{context_prefix}{message}",
    })

    full_response = ""
    # Try fallback model first (fast), then primary if empty
    for model_choice in ("fallback", "primary"):
      try:
        async for chunk in llm_chat_stream(
          system=CLARIFY_SYSTEM_PROMPT,
          messages=messages,
          max_tokens=1024,
          model=model_choice,
        ):
          if chunk:
            full_response += chunk
            yield _text(chunk)
        if full_response.strip():
          break
        logger.warning("handle_clarify: model=%s returned empty, trying next", model_choice)
      except Exception as llm_exc:
        logger.warning("handle_clarify: model=%s failed: %s", model_choice, llm_exc)
        continue

    if not full_response.strip():
      # All models failed -- empathetic fallback
      logger.warning("handle_clarify: all models failed, using fallback")
      fallback = "我理解你想出去走走的心情。能告诉我大概什么时候出发、几个人一起吗？这样我能给你更好的推荐 😊"
      full_response = fallback
      yield _text(fallback)

    if full_response:
      await session_memory.add_message(session_id, "assistant", full_response)

    yield _done(session_id)

  except Exception as exc:
    logger.exception("Clarify handler error")
    yield _error(str(exc))
    yield _done(session_id)


# ------------------------------------------------------------------ #
# Theater performance + section routing
# ------------------------------------------------------------------ #

async def theater_with_sections(
  llm_task: asyncio.Task,
  stream_buffer: StreamBuffer,
  pre_started: set[str] | None = None,
) -> AsyncGenerator[dict, None]:
  """Perform theater agent steps while streaming LLM output.

  Yields AGENT_START events as "theater" steps, then streams TEXT events
  from the LLM buffer. Detects section markers to emit AGENT_RESULT events.

  Args:
    pre_started: Steps already emitted as AGENT_START by caller (skip duplicates).
  """
  detector = SectionDetector()
  current_section: Optional[str] = None
  section_content: str = ""
  started_steps: set[str] = set(pre_started) if pre_started else set()

  # Start all theater steps with staggered timing
  step_task = asyncio.create_task(
    _emit_theater_steps(started_steps)
  )

  # Stream LLM output, detecting sections
  try:
    async for chunk in stream_buffer.stream():
      # Detect section boundaries
      detected = detector.detect(chunk)
      if detected:
        # Emit result for previous section if any
        if current_section and section_content.strip():
          yield _agent_result(
            current_section,
            section_content.strip()[:120],
            {"content": section_content.strip(), "section": current_section},
          )

        current_section = detected
        section_content = ""

        # If this section wasn't started in theater, start it now
        if detected not in started_steps:
          yield _agent_start(detected, f"正在处理 {detected}...")
          started_steps.add(detected)
      else:
        section_content += chunk

      # Always forward text to frontend
      yield _text(chunk)
  except Exception as stream_exc:
    logger.warning("Stream reading error: %s", stream_exc)

  logger.info("THEATER stream loop exited")

  # Emit final section result
  if current_section and section_content.strip():
    yield _agent_result(
      current_section,
      section_content.strip()[:120],
      {"content": section_content.strip(), "section": current_section},
    )

  # Wait for theater steps and LLM task to finish
  logger.info("THEATER cancelling step_task")
  step_task.cancel()
  try:
    await step_task
  except asyncio.CancelledError:
    pass

  logger.info("THEATER checking llm_task.done()=%s", llm_task.done())
  if not llm_task.done():
    try:
      await asyncio.wait_for(llm_task, timeout=5.0)
    except asyncio.TimeoutError:
      logger.warning("THEATER llm_task did not finish in 5s, cancelling")
      llm_task.cancel()
    except Exception as exc:
      logger.warning("LLM task error: %s", exc)

  logger.info("THEATER theater_with_sections done")


async def _emit_theater_steps(started_steps: set[str]) -> None:
  """Emit theater AGENT_START events with staggered delays.

  This runs as a background task. Steps are emitted at predefined
  intervals to give the user visual feedback while LLM is streaming.
  """
  try:
    for name, display, delay in THEATER_STEPS:
      await asyncio.sleep(delay if not started_steps else max(0.3, delay - 0.2))
      started_steps.add(name)
  except asyncio.CancelledError:
    pass
