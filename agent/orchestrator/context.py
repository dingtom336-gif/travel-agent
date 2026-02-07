# Context builder – compresses conversation history for LLM consumption
from __future__ import annotations

import logging
from typing import Any

from agent.llm import llm_chat

logger = logging.getLogger(__name__)


async def build_context_with_summary(
  history: list[dict[str, Any]],
) -> str:
  """Build context: recent turns verbatim + older turns as summary."""
  if not history:
    return ""
  if len(history) <= 4:
    # 2 turns or fewer – keep everything
    return "\n".join(f'{m["role"]}: {m["content"]}' for m in history)

  # Split: compress older, keep recent
  older = history[:-4]
  recent = history[-4:]

  summary = await summarize_history(older)
  recent_text = "\n".join(f'{m["role"]}: {m["content"]}' for m in recent)
  return f"[Earlier conversation summary]: {summary}\n\n[Recent messages]:\n{recent_text}"


async def summarize_history(messages: list[dict[str, Any]]) -> str:
  """Compress older messages into a 1-2 sentence summary."""
  try:
    text = "\n".join(
      f'{m["role"]}: {m["content"][:200]}' for m in messages
    )
    result = await llm_chat(
      system=(
        "Summarize this conversation in 1-2 sentences. "
        "Focus on: destination, dates, travelers, budget, preferences. "
        "Chinese output."
      ),
      messages=[{"role": "user", "content": text}],
      max_tokens=150,
      temperature=0.1,
    )
    return result or text[:200]  # fallback if LLM returns None
  except Exception as exc:
    logger.warning("History summarization failed: %s", exc)
    # Fallback: simple truncation
    return "; ".join(m["content"][:80] for m in messages[-3:])


def build_messages(
  history: list[dict[str, Any]],
) -> list[dict[str, str]]:
  """Convert session history to Claude message format."""
  messages: list[dict[str, str]] = []
  for msg in history[-10:]:  # last 5 turns
    role = msg["role"]
    if role in ("user", "assistant"):
      messages.append({"role": role, "content": msg["content"]})
  # Ensure messages start with user
  if messages and messages[0]["role"] != "user":
    messages = messages[1:]
  return messages if messages else [{"role": "user", "content": "hello"}]
