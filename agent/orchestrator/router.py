# Model router – decides whether to use quick reply or full ReAct loop
from __future__ import annotations

import logging
from typing import Any

from agent.config.settings import get_settings
from agent.llm import llm_chat

logger = logging.getLogger(__name__)

ROUTER_SYSTEM_PROMPT = """You are a routing classifier for TravelMind, a travel planning AI.

Given the user's message, classify it into exactly one category:

- "simple": greetings, chit-chat, simple factual questions that can be answered directly
  (e.g. "hi", "thanks", "what time zone is Tokyo in?")
- "complex": travel planning requests that need multiple agents
  (e.g. "plan a 5-day trip to Japan", "find flights and hotels for my family vacation")

Respond with ONLY the word "simple" or "complex"."""


async def classify_complexity(
  user_message: str,
  conversation_history: list[dict[str, Any]] | None = None,
) -> str:
  """Return 'simple' or 'complex' for the given message.

  Falls back to keyword heuristic when LLM is unavailable.
  """
  try:
    # Include recent history so the LLM can tell follow-ups from new requests
    if conversation_history:
      recent = conversation_history[-4:]
      context = "\n".join(
        f'{m["role"]}: {m["content"][:150]}' for m in recent
      )
      prompt = f"Context:\n{context}\n\nLatest message: {user_message}"
    else:
      prompt = user_message

    text = await llm_chat(
      system=ROUTER_SYSTEM_PROMPT,
      messages=[{"role": "user", "content": prompt}],
      max_tokens=8,
      temperature=0.1,
    )
    if text is None:
      return _heuristic_classify(user_message)
    result = text.strip().lower()
    if result in ("simple", "complex"):
      return result
    return "complex"  # default to complex if unclear
  except Exception as exc:
    logger.warning("Router classification failed: %s – using heuristic", exc)
    return _heuristic_classify(user_message)


def _heuristic_classify(message: str) -> str:
  """Keyword-based fallback when Claude is unavailable."""
  simple_patterns = [
    "hello", "hi", "hey", "thanks", "thank you", "bye",
    "你好", "谢谢", "再见", "嗯", "好的", "ok",
  ]
  msg_lower = message.strip().lower()
  # Short messages or matching simple patterns
  if len(msg_lower) < 10 or msg_lower in simple_patterns:
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
