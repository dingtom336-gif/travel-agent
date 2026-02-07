# Scoring rule functions for each evaluation dimension
from __future__ import annotations

import re
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Keyword patterns used by rule engine
# ---------------------------------------------------------------------------

DESTINATION_KEYWORDS = [
  "目的地", "去", "到", "destination", "city", "country",
  "日本", "泰国", "东京", "三亚", "北京", "上海",
]
DATE_KEYWORDS = [
  "日期", "出发", "几号", "月", "春节", "国庆", "暑假",
  "date", "when", "start_date",
]
PEOPLE_KEYWORDS = [
  "人", "位", "个人", "travelers", "people", "adults", "children",
  "家人", "朋友", "孩子", "爸妈",
]
BUDGET_KEYWORDS = [
  "预算", "花", "钱", "budget", "cost", "price",
  "万", "元", "块",
]

EXPECTED_AGENTS = [
  "transport", "hotel", "poi", "itinerary", "budget",
  "weather", "knowledge",
]


def _extract_messages(
  messages: List[Dict[str, Any]],
  role: str,
) -> List[str]:
  """Extract content strings for a given role."""
  return [
    m["content"] for m in messages if m.get("role") == role
  ]


# ---------------------------------------------------------------------------
# Rule: Intent Understanding
# ---------------------------------------------------------------------------

def score_intent_understanding(
  messages: List[Dict[str, Any]],
  traces: List[Dict[str, Any]],
) -> tuple:
  """Check if key travel info was extracted.

  Returns:
    (score, reason, details) tuple
  """
  user_msgs = _extract_messages(messages, "user")
  assistant_msgs = _extract_messages(messages, "assistant")
  combined = " ".join(user_msgs + assistant_msgs) + " " + str(traces)

  found_count = 0
  details: Dict[str, bool] = {}

  has_dest = any(kw in combined for kw in DESTINATION_KEYWORDS)
  details["destination_identified"] = has_dest
  if has_dest:
    found_count += 1

  has_date = any(kw in combined for kw in DATE_KEYWORDS)
  details["date_identified"] = has_date
  if has_date:
    found_count += 1

  has_people = any(kw in combined for kw in PEOPLE_KEYWORDS)
  details["travelers_identified"] = has_people
  if has_people:
    found_count += 1

  has_budget = any(kw in combined for kw in BUDGET_KEYWORDS)
  details["budget_identified"] = has_budget
  if has_budget:
    found_count += 1

  score = min(5, found_count + 1)
  reason = f"Identified {found_count}/4 key travel parameters"
  return score, reason, details


# ---------------------------------------------------------------------------
# Rule: Tool Usage
# ---------------------------------------------------------------------------

def score_tool_usage(
  messages: List[Dict[str, Any]],
  traces: List[Dict[str, Any]],
) -> tuple:
  """Check if correct agents/tools were dispatched and succeeded.

  Returns:
    (score, reason, details) tuple
  """
  if not traces:
    return (
      3,
      "No agent traces provided; cannot fully evaluate tool usage",
      {"traces_available": False},
    )

  total_calls = len(traces)
  successful = sum(
    1 for t in traces
    if t.get("status") in ("success", "SUCCESS")
  )
  agents_used = list(set(
    t.get("agent", "unknown") for t in traces
  ))

  success_rate = successful / total_calls if total_calls > 0 else 0
  coverage = sum(1 for a in EXPECTED_AGENTS if a in agents_used)
  coverage_ratio = coverage / len(EXPECTED_AGENTS)

  raw = (success_rate * 0.6 + coverage_ratio * 0.4) * 5
  score = max(1, min(5, round(raw)))

  reason = (
    f"{successful}/{total_calls} tool calls succeeded; "
    f"{coverage}/{len(EXPECTED_AGENTS)} expected agents used"
  )
  details = {
    "total_calls": total_calls,
    "successful_calls": successful,
    "success_rate": round(success_rate, 2),
    "agents_used": agents_used,
    "coverage": coverage,
  }
  return score, reason, details


# ---------------------------------------------------------------------------
# Rule: Response Quality
# ---------------------------------------------------------------------------

def score_response_quality(
  messages: List[Dict[str, Any]],
) -> tuple:
  """Check response length, structure, and relevance.

  Returns:
    (score, reason, details) tuple
  """
  assistant_msgs = _extract_messages(messages, "assistant")
  user_msgs = _extract_messages(messages, "user")

  if not assistant_msgs:
    return 1, "No assistant responses found", {}

  score_points = 0
  details: Dict[str, Any] = {}

  # 1. Average response length
  avg_len = sum(len(m) for m in assistant_msgs) / len(assistant_msgs)
  details["avg_response_length"] = round(avg_len)
  if avg_len >= 100:
    score_points += 1
  if avg_len >= 200:
    score_points += 1

  # 2. Contains structured info
  has_structure = any(
    re.search(r"(#{1,3}\s|\*\s|-\s|\d+\.\s)", m)
    for m in assistant_msgs
  )
  details["has_structured_content"] = has_structure
  if has_structure:
    score_points += 1

  # 3. Addresses user questions
  if user_msgs and assistant_msgs:
    last_user = user_msgs[-1]
    last_assistant = assistant_msgs[-1]
    user_words = set(
      w for w in re.findall(r"[\u4e00-\u9fff]+|\w{2,}", last_user)
      if len(w) >= 2
    )
    matched = sum(1 for w in user_words if w in last_assistant)
    relevance = matched / len(user_words) if user_words else 0
    details["keyword_relevance"] = round(relevance, 2)
    if relevance >= 0.2:
      score_points += 1

  # 4. No error messages
  has_errors = any(
    "[ERROR]" in m or "error" in m.lower()[:50]
    for m in assistant_msgs
  )
  details["has_error_messages"] = has_errors
  if not has_errors:
    score_points += 1

  score = max(1, min(5, score_points))
  reason = (
    f"Quality score {score_points}/5 based on length, "
    f"structure, relevance, and error-free checks"
  )
  return score, reason, details


# ---------------------------------------------------------------------------
# Rule: Personalization
# ---------------------------------------------------------------------------

def score_personalization(
  messages: List[Dict[str, Any]],
  traces: List[Dict[str, Any]],
) -> tuple:
  """Check if user preferences and profile info are utilized.

  Returns:
    (score, reason, details) tuple
  """
  assistant_msgs = _extract_messages(messages, "assistant")
  combined = " ".join(assistant_msgs)

  score_points = 0
  details: Dict[str, Any] = {}

  pref_keywords = [
    "偏好", "喜欢", "习惯", "preference", "您之前",
    "根据您", "为您", "推荐给您", "适合您",
  ]
  has_pref = any(kw in combined for kw in pref_keywords)
  details["references_preferences"] = has_pref
  if has_pref:
    score_points += 2

  personal_patterns = ["您", "你", "your", "you"]
  has_personal_tone = any(kw in combined for kw in personal_patterns)
  details["personal_tone"] = has_personal_tone
  if has_personal_tone:
    score_points += 1

  trace_text = str(traces)
  has_profile = any(
    kw in trace_text
    for kw in ["profile", "preference", "user_pref", "偏好"]
  )
  details["profile_data_loaded"] = has_profile
  if has_profile:
    score_points += 2

  score = max(1, min(5, score_points))
  reason = f"Personalization score {score_points}/5"
  return score, reason, details


# ---------------------------------------------------------------------------
# Rule: Completeness
# ---------------------------------------------------------------------------

def score_completeness(
  messages: List[Dict[str, Any]],
  traces: List[Dict[str, Any]],
) -> tuple:
  """Check if the plan covers transport, accommodation, attractions, budget.

  Returns:
    (score, reason, details) tuple
  """
  assistant_msgs = _extract_messages(messages, "assistant")
  full_text = " ".join(assistant_msgs) + " " + str(traces)

  covered: Dict[str, bool] = {}

  transport_kw = [
    "机票", "航班", "火车", "高铁", "交通", "flight",
    "transport", "飞机", "大巴",
  ]
  covered["transport"] = any(kw in full_text for kw in transport_kw)

  hotel_kw = [
    "酒店", "住宿", "民宿", "旅馆", "hotel", "accommodation",
    "入住", "退房",
  ]
  covered["accommodation"] = any(kw in full_text for kw in hotel_kw)

  poi_kw = [
    "景点", "游玩", "参观", "attraction", "poi", "体验",
    "游览", "打卡", "推荐",
  ]
  covered["attractions"] = any(kw in full_text for kw in poi_kw)

  budget_kw = [
    "预算", "费用", "花费", "budget", "cost", "价格",
    "总计", "合计",
  ]
  covered["budget"] = any(kw in full_text for kw in budget_kw)

  coverage_count = sum(1 for v in covered.values() if v)
  score = max(1, min(5, coverage_count + 1))
  reason = f"Covered {coverage_count}/4 plan categories"
  return score, reason, {"coverage": covered}


# ---------------------------------------------------------------------------
# Rule: Coherence
# ---------------------------------------------------------------------------

def score_coherence(
  messages: List[Dict[str, Any]],
) -> tuple:
  """Check multi-turn coherence: context consistency across turns.

  Returns:
    (score, reason, details) tuple
  """
  assistant_msgs = _extract_messages(messages, "assistant")

  if len(assistant_msgs) < 2:
    return (
      4,
      "Single-turn conversation; coherence check not fully applicable",
      {"turns": len(assistant_msgs)},
    )

  score_points = 0
  details: Dict[str, Any] = {"turns": len(assistant_msgs)}

  # 1. Destination consistency
  dest_pattern = re.compile(
    r"(日本|泰国|东京|三亚|北京|上海|大阪|首尔|"
    r"曼谷|新加坡|巴厘岛|马尔代夫)"
  )
  destinations: List[str] = []
  for msg in assistant_msgs:
    destinations.extend(dest_pattern.findall(msg))

  unique_dests = set(destinations)
  details["destinations_mentioned"] = list(unique_dests)
  if len(unique_dests) <= 2:
    score_points += 2
  elif len(unique_dests) <= 4:
    score_points += 1

  # 2. Later turns reference earlier context
  if len(assistant_msgs) >= 2:
    mid = len(assistant_msgs) // 2
    early_text = " ".join(assistant_msgs[:mid])
    late_text = " ".join(assistant_msgs[mid:])

    early_words = set(re.findall(r"[\u4e00-\u9fff]{2,}", early_text))
    if early_words:
      overlap = sum(1 for w in early_words if w in late_text)
      continuity = overlap / len(early_words)
      details["context_continuity"] = round(continuity, 2)
      if continuity >= 0.1:
        score_points += 1
      if continuity >= 0.3:
        score_points += 1

  # 3. Base point for multi-turn
  score_points += 1

  score = max(1, min(5, score_points))
  reason = (
    f"Coherence score {score_points}/5 "
    f"across {len(assistant_msgs)} turns"
  )
  return score, reason, details
