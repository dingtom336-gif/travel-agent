# Synthesis engine – combines agent results into user-facing responses
from __future__ import annotations

import logging
import time
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from agent.config.settings import get_settings
from agent.llm import llm_chat, llm_chat_stream
from agent.memory.session import session_memory
from agent.models import AgentResult, SSEEventType, SSEMessage
from agent.orchestrator.constants import (
  ORCHESTRATOR_SYSTEM_PROMPT,
  SYNTHESIS_OUTPUT_GUIDE,
)
from agent.orchestrator.context import build_context_with_summary, build_messages
from agent.orchestrator.ui_mapper import truncate_tool_data_for_synthesis

logger = logging.getLogger(__name__)


class Synthesizer:
  """Handles simple replies and full synthesis of agent results."""

  # ------------------------------------------------------------------ #
  # Simple reply
  # ------------------------------------------------------------------ #

  async def handle_simple(
    self,
    session_id: str,
    message: str,
    history: list[dict[str, Any]],
    personalization_ctx: str = "",
  ) -> AsyncGenerator[dict, None]:
    """Handle simple messages with a direct Claude call."""
    try:
      start = time.time()
      response = await self._call_claude_simple(
        message, history, personalization_ctx,
      )
      duration = int((time.time() - start) * 1000)

      await session_memory.add_trace(session_id, {
        "agent": "orchestrator",
        "task_id": f"simple-{uuid.uuid4().hex[:8]}",
        "goal": message[:100],
        "status": "success",
        "summary": response[:200],
        "duration_ms": duration,
        "error": None,
        "timestamp": time.time(),
      })

      yield SSEMessage(
        event=SSEEventType.TEXT,
        data={"content": response},
      ).format()
      await session_memory.add_message(session_id, "assistant", response)
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
  # Full synthesis (streaming)
  # ------------------------------------------------------------------ #

  async def synthesize_stream(
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

  async def synthesize(
    self,
    user_message: str,
    results: dict[str, AgentResult],
    state_ctx: str,
    history: list[dict[str, Any]],
    personalization_ctx: str = "",
  ) -> str:
    """Non-streaming synthesis."""
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

  # ------------------------------------------------------------------ #
  # Internals
  # ------------------------------------------------------------------ #

  async def _call_claude_simple(
    self,
    message: str,
    history: list[dict[str, Any]],
    personalization_ctx: str = "",
  ) -> str:
    """Quick LLM call for simple messages."""
    try:
      system_prompt = ORCHESTRATOR_SYSTEM_PROMPT
      if personalization_ctx:
        system_prompt += (
          f"\n\n--- User Profile ---\n{personalization_ctx}\n"
          "Use the above user preferences to personalize your response."
        )

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
      "IMPORTANT: 如果提供了用户画像/偏好，你必须在回答中明确引用并体现个性化。"
      "使用'根据您的偏好'、'考虑到您喜欢...'等表达，让用户感受到定制化服务。"
      "Respond in the user's language."
    )
    return prompt, combined

  @staticmethod
  def _build_personalization_instructions(personalization_ctx: str) -> str:
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
    if not instructions:
      instructions.append("- 在回答中自然引用用户在对话中表达的偏好和需求")
    return "### Personalization:\n" + "\n".join(instructions)
