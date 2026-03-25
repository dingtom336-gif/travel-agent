# Theater Orchestrator – compressed ReAct: Think → Act → Observe → Reflect
# Single mega-LLM call replaces N agent calls. "Theater" steps give UX feedback
# while the LLM streams section-by-section output.
from __future__ import annotations

import asyncio
import json
import logging
import time
import httpx
from collections import OrderedDict
from collections.abc import AsyncGenerator
from typing import Any, Optional

from agent.config.mega_prompt import (
  CLARIFY_SYSTEM_PROMPT,
  FIX_PROMPT,
  INCREMENTAL_PROMPT_TEMPLATE,
  MEGA_SYSTEM_PROMPT,
)
from agent.config.settings import get_settings
from agent.llm import llm_chat, llm_chat_stream
from agent.memory.session import session_memory
from agent.memory.state_pool import state_pool
from agent.models import SSEEventType, SSEMessage
from agent.orchestrator.section_parser import (
  SectionDetector,
  StreamBuffer,
  parse_section_names,
)
from agent.orchestrator.state_extractor import heuristic_extract
from agent.orchestrator.synthesis import _smart_fallback
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


# Module-level httpx client singleton for connection reuse
_reasoning_client: httpx.AsyncClient | None = None


def _get_reasoning_client() -> httpx.AsyncClient:
  """Return a persistent httpx client, creating one if needed."""
  global _reasoning_client
  if _reasoning_client is None or _reasoning_client.is_closed:
    _reasoning_client = httpx.AsyncClient(
      timeout=httpx.Timeout(60.0, connect=10.0),
    )
  return _reasoning_client

# Fields that count toward incremental state-change detection
_INCREMENTAL_FIELDS = (
  "destination", "origin", "start_date", "end_date",
  "duration_days", "travelers", "budget", "preferences", "constraints",
)


def _detect_state_changes(
  old_state: Optional[Any],
  new_state: Optional[Any],
) -> dict[str, tuple[Any, Any]]:
  """Compare two SessionState objects, return changed fields as {field: (old, new)}."""
  if old_state is None or new_state is None:
    return {}
  changes: dict[str, tuple[Any, Any]] = {}
  for field in _INCREMENTAL_FIELDS:
    old_val = getattr(old_state, field, None)
    new_val = getattr(new_state, field, None)
    if old_val != new_val and new_val is not None:
      changes[field] = (old_val, new_val)
  return changes


def _format_state_changes(changes: dict[str, tuple[Any, Any]]) -> str:
  """Format state changes into readable text for the incremental prompt."""
  lines: list[str] = []
  for field, (old_val, new_val) in changes.items():
    if old_val is not None:
      lines.append(f"- {field}: {old_val} → {new_val}")
    else:
      lines.append(f"- {field}: (新增) {new_val}")
  return "\n".join(lines) if lines else "无明显参数变化"


def _snapshot_state(state: Optional[Any]) -> Optional[Any]:
  """Create a shallow copy of state fields for later comparison."""
  if state is None:
    return None
  from agent.models import SessionState
  snap = SessionState()
  for field in _INCREMENTAL_FIELDS:
    val = getattr(state, field, None)
    if val is not None:
      setattr(snap, field, val)
  return snap


def _guess_affected_sections(changes: dict[str, tuple[Any, Any]]) -> list[str]:
  """Map state field changes to likely affected SECTION names."""
  affected: set[str] = set()
  field_to_sections: dict[str, list[str]] = {
    "budget": ["hotel", "transport", "poi"],
    "duration_days": ["itinerary", "hotel"],
    "start_date": ["weather", "transport", "itinerary"],
    "end_date": ["weather", "itinerary"],
    "travelers": ["hotel", "transport"],
    "origin": ["transport"],
    "preferences": ["poi", "itinerary"],
    "constraints": ["poi", "itinerary"],
  }
  for field in changes:
    for section in field_to_sections.get(field, ["itinerary"]):
      affected.add(section)
  # Always include itinerary as it's the most commonly affected
  affected.add("itinerary")
  return list(affected)[:3]


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
    # ── Think: immediate feedback + state extraction ──
    yield _thinking("正在分析你的需求...")

    # Snapshot old state before extraction for incremental diff
    existing_state = await state_pool.get(session_id)
    old_state_snapshot = _snapshot_state(existing_state)
    await heuristic_extract(session_id, message, existing_state)
    state = await state_pool.get(session_id)
    state_ctx = await state_pool.to_prompt_context(session_id)

    # ── Incremental mode: if cached output exists and changes are small ──
    previous_output = _mega_cache.get(session_id)
    state_changes = _detect_state_changes(old_state_snapshot, state)
    is_incremental = (
      previous_output
      and len(state_changes) <= 3  # relaxed from 2 to allow more follow-ups
      and "destination" not in state_changes  # destination change → full replan
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

    # ── Full mode: Act → parallel LLM + theater performance ──
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
    # extract_ui_components expects result_data = {"tool_data": {key: {results:[...]}}}
    # where key names must match ui_mapper expectations
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

    # ── Observe: quality gate ──
    logger.info("THEATER entering quality_gate")
    full_text = stream_buffer.full_text
    logger.info("THEATER full_text length=%d", len(full_text))
    issues = quality_gate(full_text, state)
    logger.info("THEATER quality_gate issues=%s", issues)

    # ── Reflect: fix only on failure (1 retry) ──
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
      # All models failed — empathetic fallback
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


# ------------------------------------------------------------------ #
# Tool data gathering
# ------------------------------------------------------------------ #

async def gather_tool_data(state: Optional[Any]) -> dict[str, Any]:
  """Call mock tools in parallel to collect supplementary data.

  This pre-gathers data that enriches the mega prompt. Since tools are
  mock-based, they're fast. Real API integration would add timeouts here.
  """
  if state is None:
    return {}

  tool_data: dict[str, Any] = {}
  tasks: list[tuple[str, Any]] = []

  dest = getattr(state, "destination", None)
  origin = getattr(state, "origin", None)
  start_date = getattr(state, "start_date", None)
  duration = getattr(state, "duration_days", None)
  travelers = getattr(state, "travelers", None) or 1
  budget = getattr(state, "budget", None)

  if dest:
    # Weather data
    try:
      from agent.tools.mcp.weather_api import get_weather_forecast
      tasks.append(("weather", get_weather_forecast(
        city=dest,
        start_date=start_date or "2026-04-01",
        days=duration or 5,
      )))
    except Exception:
      pass

    # POI data
    try:
      from agent.tools.mcp.poi_search import search_pois
      tasks.append(("pois", search_pois(
        city=dest,
        category=None,
        limit=10,
      )))
    except Exception:
      pass

    # Hotel data – needs checkin/checkout dates
    try:
      from agent.tools.mcp.hotel_search import search_hotels
      checkin = start_date or "2026-04-01"
      # Calculate checkout from duration
      try:
        from datetime import datetime, timedelta
        ci = datetime.strptime(checkin, "%Y-%m-%d")
        checkout = (ci + timedelta(days=duration or 3)).strftime("%Y-%m-%d")
      except Exception:
        checkout = "2026-04-04"
      tasks.append(("hotels", search_hotels(
        city=dest,
        checkin=checkin,
        checkout=checkout,
        guests=travelers,
      )))
    except Exception:
      pass

    # Transport data
    if origin:
      try:
        from agent.tools.mcp.flight_search import search_flights
        tasks.append(("flights", search_flights(
          departure=origin,
          arrival=dest,
          date=start_date or "",
          passengers=travelers,
        )))
      except Exception:
        pass

  # Run all tool calls in parallel
  if tasks:
    names = [t[0] for t in tasks]
    coros = [t[1] for t in tasks]
    try:
      results = await asyncio.gather(*coros, return_exceptions=True)
      for name, result in zip(names, results):
        if isinstance(result, Exception):
          logger.warning("Tool %s failed: %s", name, result)
        else:
          tool_data[name] = result
    except Exception as exc:
      logger.warning("gather_tool_data error: %s", exc)

  return tool_data


# ------------------------------------------------------------------ #
# Mega prompt builder
# ------------------------------------------------------------------ #

def build_mega_prompt(
  message: str,
  state_ctx: str,
  history: list[dict[str, Any]],
  tool_data: dict[str, Any],
  personalization_ctx: str = "",
  conversation_summary: str = "",
) -> str:
  """Assemble the final mega prompt for the single LLM call.

  Combines: user message + state context + conversation history +
  tool data + personalization into one structured prompt.
  """
  parts: list[str] = []

  # Conversation context: running summary + recent turns (fuller content)
  if history and len(history) > 2:
    history_parts = []
    if conversation_summary:
      history_parts.append(f"[前序对话要点] {conversation_summary}")

    # Recent turns: last 4 messages (2 turns) with 500 char limit
    recent = history[-4:]
    for msg in recent:
      role = "用户" if msg.get("role") == "user" else "AI"
      content = msg.get("content", "")[:500]
      history_parts.append(f"{role}: {content}")
    parts.append("[对话历史]\n" + "\n".join(history_parts))

  # Current travel state
  if state_ctx:
    parts.append(f"[旅行参数]\n{state_ctx}")

  # Tool data (real-time info)
  if tool_data:
    parts.append("[实时数据]")
    for tool_name, data in tool_data.items():
      try:
        data_str = json.dumps(data, ensure_ascii=False, default=str)[:2000]
        parts.append(f"--- {tool_name} ---\n{data_str}")
      except Exception:
        pass

  # Personalization
  if personalization_ctx:
    parts.append(f"[用户画像]\n{personalization_ctx}")

  # User message (always last)
  parts.append(f"[用户需求]\n{message}")

  return "\n\n".join(parts)


# ------------------------------------------------------------------ #
# Quality gate
# ------------------------------------------------------------------ #

def quality_gate(
  mega_result: str,
  state: Optional[Any],
) -> list[str]:
  """Rule-based quality check on mega LLM output.

  Returns list of issue descriptions. Empty list = pass.
  Checks: destination consistency, duration match, section completeness.
  """
  issues: list[str] = []

  if not mega_result or len(mega_result) < 100:
    issues.append("输出内容过短，可能不完整")
    return issues

  # Section completeness: skip check under dynamic budget mode.
  # The LLM adaptively skips irrelevant sections, which is correct behavior.
  # Only flag if zero sections found (likely a generation failure).
  found_sections = set(parse_section_names(mega_result))
  if not found_sections and len(mega_result) > 200:
    issues.append("未检测到任何 SECTION 标记，可能格式异常")

  # Destination consistency check
  if state:
    dest = getattr(state, "destination", None)
    if dest and dest not in mega_result:
      issues.append(f"目的地 '{dest}' 未在输出中出现")

    # Duration consistency check
    duration = getattr(state, "duration_days", None)
    if duration and f"{duration}天" not in mega_result and f"{duration}日" not in mega_result:
      # Also check for day-by-day mentions (Day 1, Day 2, etc.)
      day_count = mega_result.count("Day ") + mega_result.count("第")
      if day_count < duration:
        issues.append(f"天数 {duration}天 可能与行程不一致")

  return issues


# ------------------------------------------------------------------ #
# LLM streaming helpers
# ------------------------------------------------------------------ #

# Skeleton prompt for Stage 1 reasoning
_SKELETON_SYSTEM = """\
你是旅行决策引擎。根据用户需求，输出一个JSON格式的规划骨架。只输出JSON，不要任何解释。

JSON结构：
{"destination":"推荐目的地","why":"一句话为什么选这里而不是热门地",\
"budget_split":{"交通":"xx元","住宿":"xx元","餐饮":"xx元","活动":"xx元"},\
"hotel":{"name":"推荐酒店/民宿","price":"xx元/晚","why":"一句话亮点"},\
"highlights":["小众亮点1","小众亮点2","省钱技巧"],\
"daily_skeleton":[{"day":1,"theme":"主题","morning":"上午活动","afternoon":"下午活动","evening":"晚上活动"}],\
"tips_for_elderly":"老人注意事项","tips_for_kids":"小孩注意事项"}"""

_EXPAND_SYSTEM = """\
你是旅行规划写手。根据以下规划骨架，写出温暖、实用、有细节的旅行方案。

要求：
- 用列表/表格形式，不写废话
- 保持骨架中的所有具体信息（地名、价格、tips），用自然流畅的中文展开
- 用 <!-- SECTION:xxx --> 标记分隔每个维度（knowledge/weather/transport/hotel/poi/itinerary）
- 根据骨架内容自适应跳过不相关的SECTION
- 禁止抒情散文、废话、总结段

篇幅控制（根据骨架复杂度自适应）：
- 骨架中有N天行程 → 每天的详细行程不超过4行
- 每个SECTION用列表/表格，不写段落
- 总输出控制在骨架字数的1.5-2倍
- 禁止重复骨架中已有的信息，只做"展开"不做"复制"
- 每条信息精炼到一行，用数据说话（价格、时间、距离），不堆砌形容词"""


def _needs_deep_thinking(message: str, state: Any) -> bool:
  """Decide if Stage 1 should use thinking mode (slower but higher quality).

  Deep thinking for: no destination, emotional queries, vague constraints.
  No thinking for: explicit destination, follow-up modifications.
  """
  dest = getattr(state, "destination", None) if state else None
  if dest:
    return False  # Has destination → standard reasoning is enough

  # Vague/emotional patterns that benefit from deep thinking
  deep_patterns = [
    "找个地方", "去哪", "推荐", "哪里好", "不知道去哪",
    "散心", "疗伤", "分手", "压力", "放松", "逃离",
    "带爸妈", "带老人", "全家", "亲子",
  ]
  msg_lower = message.lower()
  return any(p in msg_lower for p in deep_patterns)


async def _stream_llm_to_buffer(
  mega_prompt: str,
  buffer: StreamBuffer,
  use_thinking: bool = False,
  user_message: str = "",
) -> None:
  """Two-stage pipeline: GLM-5 reasoning → GLM-4-32B writing.

  Stage 1: GLM-5 generates a JSON skeleton (with/without thinking).
  Stage 2: GLM-4-32B expands skeleton into full sectioned response (streamed).
  Falls back to _smart_fallback if all LLM calls fail (prevents 0-char responses).
  """
  try:
    settings = get_settings()
    logger.info(
      "THEATER Stage1 start: thinking=%s model=%s",
      use_thinking, settings.REASONING_MODEL,
    )

    # ── Stage 1: Reasoning → JSON skeleton ──
    t1 = time.time()
    skeleton = await _call_reasoning(
      mega_prompt, settings.REASONING_MODEL, use_thinking,
    )
    s1_ms = int((time.time() - t1) * 1000)
    logger.info("THEATER Stage1 done: %dms skeleton=%d chars thinking=%s", s1_ms, len(skeleton or ""), use_thinking)

    min_skeleton = getattr(settings, "STAGE1_MIN_SKELETON_LEN", 50)
    if not skeleton or len(skeleton.strip()) < min_skeleton:
      # Skeleton empty or too short — skip Stage2, go direct to single-call fallback
      logger.warning(
        "THEATER Stage1 skeleton too short (%d chars < %d), falling back to single-call",
        len(skeleton or ""), min_skeleton,
      )
      try:
        async for chunk in llm_chat_stream(
          system=MEGA_SYSTEM_PROMPT,
          messages=[{"role": "user", "content": mega_prompt}],
          max_tokens=settings.LLM_MAX_TOKENS,
          model=settings.WRITING_MODEL,
        ):
          if chunk:
            await buffer.write(chunk)
      except Exception as fb_exc:
        logger.warning("THEATER writing model fallback also failed: %s", fb_exc)
      # If buffer still empty after writing model fallback, use smart fallback
      if not buffer.full_text.strip():
        logger.warning("THEATER all LLM fallbacks failed, using _smart_fallback")
        fallback_text = _smart_fallback(user_message)
        await buffer.write(fallback_text)
      return

    # ── Stage 2: Writing → streamed sectioned text ──
    t2 = time.time()
    logger.info("THEATER Stage2 start: model=%s skeleton=%d chars", settings.WRITING_MODEL, len(skeleton))
    async for chunk in llm_chat_stream(
      system=_EXPAND_SYSTEM,
      messages=[{"role": "user", "content": f"请基于以下骨架写出完整旅行方案：\n\n{skeleton}"}],
      max_tokens=settings.LLM_MAX_TOKENS,
      model=settings.WRITING_MODEL,
    ):
      if chunk:
        await buffer.write(chunk)
    s2_ms = int((time.time() - t2) * 1000)
    logger.info("THEATER Stage2 done: %dms output=%d chars", s2_ms, len(buffer.full_text))

    # Stage2 output guard — if still too short, fallback
    if len(buffer.full_text.strip()) < 20:
      logger.warning("THEATER Stage2 output too short (%d chars), using _smart_fallback", len(buffer.full_text))
      fallback_text = _smart_fallback(user_message)
      await buffer.write("\n\n" + fallback_text)

  except Exception as exc:
    logger.warning("THEATER pipeline failed: %s", exc)
    # Last resort: write smart fallback if buffer is empty
    if not buffer.full_text.strip():
      try:
        fallback_text = _smart_fallback(user_message)
        await buffer.write(fallback_text)
      except Exception:
        pass
  finally:
    logger.info("THEATER pipeline finished, calling buffer.finish()")
    buffer.finish()


async def _call_reasoning(
  user_prompt: str,
  model: str,
  use_thinking: bool,
) -> Optional[str]:
  """Call reasoning model (Stage 1). Supports thinking on/off via extra_body.

  Uses httpx directly to pass thinking parameter that OpenAI SDK may not support.
  """
  settings = get_settings()
  api_key = settings.SILICONFLOW_API_KEY or settings.DEEPSEEK_API_KEY
  base_url = settings.SILICONFLOW_BASE_URL or settings.DEEPSEEK_BASE_URL

  payload: dict[str, Any] = {
    "model": model,
    "messages": [
      {"role": "system", "content": _SKELETON_SYSTEM},
      {"role": "user", "content": user_prompt},
    ],
    "max_tokens": 800,
    "temperature": 0.3,
  }
  if not use_thinking:
    payload["thinking"] = {"type": "disabled"}

  stage1_timeout = settings.STAGE1_THINKING_TIMEOUT if use_thinking else settings.STAGE1_NO_THINKING_TIMEOUT
  client = _get_reasoning_client()
  headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
  try:
    resp = await client.post(
      f"{base_url}/chat/completions",
      json=payload,
      headers=headers,
      timeout=httpx.Timeout(stage1_timeout, connect=10.0),
    )
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"].get("content", "")
    return content if content else None
  except httpx.ReadTimeout:
    logger.warning("Stage1 reasoning timeout (%ss), will retry without thinking", stage1_timeout)
    if use_thinking:
      retry_payload = {**payload, "thinking": {"type": "disabled"}}
      try:
        resp = await client.post(
          f"{base_url}/chat/completions",
          json=retry_payload,
          headers=headers,
          timeout=httpx.Timeout(15.0, connect=10.0),
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"].get("content", "")
        logger.info("Stage1 retry without thinking succeeded: %d chars", len(content or ""))
        return content if content else None
      except Exception as retry_exc:
        logger.warning("Stage1 retry also failed: %s", retry_exc)
    return None
  except Exception as exc:
    logger.warning("Stage1 reasoning call failed: %s", exc)
    return None


async def _stream_fix(
  original_output: str,
  issues: list[str],
) -> AsyncGenerator[str, None]:
  """Stream a fix attempt using FIX_PROMPT."""
  fix_prompt = FIX_PROMPT.format(
    issues="\n".join(f"- {i}" for i in issues),
    original_output=original_output[:3000],
  )
  settings = get_settings()
  async for chunk in llm_chat_stream(
    system=MEGA_SYSTEM_PROMPT,
    messages=[{"role": "user", "content": fix_prompt}],
    max_tokens=settings.LLM_MAX_TOKENS,
    model="primary",
  ):
    if chunk:
      yield chunk
