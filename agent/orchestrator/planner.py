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
2. Each task has: agent (string), goal (string), params (object), depends_on (array of agent names whose results this task needs).
3. Tasks without dependencies can run in parallel.
4. The "itinerary" agent usually depends on transport, poi, hotel results.
5. If the user's message is a simple greeting or chit-chat, return an empty array [].

Respond ONLY with the JSON array, no extra text."""

# Mock plan for when Claude is unavailable
MOCK_PLAN: list[dict[str, Any]] = [
  {
    "agent": "knowledge",
    "goal": "Look up visa and travel tips for the destination",
    "params": {},
    "depends_on": [],
  },
  {
    "agent": "weather",
    "goal": "Check weather forecast for the destination during travel dates",
    "params": {},
    "depends_on": [],
  },
  {
    "agent": "transport",
    "goal": "Search for transport options to the destination",
    "params": {},
    "depends_on": [],
  },
  {
    "agent": "poi",
    "goal": "Recommend attractions and experiences at the destination",
    "params": {},
    "depends_on": [],
  },
  {
    "agent": "itinerary",
    "goal": "Compile a day-by-day itinerary from all agent results",
    "params": {},
    "depends_on": ["transport", "poi", "knowledge", "weather"],
  },
]


async def decompose_tasks(
  user_message: str,
  state_context: str = "",
  conversation_history: list[dict[str, Any]] | None = None,
) -> list[AgentTask]:
  """Call Claude to decompose the user message into AgentTasks.

  Falls back to a mock plan when the API key is missing or on error.
  """
  settings = get_settings()
  raw_tasks = await _call_planner(settings, user_message, state_context, conversation_history)
  return _parse_tasks(raw_tasks)


async def _call_planner(
  settings: Any,
  user_message: str,
  state_context: str,
  conversation_history: list[dict[str, Any]] | None,
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
    prompt_parts.append(f"User message: {user_message}")
    full_prompt = "\n\n".join(prompt_parts)

    text = await llm_chat(
      system=PLANNER_SYSTEM_PROMPT,
      messages=[{"role": "user", "content": full_prompt}],
      max_tokens=2048,
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
        )
      )
    except (ValueError, KeyError) as exc:
      logger.warning("Skipping invalid task %s: %s", item, exc)
  return tasks
