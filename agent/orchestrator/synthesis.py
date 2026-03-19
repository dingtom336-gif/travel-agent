# Synthesis engine – combines agent results into user-facing responses
from __future__ import annotations

import logging
import time
import uuid
from collections.abc import AsyncGenerator
from typing import Any, Optional

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

# --- Smart fallback when all LLM models fail ---
_NEGATIVE_EMOTION_KW = (
    "离婚", "癌症", "去世", "分手", "失恋", "吵架", "冷战",
    "抑郁", "焦虑", "自闭", "伤心", "难过", "委屈", "压力大",
    "走了", "离开", "生病", "治疗",
)
_POSITIVE_EMOTION_KW = (
    "上市", "毕业", "博士", "结婚", "升职", "退休", "聚会",
    "犒劳", "庆祝", "纪念", "拿到", "考上",
)


def _smart_fallback(message: str) -> str:
    """Context-aware fallback when all LLM models are unavailable."""
    msg = message.strip().lower()
    if any(w in msg for w in ("你好", "嗨", "hi", "hello")):
        return "你好！我是 TravelMind 旅行规划助手，无论是国内周边游还是出国度假，我都能帮你规划。想去哪里玩呢？"
    if any(w in msg for w in ("再见", "拜拜", "晚安")):
        return "期待下次为你规划旅行！祝你生活愉快。"
    if any(w in msg for w in ("谢谢", "感谢")):
        return "不客气！随时可以找我规划旅行。"
    if any(w in msg for w in _NEGATIVE_EMOTION_KW):
        return (
            "我理解你现在的心情。有时候出去走走，换个环境，确实能让人感觉好一些。"
            "如果你愿意，可以告诉我想去什么样的地方，我来帮你规划一趟旅行。"
        )
    if any(w in msg for w in _POSITIVE_EMOTION_KW):
        return (
            "恭喜你！这样的时刻值得好好庆祝。"
            "想不想来一趟旅行犒劳自己？告诉我你的想法，我来帮你规划！"
        )
    return "收到你的消息了！作为旅行助手，我最擅长帮你规划行程和推荐目的地。有什么旅行想法想聊聊吗？"


class Synthesizer:
  """Handles simple replies and full synthesis of agent results."""

  # ------------------------------------------------------------------ #
  # Simple reply – streaming (v0.7.0: converted from non-streaming)
  # ------------------------------------------------------------------ #

  async def handle_simple(
    self,
    session_id: str,
    message: str,
    history: list[dict[str, Any]],
    personalization_ctx: str = "",
  ) -> AsyncGenerator[dict, None]:
    """Handle simple messages with streaming LLM call."""
    try:
      start = time.time()

      system_prompt = ORCHESTRATOR_SYSTEM_PROMPT
      if personalization_ctx:
        system_prompt += (
          f"\n\n--- User Profile ---\n{personalization_ctx}\n"
          "Use the above user preferences to personalize your response."
        )

      # Only build context summary for longer conversations
      if len(history) > 4:
        context_summary = await build_context_with_summary(history)
        if context_summary:
          system_prompt += f"\n\n--- Conversation Context ---\n{context_summary}"

      messages = build_messages(history)

      full_response = ""
      got_content = False

      # Use WRITING_MODEL (GLM-4-32B, fastest at 122tok/s), fallback on failure
      settings = get_settings()
      for model_choice in (settings.WRITING_MODEL, "fallback"):
        try:
          async for chunk in llm_chat_stream(
            system=system_prompt,
            messages=messages,
            max_tokens=1024,
            model=model_choice,
          ):
            if chunk:
              got_content = True
              full_response += chunk
              yield SSEMessage(
                event=SSEEventType.TEXT,
                data={"content": chunk},
              ).format()
          if got_content:
            break
          logger.warning("handle_simple: model=%s returned empty, trying next", model_choice)
        except Exception as model_exc:
          logger.warning("handle_simple: model=%s failed: %s", model_choice, model_exc)
          continue

      if not got_content:
        # All models failed — generate contextual fallback based on user message
        logger.warning("handle_simple: all models failed, using smart fallback")
        fallback = _smart_fallback(message)
        full_response = fallback
        yield SSEMessage(
          event=SSEEventType.TEXT,
          data={"content": fallback},
        ).format()

      duration = int((time.time() - start) * 1000)
      logger.info("TIMING stage=simple_reply duration_ms=%d session=%s", duration, session_id)

      await session_memory.add_trace(session_id, {
        "agent": "orchestrator",
        "task_id": f"simple-{uuid.uuid4().hex[:8]}",
        "goal": message[:100],
        "status": "success",
        "summary": full_response[:200],
        "duration_ms": duration,
        "error": None,
        "timestamp": time.time(),
      })

      await session_memory.add_message(session_id, "assistant", full_response)
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
    context_summary: Optional[str] = None,
  ) -> AsyncGenerator[str, None]:
    """Stream synthesis – yields text chunks for SSE.

    Args:
      context_summary: Pre-built conversation summary from react_loop.
                       If provided, skips the duplicate LLM call.
    """
    settings = get_settings()
    # Reuse pre-built summary if available, otherwise build fresh
    if context_summary is None:
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
        yield f"以下是根据分析结果整理的旅行方案：\n\n{combined}"
    except Exception as exc:
      logger.warning("Synthesis stream failed: %s", exc)
      yield f"以下是为你整理的旅行方案：\n\n{combined}"

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
        return f"以下是根据分析结果整理的旅行方案：\n\n{combined}"
      return result
    except Exception as exc:
      logger.warning("Synthesis LLM call failed: %s", exc)
      return f"以下是为你整理的旅行方案：\n\n{combined}"

  # ------------------------------------------------------------------ #
  # Internals
  # ------------------------------------------------------------------ #

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
