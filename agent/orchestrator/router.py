# Model router – decides whether to use quick reply or full ReAct loop
from __future__ import annotations

import logging
from typing import Any

from agent.config.settings import get_settings
from agent.llm import llm_chat

logger = logging.getLogger(__name__)

ROUTER_SYSTEM_PROMPT = """You are a routing classifier for TravelMind.

Classify the LATEST message as "simple" or "complex":

- "simple": pure greetings, thanks, or factual questions unrelated to planning
  (e.g. "hi", "thanks", "what time zone is Tokyo in?")
- "complex": ANY message that should trigger travel planning or replanning:
  - New travel request ("plan a 5-day trip to Japan")
  - User providing missing info (dates, budget, preferences, ages, style)
  - User adding constraints or changing requirements
  - Follow-up that completes enough info to start/update a plan

IMPORTANT: If the conversation already has a travel topic and the user
provides additional details (even short ones like "明天" or "3岁"),
classify as "complex" — these trigger agent replanning.

Respond with ONLY "simple" or "complex"."""


async def classify_complexity(
  user_message: str,
  conversation_history: list[dict[str, Any]] | None = None,
  has_travel_context: bool = False,
) -> str:
  """Return 'simple' or 'complex' for the given message.

  Falls back to keyword heuristic when LLM is unavailable.
  """
  try:
    # Include recent history so the LLM can tell follow-ups from new requests
    if conversation_history:
      recent = conversation_history[-6:]
      context = "\n".join(
        f'{m["role"]}: {m["content"][:150]}' for m in recent
      )
      prompt = f"Context:\n{context}\n\nLatest message: {user_message}"
    else:
      prompt = user_message

    text = await llm_chat(
      system=ROUTER_SYSTEM_PROMPT,
      messages=[{"role": "user", "content": prompt}],
      max_tokens=16,
      temperature=0.1,
    )
    if text is None:
      return _heuristic_classify(user_message, has_travel_context)
    result = text.strip().lower()
    if result in ("simple", "complex"):
      return result
    return "complex"  # default to complex if unclear
  except Exception as exc:
    logger.warning("Router classification failed: %s – using heuristic", exc)
    return _heuristic_classify(user_message, has_travel_context)


def _heuristic_classify(message: str, has_travel_context: bool = False) -> str:
  """Keyword-based fallback when LLM is unavailable."""
  simple_patterns = [
    "hello", "hi", "hey", "thanks", "thank you", "bye",
    "你好", "谢谢", "再见", "嗯", "好的", "ok",
  ]
  msg_lower = message.strip().lower()

  # If we already have travel context, short messages are likely follow-ups
  if has_travel_context and msg_lower not in simple_patterns:
    return "complex"

  # Short messages matching simple patterns
  if msg_lower in simple_patterns:
    return "simple"

  # Very short messages without travel context → simple
  if len(msg_lower) < 10 and not has_travel_context:
    return "simple"

  complex_keywords = [
    "plan", "trip", "travel", "flight", "hotel", "itinerary",
    "旅行", "旅游", "规划", "攻略", "机票", "酒店", "行程",
    "景点", "推荐", "签证", "预算", "天气",
  ]
  for kw in complex_keywords:
    if kw in msg_lower:
      return "complex"

  return "complex"  # default to complex
