# Task planner – decomposes user input into sub-tasks via Claude
from __future__ import annotations

import json
import logging
from typing import Any

from agent.config.settings import get_settings
from agent.llm import llm_chat
from agent.models import AgentName, AgentTask

logger = logging.getLogger(__name__)

PLANNER_SYSTEM_PROMPT = """You are the Task Planner of TravelMind, a travel planning AI.

Your job is to analyze the user's message and decompose it into sub-tasks
that can be dispatched to specialist agents.

Available agents:
- transport: flights, trains, buses, driving routes
- hotel: accommodation search and recommendation
- poi: attractions, restaurants, experiences
- itinerary: compile day-by-day schedule from other results
- budget: cost estimation and budget management
- knowledge: visa, cultural tips, safety info
- weather: weather forecasts
- customer_service: after-sales, complaints, emergencies

Rules:
1. Return a JSON array of task objects.
2. Each task has: agent (string), goal (string in Chinese), params (object), depends_on (array of agent names whose results this task needs), reuse_previous (boolean, default false).
3. Tasks without dependencies can run in parallel.
4. The "itinerary" agent usually depends on transport, poi, hotel results.
5. If the user's message is a simple greeting or chit-chat, return an empty array [].
6. If the user's message is a follow-up adding new info (e.g., "from Shanghai"), only plan tasks for the new/changed aspects. For agents whose results are still valid, set reuse_previous=true so they are skipped. Do NOT re-plan everything from scratch.
7. IMPORTANT: The "goal" field MUST be written in Chinese (e.g., "查询目的地签证和旅行贴士", "搜索航班和交通方案").
8. Cross-validate: if state shows origin and destination as the same city, this is likely a state extraction error. Treat the conversation history as the source of truth for the actual destination.
9. When "Previous plan" is provided, use it as context. Only create new tasks for agents affected by the user's latest change. Mark unchanged agents with reuse_previous=true — their previous results will be reused without re-executing.

Respond ONLY with the JSON array, no extra text."""

# Mock plan for when Claude is unavailable
MOCK_PLAN: list[dict[str, Any]] = [
  {
    "agent": "knowledge",
    "goal": "查询目的地签证政策和旅行贴士",
    "params": {},
    "depends_on": [],
  },
  {
    "agent": "weather",
    "goal": "查询旅行期间目的地天气预报",
    "params": {},
    "depends_on": [],
  },
  {
    "agent": "transport",
    "goal": "搜索前往目的地的交通方案",
    "params": {},
    "depends_on": [],
  },
  {
    "agent": "poi",
    "goal": "推荐目的地热门景点和体验",
    "params": {},
    "depends_on": [],
  },
  {
    "agent": "itinerary",
    "goal": "根据所有专家结果编排每日行程",
    "params": {},
    "depends_on": ["transport", "poi", "knowledge", "weather"],
  },
]


async def decompose_tasks(
  user_message: str,
  state_context: str = "",
  conversation_history: list[dict[str, Any]] | None = None,
  previous_tasks: list[AgentTask] | None = None,
) -> list[AgentTask]:
  """Decompose user message into AgentTasks.

  For follow-ups (previous_tasks exists), uses LLM for incremental planning.
  For first-time clear travel requests, uses instant heuristic plan.
  Falls back to LLM when heuristic is not confident.
  """
  # Follow-ups need LLM for incremental planning
  if previous_tasks:
    settings = get_settings()
    raw_tasks = await _call_planner(
      settings, user_message, state_context, conversation_history, previous_tasks,
    )
    return _parse_tasks(raw_tasks)

  # First-time: try heuristic plan (instant, 0 LLM cost)
  heuristic_plan = _heuristic_decompose(user_message)
  if heuristic_plan is not None:
    logger.info("Using heuristic plan (skipping LLM planner)")
    return _parse_tasks(heuristic_plan)

  # Not confident → fall back to LLM planner
  settings = get_settings()
  raw_tasks = await _call_planner(
    settings, user_message, state_context, conversation_history, previous_tasks,
  )
  return _parse_tasks(raw_tasks)


# Known destinations for heuristic detection
_HEURISTIC_DESTINATIONS = {
  "日本", "东京", "大阪", "京都", "泰国", "曼谷", "韩国", "首尔",
  "新加坡", "马来西亚", "北京", "上海", "广州", "深圳", "成都",
  "三亚", "丽江", "西安", "杭州", "重庆", "香港", "澳门", "台北",
  "越南", "河内", "印尼", "巴厘岛", "菲律宾", "柬埔寨",
  "法国", "巴黎", "英国", "伦敦", "德国", "意大利", "罗马",
  "美国", "纽约", "洛杉矶", "澳大利亚", "悉尼", "清迈", "普吉",
  "冲绳", "北海道", "奈良", "济州岛", "马尔代夫",
}

_TRAVEL_INTENT_KEYWORDS = {"旅行", "旅游", "游", "攻略", "规划", "出行", "度假", "自由行"}


def _heuristic_decompose(user_message: str) -> list[dict[str, Any]] | None:
  """Instant task decomposition for common travel patterns.

  Returns MOCK_PLAN if confident this is a first-time travel request.
  Returns None if not confident (caller should use LLM).
  """
  msg = user_message.lower()
  has_intent = any(kw in msg for kw in _TRAVEL_INTENT_KEYWORDS)
  has_location = any(loc in user_message for loc in _HEURISTIC_DESTINATIONS)

  if not (has_intent or has_location):
    return None  # Not confident → use LLM

  return MOCK_PLAN


async def _call_planner(
  settings: Any,
  user_message: str,
  state_context: str,
  conversation_history: list[dict[str, Any]] | None,
  previous_tasks: list[AgentTask] | None = None,
) -> list[dict[str, Any]]:
  """Invoke LLM or return mock plan."""
  try:
    prompt_parts = []
    if state_context:
      prompt_parts.append(f"Current travel state:\n{state_context}")
    if conversation_history:
      recent = conversation_history[-6:]  # last 3 turns
      prompt_parts.append(
        "Recent conversation:\n"
        + "\n".join(f'{m["role"]}: {m["content"][:200]}' for m in recent)
      )
    if previous_tasks:
      prev_summary = json.dumps(
        [{"agent": t.agent.value, "goal": t.goal} for t in previous_tasks],
        ensure_ascii=False,
      )
      prompt_parts.append(f"Previous plan:\n{prev_summary}")
    prompt_parts.append(f"User message: {user_message}")
    full_prompt = "\n\n".join(prompt_parts)

    text = await llm_chat(
      system=PLANNER_SYSTEM_PROMPT,
      messages=[{"role": "user", "content": full_prompt}],
      max_tokens=1024,
      temperature=0.3,
    )
    if text is None:
      logger.info("No API key – returning mock plan")
      return MOCK_PLAN
    text = text.strip()
    # Extract JSON from possible markdown fences
    if text.startswith("```"):
      text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(text)
  except Exception as exc:
    logger.warning("Planner LLM call failed: %s – using mock plan", exc)
    return MOCK_PLAN


def _parse_tasks(raw: list[dict[str, Any]]) -> list[AgentTask]:
  """Convert raw dicts into validated AgentTask models."""
  tasks: list[AgentTask] = []
  for item in raw:
    try:
      agent_name = item.get("agent", "")
      # Validate agent name
      agent_enum = AgentName(agent_name)
      tasks.append(
        AgentTask(
          agent=agent_enum,
          goal=item.get("goal", ""),
          params=item.get("params", {}),
          depends_on=item.get("depends_on", []),
          reuse_previous=bool(item.get("reuse_previous", False)),
        )
      )
    except (ValueError, KeyError) as exc:
      logger.warning("Skipping invalid task %s: %s", item, exc)
  return tasks
