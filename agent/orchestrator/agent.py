# Orchestrator Agent – the central brain that coordinates everything
from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from agent.config.settings import get_settings
from agent.llm import llm_chat, llm_chat_stream
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
from agent.orchestrator.reflector import (
  consistency_checker,
  identify_affected_agents,
  preflight_validator,
)
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

# Agent display names for Chinese UI
agentDisplayNames: dict[str, str] = {
  "orchestrator": "主控大脑",
  "transport": "交通专家",
  "hotel": "住宿专家",
  "poi": "目的地专家",
  "itinerary": "行程编排师",
  "budget": "预算管家",
  "knowledge": "知识顾问",
  "weather": "天气助手",
  "customer_service": "客服专家",
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
- **Smart clarification**: If the user's request lacks critical info that you cannot reasonably infer from context, naturally weave 1-2 clarifying questions into your response. But if you can make reasonable assumptions (e.g., budget range, travel style), just proceed and mention your assumptions. Never ask more than 2 questions at once. Never ask about things you can figure out yourself.
- **Geographic logic**: When presenting itineraries, ensure geographic rationality: group nearby locations on the same day, arrange multi-city routes to minimize backtracking (e.g., 北京→天津→广州 not 北京→广州→天津)."""

# Rich output formatting guide injected into synthesis prompts
SYNTHESIS_OUTPUT_GUIDE = """
## Output Format Guidelines

Based on the content type, CHOOSE the most fitting format. Do NOT always use the same structure. Vary your presentation across messages.

### Format Toolkit (use as appropriate):
1. **Comparison Tables** — markdown tables for comparing 2+ options (flights, hotels, restaurants). Include key differentiators.
2. **Highlight Blockquotes** — Use `>` for key recommendations, insider tips, or important warnings.
3. **Emoji Section Headers** — Create visual rhythm: "✈️ **航班推荐**", "🏨 **住宿方案**", "🎯 **今日亮点**", "💡 **实用贴士**"
4. **Bold Key Stats** — Emphasize important numbers: **¥3,200/晚**, **4.8分**, **步行15分钟**
5. **Section Dividers** — Use `---` between major sections for clear visual separation.
6. **Bullet Tips** — Use bullet lists for practical tips, packing advice, reminders.
7. **Numbered Steps** — Use ordered lists for itinerary sequences or step-by-step guides.

### Content-Adaptive Strategy:
- **Flight/Hotel results** → Lead with a summary sentence, then comparison table, then blockquote recommendation
- **Destination guides** → Emoji headers for sections, mix highlights and practical tips
- **Complete itinerary** → Day-by-day with emoji headers (🌅 Day 1), brief description per day, highlight must-sees
- **Budget analysis** → Summary paragraph, then itemized breakdown
- **Weather/tips** → Concise bullets with practical clothing/preparation suggestions
- **Q&A / follow-up** → Conversational tone, skip heavy formatting, be direct

### Component Placeholders:
You can embed rich card components inline by placing these markers in your text:
- `{{flight_cards}}` — Insert flight comparison cards here
- `{{hotel_cards}}` — Insert hotel recommendation cards here
- `{{poi_cards}}` — Insert point-of-interest cards here
- `{{weather_cards}}` — Insert weather forecast cards here
- `{{timeline}}` — Insert day-by-day timeline here
- `{{budget_chart}}` — Insert budget breakdown chart here

Use them naturally in your text flow. Example:
"以下是为您精选的航班方案：

{{flight_cards}}

综合来看，我推荐 XX 航班，性价比最高。"

If no placeholders are used, cards will appear after your text.

{personalization_instructions}

### Important:
- VARY your structure across messages. If you used tables last time, try a different lead this time.
- Keep response under 800 chars for simple queries, up to 2000 for complex plans.
- Never output raw JSON or code. Always present data in human-readable markdown.
"""

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

      # Step 1+2: Extract state AND classify complexity in parallel
      history = session_memory.get_history(session_id)
      # Check if session already has travel context (e.g. destination set)
      existing_state = state_pool.get(session_id)
      has_travel_context = bool(existing_state and existing_state.destination)

      _, complexity = await asyncio.gather(
        extract_state(session_id, message, history, existing_state),
        classify_complexity(message, history, has_travel_context),
      )

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
          "thought": "正在分解你的需求为子任务...",
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
            "thought": f"正在调度 {len(parallel_tasks)} 个专家并行处理...",
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

      # --- REFLECT: Validate and correct results ---
      reflection_round = 0
      MAX_REFLECTION_ROUNDS = 1

      while reflection_round < MAX_REFLECTION_ROUNDS:
        state = state_pool.get(session_id)
        issues = preflight_validator.validate(results, state)

        has_errors = any(i.severity == "error" for i in issues)
        if has_errors:
          check = await consistency_checker.check(
            message, results, state_ctx,
          )
          if not check.passed and check.state_corrections:
            # Apply corrections to state pool
            state_pool.update_from_dict(
              session_id, check.state_corrections,
            )
            state_ctx = state_pool.to_prompt_context(session_id)

            yield SSEMessage(
              event=SSEEventType.THINKING,
              data={
                "agent": "orchestrator",
                "thought": "发现数据不一致，正在纠正...",
              },
            ).format()

            # Re-run affected agents with corrected state
            to_rerun = identify_affected_agents(check, results)
            for agent_name, _original in to_rerun:
              rerun_task = AgentTask(
                agent=AgentName(agent_name),
                goal="使用纠正后的参数重新查询",
              )

              yield SSEMessage(
                event=SSEEventType.AGENT_START,
                data={
                  "agent": agent_name,
                  "task": f"正在纠正 {agentDisplayNames.get(agent_name, agent_name)} 的结果...",
                },
              ).format()

              new_result = await self._execute_single_task(
                rerun_task, {"state_context": state_ctx},
              )
              # Replace old result in the results dict
              for tid, old_r in list(results.items()):
                if old_r.agent.value == agent_name:
                  results[tid] = new_result
                  break

              yield SSEMessage(
                event=SSEEventType.AGENT_RESULT,
                data={
                  "agent": agent_name,
                  "status": new_result.status.value,
                  "summary": new_result.summary,
                  "data": new_result.data,
                },
              ).format()

              for ui_event in extract_ui_components(
                agent_name, new_result.data,
              ):
                yield ui_event

            reflection_round += 1
            continue

        # Always emit validation feedback so user sees verification happened
        yield SSEMessage(
          event=SSEEventType.THINKING,
          data={
            "agent": "orchestrator",
            "thought": "所有结果已验证，未发现问题。",
          },
        ).format()
        break  # No issues or only warnings

      # --- SYNTHESIZE: Stream combined results to user ---
      yield SSEMessage(
        event=SSEEventType.THINKING,
        data={
          "agent": "orchestrator",
          "thought": "正在综合所有专家结果，生成旅行方案...",
        },
      ).format()

      full_response = ""
      async for chunk in self._synthesize_stream(
        message, results, state_ctx, history, personalization_ctx,
      ):
        full_response += chunk
        yield SSEMessage(
          event=SSEEventType.TEXT,
          data={"content": chunk},
        ).format()

      session_memory.add_message(
        session_id, "assistant", full_response,
      )

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

  def _build_personalization_instructions(self, personalization_ctx: str) -> str:
    """Generate format instructions based on user profile."""
    if not personalization_ctx:
      return ""
    instructions: list[str] = []
    ctx_lower = personalization_ctx.lower()
    if "经济" in ctx_lower or "省钱" in ctx_lower or "budget" in ctx_lower:
      instructions.append("- Emphasize prices and value comparisons. Show price per person when possible.")
    if "奢华" in ctx_lower or "高端" in ctx_lower or "luxury" in ctx_lower:
      instructions.append("- Highlight premium features, exclusive experiences, star ratings.")
    if "亲子" in ctx_lower or "孩子" in ctx_lower or "family" in ctx_lower:
      instructions.append("- Mention child-friendliness, age suitability, family facilities.")
    if "美食" in ctx_lower or "吃" in ctx_lower or "foodie" in ctx_lower:
      instructions.append("- Include restaurant recommendations with must-try dishes.")
    if "摄影" in ctx_lower or "拍照" in ctx_lower or "photo" in ctx_lower:
      instructions.append("- Mention best photo spots and golden hour times.")
    if instructions:
      return "### Personalization:\n" + "\n".join(instructions)
    return ""

  def _build_synthesis_prompt(
    self,
    user_message: str,
    results: dict[str, AgentResult],
    state_ctx: str,
    context_summary: str = "",
    personalization_ctx: str = "",
  ) -> tuple[str, str]:
    """Build synthesis prompt and combined results string."""
    result_summaries: list[str] = []
    for result in results.values():
      agent_data = result.data.get("response", result.summary)
      tool_summary = truncate_tool_data_for_synthesis(result.data)
      result_summaries.append(
        f"### {result.agent.value} agent result:\n{agent_data}{tool_summary}"
      )
    combined = "\n\n".join(result_summaries)

    context_block = ""
    if context_summary:
      context_block = f"Conversation context:\n{context_summary}\n\n"

    # Build personalization-aware output guide
    personal_instr = self._build_personalization_instructions(personalization_ctx)
    output_guide = SYNTHESIS_OUTPUT_GUIDE.replace(
      "{personalization_instructions}", personal_instr,
    )

    prompt = (
      f"{context_block}"
      f"Latest user message: {user_message}\n\n"
      f"Current travel parameters:\n{state_ctx}\n\n"
      f"Agent results:\n{combined}\n\n"
      f"{output_guide}\n\n"
      "Synthesize a coherent, well-structured response. "
      "If this is a follow-up, UPDATE the plan with new info, don't restart. "
      "If critical info is missing and cannot be inferred, naturally ask 1-2 questions in your response. "
      "Respond in the user's language."
    )
    return prompt, combined

  async def _synthesize_stream(
    self,
    user_message: str,
    results: dict[str, AgentResult],
    state_ctx: str,
    history: list[dict[str, Any]],
    personalization_ctx: str = "",
  ) -> AsyncGenerator[str, None]:
    """Stream synthesis – yields text chunks for SSE."""
    settings = get_settings()
    context_summary = await build_context_with_summary(history)
    prompt, combined = self._build_synthesis_prompt(
      user_message, results, state_ctx, context_summary, personalization_ctx,
    )

    try:
      got_content = False
      async for chunk in llm_chat_stream(
        system=ORCHESTRATOR_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=settings.LLM_MAX_TOKENS,
      ):
        if chunk:
          got_content = True
          yield chunk
      if not got_content:
        yield f"[MOCK] Here is your travel plan based on our analysis:\n\n{combined}"
    except Exception as exc:
      logger.warning("Synthesis stream failed: %s", exc)
      yield f"[MOCK] Here is your travel plan:\n\n{combined}"

  async def _synthesize(
    self,
    user_message: str,
    results: dict[str, AgentResult],
    state_ctx: str,
    history: list[dict[str, Any]],
    personalization_ctx: str = "",
  ) -> str:
    """Non-streaming synthesis – used by _handle_simple fallback."""
    settings = get_settings()
    context_summary = await build_context_with_summary(history)
    prompt, combined = self._build_synthesis_prompt(
      user_message, results, state_ctx, context_summary, personalization_ctx,
    )

    try:
      result = await llm_chat(
        system=ORCHESTRATOR_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
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
