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
2. If the AI just asked "出发城市是哪里?" or similar, and the user answers with a city name, that city is the ORIGIN (出发地), NOT the destination.
3. If the AI just asked about budget/dates/travelers/preferences and the user answers, map the answer to the CORRECT field based on what was asked.
4. **Slot-filling from AI questions**: When "AI's previous question" is provided, and the user's latest message is a short direct answer (a city, number, date, etc.), map that answer to the field the AI was asking about. For example: AI asked "几个人去？" and user says "4个" → travelers=4; AI asked "预算多少？" and user says "一万" → budget="10000元".
5. NEVER overwrite a previously established field unless the user EXPLICITLY wants to change it (e.g., "改成去泰国", "目的地换成...", "不去日本了").
6. City names after "从" or as answer to "从哪出发/出发城市" → origin field.
7. Preference words (古迹, 都市, 海滩, 美食, 购物, 自然, 文化, 亲子) → preferences object, NOT destination.

**Important**: Correct obvious typos in city names (e.g., "塞尔维他" → "塞尔维亚").
Only include fields that are NEWLY mentioned or EXPLICITLY changed in the latest message.
Use null for fields not mentioned or not changed.
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
    prompt_parts: list[str] = []

    # Include existing state so LLM knows what's already extracted
    if existing_state:
      state_fields: list[str] = []
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
          "Currently extracted state:\n" + "\n".join(state_fields)
        )

    # Include recent conversation history (last 6 messages ≈ 3 turns)
    if history:
      recent = history[-6:]
      history_text = "\n".join(
        f'{m["role"]}: {m["content"][:200]}' for m in recent
      )
      prompt_parts.append(f"Recent conversation:\n{history_text}")

      # Extract AI's last question for slot-filling context
      last_assistant = _get_last_assistant_message(history)
      if last_assistant:
        prompt_parts.append(
          f"AI's previous question: {last_assistant[:200]}"
        )

    prompt_parts.append(f"Latest user message: {message}")
    full_prompt = "\n\n".join(prompt_parts)

    text = await llm_chat(
      system=STATE_EXTRACTION_PROMPT,
      messages=[{"role": "user", "content": full_prompt}],
      max_tokens=256,
      temperature=0.1,
    )
    if text is None:
      await heuristic_extract(session_id, message, existing_state)
      return
    text = text.strip()
    if text.startswith("```"):
      text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    data = json.loads(text)
    # Remove null values
    clean = {k: v for k, v in data.items() if v is not None}
    if clean:
      await state_pool.update_from_dict(session_id, clean)
  except Exception as exc:
    logger.warning("State extraction failed: %s – using heuristic", exc)
    await heuristic_extract(session_id, message, existing_state)


async def heuristic_extract(
  session_id: str,
  message: str,
  existing_state: Optional[SessionState] = None,
) -> None:
  """Fallback keyword extraction for state slots."""
  updates: dict[str, Any] = {}

  # Known city names for route pattern matching
  _ROUTE_CITIES = (
    "日本", "东京", "大阪", "京都", "泰国", "曼谷", "韩国", "首尔",
    "新加坡", "马来西亚", "北京", "上海", "广州", "深圳", "成都",
    "三亚", "丽江", "西安", "杭州", "重庆", "香港", "澳门", "台北",
    "越南", "河内", "印尼", "巴厘岛", "菲律宾", "柬埔寨", "昆明",
    "厦门", "青岛", "南京", "武汉", "长沙", "哈尔滨", "福州",
    "法国", "巴黎", "英国", "伦敦", "纽约", "洛杉矶", "悉尼",
    "名古屋", "釜山", "清迈", "胡志明", "吉隆坡", "马尼拉",
  )

  # "X到Y" / "X飞Y" / "X→Y" pattern: extract both origin and destination
  route_origin = None
  route_dest = None
  cities_re = "|".join(re.escape(c) for c in sorted(_ROUTE_CITIES, key=len, reverse=True))
  route_re = re.compile(f"({cities_re})(?:到|飞|→)({cities_re})")
  m = route_re.search(message)
  if m:
    route_origin = m.group(1)
    route_dest = m.group(2)
    updates["origin"] = route_origin
    updates["destination"] = route_dest

  # Origin patterns: "从X出发", "从X去", "出发城市X"
  origin_patterns = [
    r"从(.{2,6}?)出发",
    r"从(.{2,6}?)去",
    r"出发城市[是为]?(.{2,6})",
  ]
  origin_found = route_origin
  if not origin_found:
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
  has_change_intent = any(kw in message for kw in ["改成", "换成", "不去", "改为"])
  # Skip destination matching if route pattern already extracted both
  if route_dest and "destination" in updates:
    pass  # Already set by "X到Y" pattern
  else:
    for dest in destinations:
      if dest in message:
        # Skip if this city was already matched as origin
        if origin_found and dest == origin_found:
          continue
        # Don't overwrite existing destination unless user explicitly wants to change
        if (existing_state and existing_state.destination
            and not has_change_intent):
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

  # Travelers
  travelers_match = re.search(r"(\d+)\s*[个人]", message)
  if travelers_match:
    n = int(travelers_match.group(1))
    if 1 <= n <= 20:
      updates["travelers"] = n

  # Constraint patterns – extract preferences/style from vague queries
  constraint_prefs: dict[str, Any] = {}
  _CONSTRAINT_MAP = {
    # Scene preferences
    "海边": "scene_beach", "海岛": "scene_island", "沙滩": "scene_beach",
    "山": "scene_mountain", "温泉": "scene_hotspring",
    "古镇": "scene_ancient_town", "古城": "scene_ancient_town",
    "滑雪": "activity_ski", "潜水": "activity_dive",
    # Travel style
    "散心": "style_relaxing", "放松": "style_relaxing", "躺平": "style_relaxing",
    "发呆": "style_relaxing", "解压": "style_relaxing", "疗愈": "style_relaxing",
    "冒险": "style_adventure", "刺激": "style_adventure",
    "文化": "style_cultural", "历史": "style_cultural",
    "美食": "style_foodie", "吃": "style_foodie",
    "购物": "style_shopping", "买买买": "style_shopping",
    # Companion type
    "亲子": "companion_family", "带娃": "companion_family",
    "带孩子": "companion_family", "带老人": "companion_elderly",
    "带爸妈": "companion_elderly", "情侣": "companion_couple",
    "蜜月": "companion_honeymoon", "独行": "companion_solo",
    "一个人": "companion_solo",
    # Season / timing
    "周末": "timing_weekend", "五一": "timing_may_day",
    "十一": "timing_national_day", "国庆": "timing_national_day",
    "春节": "timing_spring_festival", "暑假": "timing_summer",
    "寒假": "timing_winter",
  }
  for keyword, tag in _CONSTRAINT_MAP.items():
    if keyword in message:
      constraint_prefs[tag] = True

  if constraint_prefs:
    updates["preferences"] = constraint_prefs

  # Constraints as list (emotional / motivational keywords)
  constraints: list[str] = []
  _EMOTIONAL_CONSTRAINTS = [
    ("分手", "情感疗愈旅行"), ("失恋", "情感疗愈旅行"),
    ("散心", "放松解压"), ("毕业旅行", "毕业纪念"),
    ("纪念日", "纪念日庆祝"), ("蜜月", "蜜月旅行"),
  ]
  for keyword, label in _EMOTIONAL_CONSTRAINTS:
    if keyword in message:
      constraints.append(label)
  if constraints:
    updates["constraints"] = constraints

  if updates:
    await state_pool.update_from_dict(session_id, updates)


def _get_last_assistant_message(history: list[dict[str, Any]]) -> str:
  """Return the content of the last assistant message, or empty string."""
  for msg in reversed(history):
    if msg.get("role") == "assistant":
      return msg.get("content", "")
  return ""
