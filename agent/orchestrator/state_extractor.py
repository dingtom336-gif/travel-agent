# State extractor – pulls travel parameters from user messages
from __future__ import annotations

import json
import logging
import re
from typing import Any

from agent.llm import llm_chat
from agent.memory.state_pool import state_pool

logger = logging.getLogger(__name__)

STATE_EXTRACTION_PROMPT = """Extract travel parameters from the user message into a JSON object.
**Important**: If the user has obvious typos or misspellings in destination/city names,
correct them to the standard name (e.g., "塞尔维他" → "塞尔维亚", "东经" → "东京", "巴黎黎" → "巴黎").
Only include fields that are explicitly mentioned. Use null for unmentioned fields.
Fields: destination, origin, start_date, end_date, duration_days, travelers, budget, preferences (object), constraints (array of strings).
Return ONLY valid JSON, no other text."""


async def extract_state(session_id: str, message: str) -> None:
  """Try to extract travel parameters from the user message."""
  try:
    text = await llm_chat(
      system=STATE_EXTRACTION_PROMPT,
      messages=[{"role": "user", "content": message}],
      max_tokens=512,
      temperature=0.1,
    )
    if text is None:
      heuristic_extract(session_id, message)
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
    heuristic_extract(session_id, message)


def heuristic_extract(session_id: str, message: str) -> None:
  """Fallback keyword extraction for state slots."""
  updates: dict[str, Any] = {}
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
