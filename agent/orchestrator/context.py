# Context builder – compresses conversation history for LLM consumption
# v0.9.0: Fast local summarization (no LLM call), running summary support
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Key travel entities to preserve in summaries
_TRAVEL_ENTITY_RE = re.compile(
  r"(\d+[天日万元块人个月]+|"
  r"[一二三四五六七八九十]+[天日个人]+|"
  r"[\u4e00-\u9fff]{2,4}(?:机场|车站|景区|酒店|民宿)|"
  r"预算[\d.]+|"
  r"\d{1,2}月\d{1,2}日)"
)


def fast_summarize(messages: list[dict[str, Any]], max_chars: int = 300) -> str:
  """Fast local summarization – extract key info without LLM call (~0ms).

  Extracts: destinations, dates, budget, traveler count, preferences
  from older conversation turns. No API call needed.
  """
  if not messages:
    return ""

  key_points: list[str] = []
  seen: set[str] = set()

  for msg in messages:
    content = msg.get("content", "")[:300]
    role = msg.get("role", "user")

    # Extract travel entities
    entities = _TRAVEL_ENTITY_RE.findall(content)
    for e in entities:
      if e not in seen:
        seen.add(e)
        key_points.append(e)

    # For user messages, keep a compact version of intent
    if role == "user" and len(content) > 10:
      # Take first meaningful sentence (up to 60 chars)
      first_line = content.split("。")[0].split("，")[0][:60]
      if first_line not in seen:
        seen.add(first_line)
        key_points.append(f"用户: {first_line}")

  result = "; ".join(key_points)
  return result[:max_chars] if result else ""


def update_running_summary(
  existing_summary: str,
  new_user_msg: str,
  new_assistant_msg: str,
  max_chars: int = 400,
) -> str:
  """Update a running conversation summary with the latest turn.

  Keeps the summary compact by preserving only key travel decisions
  and dropping redundant context. No LLM call.
  """
  parts: list[str] = []

  # Keep existing summary (compressed)
  if existing_summary:
    # If summary is getting long, trim the oldest half
    if len(existing_summary) > max_chars * 0.7:
      # Keep the more recent portion
      sentences = existing_summary.split("; ")
      half = len(sentences) // 2
      parts.append("; ".join(sentences[half:]))
    else:
      parts.append(existing_summary)

  # Extract key info from new user message
  user_key = new_user_msg[:80].split("。")[0]
  if user_key:
    parts.append(f"用户: {user_key}")

  # Extract key info from assistant response (first line / decision)
  if new_assistant_msg:
    # Get first substantive line from response
    for line in new_assistant_msg.split("\n"):
      clean = line.strip().lstrip("#- *>")
      if len(clean) > 15:
        parts.append(f"AI推荐: {clean[:80]}")
        break

  result = "; ".join(parts)
  return result[:max_chars]


async def build_context_with_summary(
  history: list[dict[str, Any]],
) -> str:
  """Build context: recent turns verbatim + older turns as fast summary.

  No LLM call — uses fast_summarize for older history.
  """
  if not history:
    return ""
  if len(history) <= 4:
    # 2 turns or fewer – keep everything
    return "\n".join(f'{m["role"]}: {m["content"][:400]}' for m in history)

  # Split: compress older, keep recent
  older = history[:-4]
  recent = history[-4:]

  summary = fast_summarize(older)
  recent_text = "\n".join(
    f'{m["role"]}: {m["content"][:400]}' for m in recent
  )
  if summary:
    return f"[前序对话要点]: {summary}\n\n[近期对话]:\n{recent_text}"
  return f"[近期对话]:\n{recent_text}"


def build_messages(
  history: list[dict[str, Any]],
) -> list[dict[str, str]]:
  """Convert session history to LLM message format."""
  messages: list[dict[str, str]] = []
  for msg in history[-20:]:  # last 10 turns
    role = msg["role"]
    if role in ("user", "assistant"):
      messages.append({"role": role, "content": msg["content"]})
  # Ensure messages start with user
  if messages and messages[0]["role"] != "user":
    messages = messages[1:]
  return messages if messages else [{"role": "user", "content": "hello"}]
