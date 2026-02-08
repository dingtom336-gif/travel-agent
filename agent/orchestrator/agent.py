# Orchestrator Agent – the central brain that coordinates everything
from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from agent.config.settings import get_settings
from agent.llm import llm_chat
from agent.memory.profile import profile_manager
from agent.memory.session import session_memory
from agent.memory.state_pool import state_pool
from agent.models import (
  AgentName,
  AgentResult,
  AgentTask,
  SSEEventType,
  SSEMessage,
  TaskStatus,
)
from agent.orchestrator.context import build_context_with_summary, build_messages
from agent.orchestrator.planner import decompose_tasks
from agent.orchestrator.router import classify_complexity
from agent.orchestrator.state_extractor import extract_state
from agent.orchestrator.ui_mapper import (
  extract_ui_components,
  truncate_tool_data_for_synthesis,
)
from agent.teams.base import BaseAgent
from agent.teams.budget import BudgetAgent
from agent.teams.customer_service import CustomerServiceAgent
from agent.teams.hotel import HotelAgent
from agent.teams.itinerary import ItineraryAgent
from agent.teams.knowledge import KnowledgeAgent
from agent.teams.poi import POIAgent
from agent.teams.transport import TransportAgent
from agent.teams.weather import WeatherAgent

logger = logging.getLogger(__name__)

# --- Agent registry ---
AGENT_REGISTRY: dict[AgentName, BaseAgent] = {
  AgentName.TRANSPORT: TransportAgent(),
  AgentName.HOTEL: HotelAgent(),
  AgentName.POI: POIAgent(),
  AgentName.ITINERARY: ItineraryAgent(),
  AgentName.BUDGET: BudgetAgent(),
  AgentName.KNOWLEDGE: KnowledgeAgent(),
  AgentName.WEATHER: WeatherAgent(),
  AgentName.CUSTOMER_SERVICE: CustomerServiceAgent(),
}

# System prompt for quick replies and final synthesis
ORCHESTRATOR_SYSTEM_PROMPT = """You are TravelMind, a friendly and professional AI travel planning assistant.

When responding:
- Use the same language as the user (Chinese or English).
- Be warm, concise, and helpful.
- If the user greets you, respond naturally and ask how you can help with travel planning.
- If you receive results from specialist agents, synthesize them into a coherent, well-structured response.
- Use markdown formatting for readability.
- Always be encouraging and proactive in gathering travel preferences.
- **Conversation continuity**: Treat each message as a continuation of the conversation. If the user provides new info (like "from Shanghai"), UPDATE your previous advice rather than starting over. Reference what was discussed before.
- **Smart clarification**: If the user's request lacks critical info that you cannot reasonably infer from context, naturally weave 1-2 clarifying questions into your response. But if you can make reasonable assumptions (e.g., budget range, travel style), just proceed and mention your assumptions. Never ask more than 2 questions at once. Never ask about things you can figure out yourself."""

class OrchestratorAgent:
  """Central agent that drives the ReAct loop and coordinates specialist agents."""

  async def handle_message(
    self,
    session_id: str | None,
    message: str,
  ) -> AsyncGenerator[dict, None]:
    """Main entry point – yields SSE-formatted strings."""
    try:
      # Ensure session
      if not session_id:
        session_id = str(uuid.uuid4())

      # Store user message
      session_memory.add_message(session_id, "user", message)

      # Step 0: Load personalization context from user profile
      # Use session_id as user_id for now (will be replaced by real auth later)
      user_id = session_id
      personalization_ctx = profile_manager.get_personalization_context(user_id)

      # Step 1: Extract state from user message
      yield SSEMessage(
        event=SSEEventType.THINKING,
        data={"agent": "orchestrator", "thought": "Analyzing your request..."},
      ).format()

      await extract_state(session_id, message)

      # Step 2: Route – simple or complex?
      history = session_memory.get_history(session_id)
      complexity = await classify_complexity(message, history)

      if complexity == "simple":
        async for chunk in self._handle_simple(
          session_id, message, history, personalization_ctx,
        ):
          yield chunk
        # Learn from session after reply
        self._learn_from_session_safe(user_id, history)
        return

      # Step 3: Complex → full ReAct loop
      async for chunk in self._react_loop(
        session_id, message, history, personalization_ctx,
      ):
        yield chunk

      # Learn from session after full ReAct loop
      updated_history = session_memory.get_history(session_id)
      self._learn_from_session_safe(user_id, updated_history)

    except Exception as exc:
      logger.exception("Orchestrator error")
      yield SSEMessage(
        event=SSEEventType.ERROR,
        data={"error": str(exc)},
      ).format()
      yield SSEMessage(
        event=SSEEventType.DONE,
        data={"session_id": session_id or ""},
      ).format()

  # ------------------------------------------------------------------ #
  # Simple reply
  # ------------------------------------------------------------------ #

  async def _handle_simple(
    self,
    session_id: str,
    message: str,
    history: list[dict[str, Any]],
    personalization_ctx: str = "",
  ) -> AsyncGenerator[dict, None]:
    """Handle simple messages with a direct Claude call."""
    try:
      response = await self._call_claude_simple(
        message, history, personalization_ctx,
      )
      yield SSEMessage(
        event=SSEEventType.TEXT,
        data={"content": response},
      ).format()
      session_memory.add_message(session_id, "assistant", response)
      yield SSEMessage(
        event=SSEEventType.DONE,
        data={"session_id": session_id},
      ).format()
    except Exception as exc:
      logger.exception("Simple handler error")
      yield SSEMessage(
        event=SSEEventType.ERROR,
        data={"error": str(exc)},
      ).format()

  # ------------------------------------------------------------------ #
  # ReAct Loop
  # ------------------------------------------------------------------ #

  async def _react_loop(
    self,
    session_id: str,
    message: str,
    history: list[dict[str, Any]],
    personalization_ctx: str = "",
  ) -> AsyncGenerator[dict, None]:
    """Thought -> Action -> Observe -> Reflect cycle."""
    try:
      state_ctx = state_pool.to_prompt_context(session_id)
      # Append personalization context to state context
      if personalization_ctx:
        state_ctx += f"\n\n--- User Profile ---\n{personalization_ctx}"

      # --- THOUGHT: Decompose into tasks ---
      yield SSEMessage(
        event=SSEEventType.THINKING,
        data={
          "agent": "orchestrator",
          "thought": "Breaking down your request into sub-tasks...",
        },
      ).format()

      tasks = await decompose_tasks(message, state_ctx, history)
      if not tasks:
        # Planner returned empty list – treat as simple
        async for chunk in self._handle_simple(session_id, message, history):
          yield chunk
        return

      # --- ACTION: Execute tasks respecting dependencies ---
      results: dict[str, AgentResult] = {}

      # Separate parallel and dependent tasks
      parallel_tasks = [t for t in tasks if not t.depends_on]
      dependent_tasks = [t for t in tasks if t.depends_on]

      # Execute parallel tasks concurrently
      if parallel_tasks:
        yield SSEMessage(
          event=SSEEventType.THINKING,
          data={
            "agent": "orchestrator",
            "thought": f"Dispatching {len(parallel_tasks)} parallel tasks...",
          },
        ).format()

        parallel_sse, parallel_results = await self._execute_tasks_parallel(
          parallel_tasks, session_id, state_ctx,
        )
        for sse_msg in parallel_sse:
          yield sse_msg
        results.update(parallel_results)

      # Execute dependent tasks sequentially (they need upstream results)
      for task in dependent_tasks:
        # Build upstream context
        upstream = {}
        for dep_name in task.depends_on:
          for r in results.values():
            if r.agent.value == dep_name:
              upstream[dep_name] = r.data.get("response", r.summary)
        context = {
          "state_context": state_ctx,
          "upstream_results": upstream,
        }

        yield SSEMessage(
          event=SSEEventType.AGENT_START,
          data={"agent": task.agent.value, "task": task.goal},
        ).format()

        result = await self._execute_single_task(task, context)
        results[task.task_id] = result

        yield SSEMessage(
          event=SSEEventType.AGENT_RESULT,
          data={
            "agent": task.agent.value,
            "status": result.status.value,
            "summary": result.summary,
            "data": result.data,
          },
        ).format()

        # Emit UI component events for structured data
        for ui_event in extract_ui_components(task.agent.value, result.data):
          yield ui_event

      # --- OBSERVE & REFLECT: Synthesize all results ---
      yield SSEMessage(
        event=SSEEventType.THINKING,
        data={
          "agent": "orchestrator",
          "thought": "Synthesizing results from all agents...",
        },
      ).format()

      final_response = await self._synthesize(
        message, results, state_ctx, history,
      )

      yield SSEMessage(
        event=SSEEventType.TEXT,
        data={"content": final_response},
      ).format()

      session_memory.add_message(session_id, "assistant", final_response)

      yield SSEMessage(
        event=SSEEventType.DONE,
        data={"session_id": session_id},
      ).format()

    except Exception as exc:
      logger.exception("ReAct loop error")
      yield SSEMessage(
        event=SSEEventType.ERROR,
        data={"error": str(exc)},
      ).format()

  # ------------------------------------------------------------------ #
  # Task execution helpers
  # ------------------------------------------------------------------ #

  async def _execute_tasks_parallel(
    self,
    tasks: list[AgentTask],
    session_id: str,
    state_ctx: str,
  ) -> tuple[list[dict], dict[str, AgentResult]]:
    """Run independent tasks concurrently; return SSE messages and results."""
    sse_messages: list[dict] = []
    for t in tasks:
      sse_messages.append(
        SSEMessage(
          event=SSEEventType.AGENT_START,
          data={"agent": t.agent.value, "task": t.goal},
        ).format()
      )

    context = {"state_context": state_ctx}
    coros = [self._execute_single_task(t, context) for t in tasks]
    raw_results = await asyncio.gather(*coros, return_exceptions=True)

    results: dict[str, AgentResult] = {}
    for task, res in zip(tasks, raw_results):
      if isinstance(res, Exception):
        result = AgentResult(
          task_id=task.task_id,
          agent=task.agent,
          status=TaskStatus.FAILED,
          error=str(res),
        )
      else:
        result = res
      results[task.task_id] = result
      sse_messages.append(
        SSEMessage(
          event=SSEEventType.AGENT_RESULT,
          data={
            "agent": task.agent.value,
            "status": result.status.value,
            "summary": result.summary,
            "data": result.data,
          },
        ).format()
      )
      # Emit UI component events for structured data
      for ui_event in extract_ui_components(task.agent.value, result.data):
        sse_messages.append(ui_event)

    return sse_messages, results

  async def _execute_single_task(
    self,
    task: AgentTask,
    context: dict[str, Any],
  ) -> AgentResult:
    """Dispatch a single task to the appropriate agent with timeout."""
    agent = AGENT_REGISTRY.get(task.agent)
    if not agent:
      return AgentResult(
        task_id=task.task_id,
        agent=task.agent,
        status=TaskStatus.FAILED,
        error=f"No agent registered for {task.agent.value}",
      )
    try:
      settings = get_settings()
      return await asyncio.wait_for(
        agent.execute(task, context),
        timeout=settings.LLM_TASK_TIMEOUT,
      )
    except asyncio.TimeoutError:
      return AgentResult(
        task_id=task.task_id,
        agent=task.agent,
        status=TaskStatus.FAILED,
        error=f"Agent {task.agent.value} timed out after {get_settings().LLM_TASK_TIMEOUT}s",
      )
    except Exception as exc:
      return AgentResult(
        task_id=task.task_id,
        agent=task.agent,
        status=TaskStatus.FAILED,
        error=str(exc),
      )

  # ------------------------------------------------------------------ #
  # Claude helpers
  # ------------------------------------------------------------------ #

  async def _call_claude_simple(
    self,
    message: str,
    history: list[dict[str, Any]],
    personalization_ctx: str = "",
  ) -> str:
    """Quick LLM call for simple messages."""
    try:
      # Inject personalization context into system prompt
      system_prompt = ORCHESTRATOR_SYSTEM_PROMPT
      if personalization_ctx:
        system_prompt += (
          f"\n\n--- User Profile ---\n{personalization_ctx}\n"
          "Use the above user preferences to personalize your response."
        )

      # Build messages with compressed history for context continuity
      context_summary = await build_context_with_summary(history)
      if context_summary and len(history) > 4:
        system_prompt += f"\n\n--- Conversation Context ---\n{context_summary}"

      messages = build_messages(history)
      result = await llm_chat(
        system=system_prompt,
        messages=messages,
        max_tokens=1024,
      )
      if result is None:
        return (
          "[MOCK] Hi! I'm TravelMind, your AI travel planning assistant. "
          "I can help you plan trips, find flights, hotels, attractions, and more. "
          "Where would you like to go?"
        )
      return result
    except Exception as exc:
      logger.warning("Simple LLM call failed: %s", exc)
      return (
        "[MOCK] Hi! I'm TravelMind. I'm here to help you plan your perfect trip. "
        "What destination are you considering?"
      )

  async def _synthesize(
    self,
    user_message: str,
    results: dict[str, AgentResult],
    state_ctx: str,
    history: list[dict[str, Any]],
  ) -> str:
    """Combine all agent results into a coherent final answer."""
    settings = get_settings()

    # Build a summary of all agent results (include tool_data for richer synthesis)
    result_summaries: list[str] = []
    for result in results.values():
      agent_data = result.data.get("response", result.summary)
      tool_summary = truncate_tool_data_for_synthesis(result.data)
      result_summaries.append(
        f"### {result.agent.value} agent result:\n{agent_data}{tool_summary}"
      )
    combined = "\n\n".join(result_summaries)

    # Inject conversation context for continuity
    context_summary = await build_context_with_summary(history)
    context_block = ""
    if context_summary:
      context_block = f"Conversation context:\n{context_summary}\n\n"

    synthesis_prompt = (
      f"{context_block}"
      f"Latest user message: {user_message}\n\n"
      f"Current travel parameters:\n{state_ctx}\n\n"
      f"Agent results:\n{combined}\n\n"
      "Synthesize a coherent, well-structured response. "
      "If this is a follow-up, UPDATE the plan with new info, don't restart. "
      "If critical info is missing and cannot be inferred, naturally ask 1-2 questions in your response. "
      "Use markdown. Respond in the user's language."
    )

    try:
      result = await llm_chat(
        system=ORCHESTRATOR_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": synthesis_prompt}],
        max_tokens=settings.LLM_MAX_TOKENS,
      )
      if result is None:
        return f"[MOCK] Here is your travel plan based on our analysis:\n\n{combined}"
      return result
    except Exception as exc:
      logger.warning("Synthesis LLM call failed: %s", exc)
      return f"[MOCK] Here is your travel plan:\n\n{combined}"

  def _learn_from_session_safe(
    self,
    user_id: str,
    history: list[dict[str, Any]],
  ) -> None:
    """Learn user preferences from session – never raises."""
    try:
      profile_manager.learn_from_session(user_id, history)
    except Exception as exc:
      logger.warning("Profile learning failed (non-fatal): %s", exc)



# Singleton
orchestrator = OrchestratorAgent()
