# Mega prompt construction, quality gate, and two-stage LLM pipeline
# Extracted from theater.py to isolate prompt/LLM logic from orchestration flow.
from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncGenerator
from typing import Any, Optional

import httpx

from agent.config.mega_prompt import FIX_PROMPT, MEGA_SYSTEM_PROMPT
from agent.config.settings import get_settings
from agent.llm import llm_chat_stream
from agent.orchestrator.section_parser import StreamBuffer, parse_section_names
from agent.orchestrator.synthesis import _smart_fallback

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Module-level httpx client singleton for connection reuse
# ------------------------------------------------------------------ #

_reasoning_client: httpx.AsyncClient | None = None


def _get_reasoning_client() -> httpx.AsyncClient:
  """Return a persistent httpx client, creating one if needed."""
  global _reasoning_client
  if _reasoning_client is None or _reasoning_client.is_closed:
    _reasoning_client = httpx.AsyncClient(
      timeout=httpx.Timeout(60.0, connect=10.0),
    )
  return _reasoning_client


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
# Skeleton prompt for Stage 1 reasoning
# ------------------------------------------------------------------ #

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
    return False  # Has destination -> standard reasoning is enough

  # Vague/emotional patterns that benefit from deep thinking
  deep_patterns = [
    "找个地方", "去哪", "推荐", "哪里好", "不知道去哪",
    "散心", "疗伤", "分手", "压力", "放松", "逃离",
    "带爸妈", "带老人", "全家", "亲子",
  ]
  msg_lower = message.lower()
  return any(p in msg_lower for p in deep_patterns)


# ------------------------------------------------------------------ #
# Two-stage LLM pipeline
# ------------------------------------------------------------------ #

async def _stream_llm_to_buffer(
  mega_prompt: str,
  buffer: StreamBuffer,
  use_thinking: bool = False,
  user_message: str = "",
) -> None:
  """Two-stage pipeline: GLM-5 reasoning -> GLM-4-32B writing.

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

    # -- Stage 1: Reasoning -> JSON skeleton --
    t1 = time.time()
    skeleton = await _call_reasoning(
      mega_prompt, settings.REASONING_MODEL, use_thinking,
    )
    s1_ms = int((time.time() - t1) * 1000)
    logger.info("THEATER Stage1 done: %dms skeleton=%d chars thinking=%s", s1_ms, len(skeleton or ""), use_thinking)

    min_skeleton = getattr(settings, "STAGE1_MIN_SKELETON_LEN", 50)
    if not skeleton or len(skeleton.strip()) < min_skeleton:
      # Skeleton empty or too short -- skip Stage2, go direct to single-call fallback
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

    # -- Stage 2: Writing -> streamed sectioned text --
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

    # Stage2 output guard -- if still too short, fallback
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
