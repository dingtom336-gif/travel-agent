# Battle Runner – automated persona vs orchestrator simulation
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, List, Optional

from agent.memory.session import session_memory
from agent.orchestrator.agent import orchestrator
from agent.simulator.env_simulator import get_env_simulator
from agent.simulator.evaluator import Evaluator
from agent.simulator.user_simulator import UserSimulator

logger = logging.getLogger(__name__)

user_simulator = UserSimulator()
evaluator = Evaluator()


@dataclass
class BattleResult:
  """Result of an automated battle between a persona and the orchestrator."""

  session_id: str
  persona_name: str
  scenario_name: Optional[str]
  turns_completed: int
  total_duration_ms: int
  messages: List[Dict[str, str]]
  evaluation: Dict[str, Any]
  traces: List[Dict[str, Any]]

  def to_dict(self) -> Dict[str, Any]:
    """Serialize to dict for API responses."""
    return {
      "session_id": self.session_id,
      "persona_name": self.persona_name,
      "scenario_name": self.scenario_name,
      "turns_completed": self.turns_completed,
      "total_duration_ms": self.total_duration_ms,
      "messages": self.messages,
      "evaluation": self.evaluation,
      "traces": self.traces,
    }


async def run_battle(
  persona_name: str,
  turns: int = 3,
  scenario_name: Optional[str] = None,
) -> BattleResult:
  """Run a full automated battle: persona messages → orchestrator → evaluate.

  Args:
    persona_name: Name of the persona to simulate
    turns: Number of conversation turns
    scenario_name: Optional scenario to activate before battle

  Returns:
    BattleResult with full conversation, evaluation, and traces
  """
  env_sim = get_env_simulator()
  start_time = time.time()

  # Generate session ID
  session_id = f"battle-{uuid.uuid4().hex[:8]}"

  # Optionally activate a fault scenario
  if scenario_name:
    env_sim.simulate_scenario(scenario_name)
    logger.info("Battle: activated scenario '%s'", scenario_name)

  # Generate user messages from persona
  persona = user_simulator.get_persona(persona_name)
  user_messages = user_simulator.generate_conversation(persona, turns=turns)

  # Run each turn through the real orchestrator
  all_messages: List[Dict[str, str]] = []
  turns_done = 0

  for msg in user_messages:
    user_text = msg["content"]
    all_messages.append({"role": "user", "content": user_text})

    try:
      # Collect full response by consuming the SSE stream
      import json
      text_parts: List[str] = []
      async for sse_chunk in orchestrator.handle_message(
        session_id=session_id,
        message=user_text,
      ):
        if isinstance(sse_chunk, dict):
          evt = sse_chunk.get("event", "")
          data_str = sse_chunk.get("data", "{}")
          try:
            payload = json.loads(data_str)
          except (json.JSONDecodeError, TypeError):
            continue
          if evt == "text":
            text_parts.append(payload.get("content", ""))

      assistant_text = "\n".join(text_parts) if text_parts else "[no response]"
      all_messages.append({"role": "assistant", "content": assistant_text})
      turns_done += 1

    except Exception as exc:
      logger.error("Battle turn %d failed: %s", turns_done + 1, exc)
      all_messages.append({
        "role": "assistant",
        "content": f"[ERROR: {exc}]",
      })
      turns_done += 1

  # Collect traces and evaluate
  traces = session_memory.get_traces(session_id)
  history = session_memory.get_history(session_id)
  report = evaluator.evaluate_conversation(
    messages=history if history else all_messages,
    agent_traces=traces,
  )

  # Reset faults after battle
  if scenario_name:
    env_sim.reset()

  duration_ms = int((time.time() - start_time) * 1000)

  return BattleResult(
    session_id=session_id,
    persona_name=persona_name,
    scenario_name=scenario_name,
    turns_completed=turns_done,
    total_duration_ms=duration_ms,
    messages=all_messages,
    evaluation=report.to_dict(),
    traces=traces,
  )


async def run_battle_stream(
  persona_name: str,
  turns: int = 3,
  scenario_name: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
  """Stream battle progress as events for SSE.

  Yields dicts with {event, data} for each step.
  """
  import json

  env_sim = get_env_simulator()
  session_id = f"battle-{uuid.uuid4().hex[:8]}"

  yield {
    "event": "battle_start",
    "data": json.dumps({
      "session_id": session_id,
      "persona": persona_name,
      "scenario": scenario_name,
      "turns": turns,
    }),
  }

  # Activate scenario
  if scenario_name:
    env_sim.simulate_scenario(scenario_name)
    yield {
      "event": "scenario_activated",
      "data": json.dumps({"scenario": scenario_name}),
    }

  persona = user_simulator.get_persona(persona_name)
  user_messages = user_simulator.generate_conversation(persona, turns=turns)
  all_messages: List[Dict[str, str]] = []

  for i, msg in enumerate(user_messages):
    user_text = msg["content"]
    all_messages.append({"role": "user", "content": user_text})

    yield {
      "event": "turn_start",
      "data": json.dumps({
        "turn": i + 1,
        "user_message": user_text,
      }),
    }

    try:
      text_parts: List[str] = []
      async for sse_chunk in orchestrator.handle_message(
        session_id=session_id,
        message=user_text,
      ):
        if isinstance(sse_chunk, dict):
          evt = sse_chunk.get("event", "")
          data_str = sse_chunk.get("data", "{}")
          try:
            payload = json.loads(data_str)
          except (json.JSONDecodeError, TypeError):
            continue
          if evt == "text":
            text_parts.append(payload.get("content", ""))

      assistant_text = "\n".join(text_parts) if text_parts else "[no response]"
      all_messages.append({"role": "assistant", "content": assistant_text})

      yield {
        "event": "turn_end",
        "data": json.dumps({
          "turn": i + 1,
          "assistant_response": assistant_text[:500],
        }),
      }
    except Exception as exc:
      logger.error("Battle turn %d error: %s", i + 1, exc)
      all_messages.append({"role": "assistant", "content": f"[ERROR: {exc}]"})
      yield {
        "event": "turn_error",
        "data": json.dumps({"turn": i + 1, "error": str(exc)}),
      }

  # Evaluate
  traces = session_memory.get_traces(session_id)
  history = session_memory.get_history(session_id)
  report = evaluator.evaluate_conversation(
    messages=history if history else all_messages,
    agent_traces=traces,
  )

  if scenario_name:
    env_sim.reset()

  yield {
    "event": "battle_complete",
    "data": json.dumps({
      "session_id": session_id,
      "turns_completed": len(user_messages),
      "evaluation": report.to_dict(),
      "traces": traces,
    }),
  }
