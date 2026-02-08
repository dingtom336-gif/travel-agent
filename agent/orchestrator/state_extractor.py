# State extractor – pulls travel parameters from user messages
from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from agent.llm import llm_chat
from agent.memory.state_pool import state_pool
from agent.models import SessionState

logger = logging.getLogger(__name__)

STATE_EXTRACTION_PROMPT = """Extract travel parameters from the user's LATEST message into a JSON object.

**Critical rules for multi-turn conversations:**
1. You will receive conversation history and current extracted state. Use them to understand context.
2. If the AI just asked "出发城市/从哪出发" and the user answers with a city name, that city is the ORIGIN, not the destination.
3. If the AI just asked about budget/dates/preferences and the user answers, map the answer to the correct field.
4. NEVER overwrite a previously established field unless the user EXPLICITLY wants to change it (e.g., "改成去泰国", "目的地换成...", "不去日本了").
5. A city mentioned as "从X出发/X出发/从X去" is ORIGIN, not destination.
6. Preference words (古迹/都市/海滩/美食/购物/温泉/自然 etc.) go into the preferences object, not destination.

**Typo correction**: Fix obvious misspellings (e.g., "塞尔维他" → "塞尔维亚", "东经" → "东京").
Only include fields that are NEWLY mentioned or EXPLICITLY changed in the latest message.
Use null for fields not mentioned in the latest message.
Fields: destination, origin, start_date, end_date, duration_days, travelers, budget, preferences (object), constraints (array of strings).
Return ONLY valid JSON, no other text."""


async def extract_state(
  session_id: str,
  message: str,
  history: Optional[list[dict[str, Any]]] = None,
  existing_state: Optional[SessionState] = None,
) -> None:
  """Try to extract travel parameters from the user message with conversation context."""
  try:
    # Build context-aware prompt
    prompt_parts = []

    # Include existing state so LLM knows what's already extracted
    if existing_state:
      state_fields = []
      if existing_state.destination:
        state_fields.append(f"destination: {existing_state.destination}")
      if existing_state.origin:
        state_fields.append(f"origin: {existing_state.origin}")
      if existing_state.duration_days:
        state_fields.append(f"duration_days: {existing_state.duration_days}")
      if existing_state.budget:
        state_fields.append(f"budget: {existing_state.budget}")
      if existing_state.travelers:
        state_fields.append(f"travelers: {existing_state.travelers}")
      if existing_state.preferences:
        state_fields.append(f"preferences: {existing_state.preferences}")
      if state_fields:
        prompt_parts.append(
          "Current extracted state:\n" + "\n".join(state_fields)
        )

    # Include recent conversation history (last 3 turns = 6 messages)
    if history:
      recent = history[-6:]
      history_text = "\n".join(
        f'{m["role"]}: {m["content"][:200]}' for m in recent
      )
      prompt_parts.append(f"Recent conversation:\n{history_text}")

    prompt_parts.append(f"Latest user message: {message}")
    full_prompt = "\n\n".join(prompt_parts)

    text = await llm_chat(
      system=STATE_EXTRACTION_PROMPT,
      messages=[{"role": "user", "content": full_prompt}],
      max_tokens=256,
      temperature=0.1,
    )
    if text is None:
      heuristic_extract(session_id, message, existing_state)
      return
    text = text.strip()
    if text.startswith("```"):
      text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    data = json.loads(text)
    # Remove null values
    clean = {k: v for k, v in data.items() if v is not None}
    if clean:
      state_pool.update_from_dict(session_id, clean)
  except Exception as exc:
    logger.warning("State extraction failed: %s – using heuristic", exc)
    heuristic_extract(session_id, message, existing_state)


def heuristic_extract(
  session_id: str,
  message: str,
  existing_state: Optional[SessionState] = None,
) -> None:
  """Fallback keyword extraction for state slots."""
  updates: dict[str, Any] = {}

  # Origin patterns: "从X出发", "从X去", "出发城市X"
  origin_patterns = [
    r"从(.{2,6}?)出发",
    r"从(.{2,6}?)去",
    r"出发城市[是为]?(.{2,6})",
  ]
  origin_found = None
  for pat in origin_patterns:
    m = re.search(pat, message)
    if m:
      origin_found = m.group(1).strip()
      updates["origin"] = origin_found
      break

  # Destination patterns (Chinese cities / countries)
  destinations = [
    "日本", "东京", "大阪", "京都", "泰国", "曼谷", "韩国", "首尔",
    "新加坡", "马来西亚", "北京", "上海", "广州", "深圳", "成都",
    "三亚", "丽江", "西安", "杭州", "重庆", "香港", "澳门", "台北",
    "越南", "河内", "印尼", "巴厘岛", "菲律宾", "柬埔寨",
    "法国", "巴黎", "英国", "伦敦", "德国", "意大利", "罗马",
    "西班牙", "巴塞罗那", "美国", "纽约", "洛杉矶", "澳大利亚",
    "悉尼", "新西兰", "土耳其", "伊斯坦布尔", "埃及", "迪拜",
    "塞尔维亚", "贝尔格莱德", "希腊", "瑞士", "冰岛", "挪威",
  ]
  for dest in destinations:
    if dest in message:
      # Skip if this city was matched as origin
      if origin_found and dest == origin_found:
        continue
      # Don't overwrite existing destination unless user explicitly changes it
      if (existing_state and existing_state.destination
          and "改" not in message and "换" not in message
          and "不去" not in message):
        continue
      updates["destination"] = dest
      break

  # Duration
  for i in range(1, 31):
    if f"{i}天" in message or f"{i}日" in message:
      updates["duration_days"] = i
      break
  # Budget
  budget_match = re.search(r"(\d+)[万元块]", message)
  if budget_match:
    num = int(budget_match.group(1))
    if "万" in message[budget_match.start():budget_match.end() + 1]:
      num *= 10000
    updates["budget"] = f"{num}元"

  if updates:
    state_pool.update_from_dict(session_id, updates)
