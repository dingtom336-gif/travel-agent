# Model router – LLM-based intent classification for Theater mode
# v0.9.0: Replaced regex rules with LLM classification (GLM-4-32B, ~2s)
from __future__ import annotations

import json
import logging
import re
import time
from collections import OrderedDict
from typing import Any

from agent.config.settings import get_settings
from agent.llm import llm_chat
from agent.orchestrator.intent_classifier import intent_classifier

logger = logging.getLogger(__name__)

# Module-level intent cache: message → (result_dict, timestamp)
_intent_cache: OrderedDict[str, tuple[dict, float]] = OrderedDict()
_INTENT_CACHE_SIZE = 200
_INTENT_CACHE_TTL = 300  # seconds

# System prompt for LLM intent classification
_CLASSIFY_SYSTEM = """\
你是意图分类器。根据用户消息，判断意图类型并提取关键信息。

只输出JSON，不要解释。格式：
{"intent": "simple|clarify|search|plan", "thinking": true|false, "reason": "一句话理由"}

分类规则：
- simple: 非旅行意图（问候、闲聊、写诗、讲笑话、问天气、问你是谁等日常对话）
- clarify: 有旅行意图但关键信息严重不足，需要追问才能规划（如只说"想散心"没有任何约束）
- search: 用户要查询具体旅行信息，不需要完整规划（查航班、查酒店、查景点门票、查机票价格）
- plan: 有足够信息可以开始规划（有目的地，或有2个以上可推理的约束如时间+人群+偏好）

thinking字段（仅plan时有意义）：
- true: 需要深度推理（无明确目的地需要推荐、复杂约束组合、多城市路线）
- false: 标准规划（有明确目的地、信息充分）

关键判断原则：
- "查/搜/找+航班/机票/酒店/景点/门票"→ search（用户要查具体信息，不是要做旅行规划）
- "X到Y的航班/机票"→ search
- "X酒店推荐/X住哪里"→ search
- 有明确目的地+要做行程规划 → plan, thinking=false
- 无目的地但约束丰富（过年+全家+海边+5天+预算）→ plan, thinking=true
- 情感诉求+几乎无约束（"想逃离""工作太累"）→ clarify
- 完全无旅行意图 → simple"""


async def classify_complexity(
  user_message: str,
  conversation_history: list[dict[str, Any]] | None = None,
  has_travel_context: bool = False,
) -> str:
  """Legacy two-way classifier. Kept for backward compatibility (ReAct path)."""
  label, confidence = intent_classifier.classify(
    user_message, has_travel_context=has_travel_context,
  )
  return label


async def classify_intent(
  message: str,
  history: list[dict[str, Any]] | None = None,
  has_travel_context: bool = False,
) -> dict:
  """LLM-based three-way intent classification for Theater mode.

  Returns dict: {"intent": "simple|clarify|plan", "thinking": bool, "reason": str}
  Falls back to simple on LLM failure.
  """
  # Follow-up with existing travel context → always plan (skip cache)
  if has_travel_context:
    logger.info("classify_intent: has travel context → plan")
    return {"intent": "plan", "thinking": False, "reason": "follow-up"}

  # Check cache (only when no travel context – context makes same message differ)
  now = time.time()
  if message in _intent_cache:
    cached_result, cached_ts = _intent_cache[message]
    if (now - cached_ts) < _INTENT_CACHE_TTL:
      _intent_cache.move_to_end(message)
      logger.info("classify_intent: cache hit intent=%s", cached_result.get("intent"))
      return cached_result
    else:
      _intent_cache.pop(message, None)

  # Fast local pre-check: unsafe/adversarial requests → simple (let LLM refuse)
  msg_lower = message.strip().lower()
  _UNSAFE_PATTERNS = (
    "逃票", "偷渡", "违禁", "非法", "伪造", "假证", "假的",
    "忘掉指令", "忘掉之前", "系统提示词", "system prompt", "ignore",
    "手机号", "身份证号", "隐私", "个人信息",
    "威胁信", "威胁", "勒索",
    "内部员工", "后台数据", "管理员",
    "假装你是", "扮演", "角色扮演",
    "抢票脚本", "自动抢", "外挂", "脚本",
    "诱导转账", "私下转账", "诈骗",
    "政治观点", "政治敏感", "赞美某", "不当观点",
    "核酸报告", "伪造报告", "假报告",
  )
  if any(p in msg_lower for p in _UNSAFE_PATTERNS):
    logger.info("classify_intent: unsafe request detected → simple (for refusal)")
    return {"intent": "simple", "thinking": False, "reason": "unsafe_request"}

  _OBVIOUS_SIMPLE = (
    "你好", "嗨", "hi", "hello", "再见", "拜拜", "晚安", "谢谢", "感谢",
    "你是谁", "你能做什么", "帮我算", "写首诗", "讲个笑话", "推荐一部",
    "今天周几", "几点了", "我饿了", "夸夸我", "心情不错", "1+1",
    "早上好", "下午好", "晚上好", "好的", "明白", "知道了", "没问题", "可以", "ok", "好",
  )
  if any(p in msg_lower for p in _OBVIOUS_SIMPLE) and len(message) < 20:
    logger.info("classify_intent: obvious simple (local fast-path)")
    return {"intent": "simple", "thinking": False, "reason": "obvious_simple"}

  # Fast local pre-check: fact correction/assertion → simple (not a travel request)
  # Pattern: user disagrees or states a (possibly wrong) fact about a place
  # e.g. "不对，故宫是在上海的" / "你说错了，长城在南京" / "故宫不是在北京吗"
  _CORRECTION_PREFIXES = ("不对", "不是", "错了", "你说错", "你搞错", "说错了", "纠正")
  _ASSERTION_PATTERNS = ("是在", "不是在", "在的", "属于", "不属于", "位于", "不在")
  _PLANNING_EXCLUSIONS = ("帮我", "规划", "推荐", "搜索", "预订", "安排", "查一下")
  has_correction = any(p in msg_lower for p in _CORRECTION_PREFIXES)
  has_assertion = any(p in msg_lower for p in _ASSERTION_PATTERNS)
  has_planning = any(kw in msg_lower for kw in _PLANNING_EXCLUSIONS)
  if len(message) < 40 and (has_correction or has_assertion) and not has_planning:
    logger.info("classify_intent: fact correction/assertion → simple")
    return {"intent": "simple", "thinking": False, "reason": "fact_correction"}

  # Fast local pre-check: specific search queries → search, skip LLM (~0ms)
  _SEARCH_KEYWORDS = (
    "查航班", "查机票", "查酒店", "查景点", "查门票", "查火车", "查高铁",
    "搜航班", "搜机票", "搜酒店", "搜景点",
    "找航班", "找机票", "找酒店", "找景点",
    "航班查", "机票查", "酒店查",
  )
  _SEARCH_ROUTE_PATTERN = re.compile(r".{2,6}(?:到|飞).{2,6}(?:的|最早|最晚|最便宜)?(?:航班|机票|飞机)")
  if any(k in msg_lower for k in _SEARCH_KEYWORDS) or _SEARCH_ROUTE_PATTERN.search(message):
    logger.info("classify_intent: search query detected (local fast-path)")
    return {"intent": "search", "thinking": False, "reason": "search_query"}

  # Fast local pre-check: obvious destination → plan, skip LLM (~0ms)
  _OBVIOUS_PLAN_DEST = (
    "去日本", "去泰国", "去东京", "去三亚", "去北京", "去上海", "去大阪",
    "去曼谷", "去新加坡", "去巴厘岛", "去马尔代夫", "去杭州", "去成都",
    "去西安", "去拉萨", "去云南", "去大理", "去丽江", "去厦门", "去青岛",
    "去桂林", "去张家界",
  )
  if any(d in msg_lower for d in _OBVIOUS_PLAN_DEST):
    logger.info("classify_intent: obvious destination (local fast-path)")
    return {"intent": "plan", "thinking": False, "reason": "obvious_destination"}

  settings = get_settings()
  try:
    result = await llm_chat(
      system=_CLASSIFY_SYSTEM,
      messages=[{"role": "user", "content": message}],
      max_tokens=100,
      temperature=0.1,
      model=settings.WRITING_MODEL,  # GLM-4-32B, fast (~2s)
    )

    if not result:
      logger.warning("classify_intent: LLM returned empty, fallback simple")
      return {"intent": "simple", "thinking": False, "reason": "llm_empty"}

    # Parse JSON from response (strip markdown fences if present)
    cleaned = result.strip()
    if cleaned.startswith("```"):
      cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    parsed = json.loads(cleaned)
    intent = parsed.get("intent", "simple")
    thinking = parsed.get("thinking", False)
    reason = parsed.get("reason", "")

    # Validate intent value
    if intent not in ("simple", "clarify", "search", "plan"):
      intent = "simple"

    logger.info(
      "classify_intent: intent=%s thinking=%s reason=%s",
      intent, thinking, reason,
    )
    result_dict = {"intent": intent, "thinking": thinking, "reason": reason}

    # Write to cache
    _intent_cache[message] = (result_dict, time.time())
    _intent_cache.move_to_end(message)
    while len(_intent_cache) > _INTENT_CACHE_SIZE:
      _intent_cache.popitem(last=False)

    return result_dict

  except json.JSONDecodeError as exc:
    logger.warning("classify_intent: JSON parse failed: %s, raw=%s", exc, result[:100] if result else "")
    return {"intent": "simple", "thinking": False, "reason": "json_error"}
  except Exception as exc:
    logger.warning("classify_intent: LLM call failed: %s", exc)
    return {"intent": "simple", "thinking": False, "reason": "llm_error"}
