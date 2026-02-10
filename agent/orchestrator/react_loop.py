# ReAct loop engine – Thought→Action→Observe→Reflect cycle
# v0.7.0: TIMING logs, context_summary passthrough
from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncGenerator
from typing import Any, Optional

from agent.config.settings import get_settings
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
from agent.orchestrator.constants import AGENT_DISPLAY_NAMES, AGENT_REGISTRY
from agent.orchestrator.context import build_context_with_summary
from agent.orchestrator.planner import decompose_tasks
from agent.orchestrator.reflector import (
  consistency_checker,
  identify_affected_agents,
  preflight_validator,
)
from agent.orchestrator.ui_mapper import extract_ui_components

logger = logging.getLogger(__name__)


class ReactEngine:
  """Runs the ReAct loop: decompose tasks, execute agents, reflect."""

  def __init__(self) -> None:
    # Per-session caches for incremental planning
    self._previous_tasks: dict[str, list[AgentTask]] = {}
    self._previous_results: dict[str, dict[str, AgentResult]] = {}

  async def run(
    self,
    session_id: str,
    message: str,
    history: list[dict[str, Any]],
    state_ctx: str,
    personalization_ctx: str,
    synthesize_fn: Any,
    conversation_summary: Optional[str] = None,
  ) -> AsyncGenerator[dict, None]:
    """Full ReAct cycle. Yields SSE dicts.

    Args:
      synthesize_fn: async generator that yields text chunks for synthesis.
      conversation_summary: Pre-built summary from agent.py (avoids duplicate LLM call).
    """
    try:
      # --- THOUGHT: Decompose into tasks ---
      yield SSEMessage(
        event=SSEEventType.THINKING,
        data={
          "agent": "orchestrator",
          "thought": "正在分解你的需求为子任务...",
        },
      ).format()

      t_planner = time.time()
      prev_tasks = self._previous_tasks.get(session_id)
      tasks = await decompose_tasks(message, state_ctx, history, prev_tasks)
      logger.info(
        "TIMING stage=planner duration_ms=%d session=%s",
        int((time.time() - t_planner) * 1000), session_id,
      )
      if not tasks:
        return

      # Reuse pre-built summary if available
      if conversation_summary is None:
        t_ctx = time.time()
        conversation_summary = await build_context_with_summary(history)
        logger.info(
          "TIMING stage=context_summary duration_ms=%d session=%s",
          int((time.time() - t_ctx) * 1000), session_id,
        )

      # --- ACTION: Execute tasks respecting dependencies ---
      results: dict[str, AgentResult] = {}

      # Reuse previous results for tasks marked reuse_previous
      prev_results = self._previous_results.get(session_id, {})
      reuse_tasks = [t for t in tasks if t.reuse_previous]
      active_tasks = [t for t in tasks if not t.reuse_previous]

      for task in reuse_tasks:
        cached = self._find_previous_result(prev_results, task.agent)
        if cached:
          results[task.task_id] = cached
          logger.info(
            "Reusing previous result for %s (session %s)",
            task.agent.value, session_id,
          )

      parallel_tasks = [t for t in active_tasks if not t.depends_on]
      dependent_tasks = [t for t in active_tasks if t.depends_on]

      # Execute parallel tasks concurrently, streaming results as each completes
      if parallel_tasks:
        yield SSEMessage(
          event=SSEEventType.THINKING,
          data={
            "agent": "orchestrator",
            "thought": f"正在调度 {len(parallel_tasks)} 个专家并行处理...",
          },
        ).format()

        t_agents = time.time()
        async for sse_or_result in self._execute_tasks_streaming(
          parallel_tasks, session_id, state_ctx, conversation_summary, results,
        ):
          yield sse_or_result
        logger.info(
          "TIMING stage=agents_parallel duration_ms=%d count=%d session=%s",
          int((time.time() - t_agents) * 1000), len(parallel_tasks), session_id,
        )

      # Execute dependent tasks sequentially
      for task in dependent_tasks:
        upstream = {}
        for dep_name in task.depends_on:
          for r in results.values():
            if r.agent.value == dep_name:
              upstream[dep_name] = r.data.get("response", r.summary)
        context = {
          "state_context": state_ctx,
          "upstream_results": upstream,
          "conversation_summary": conversation_summary,
        }

        yield SSEMessage(
          event=SSEEventType.AGENT_START,
          data={"agent": task.agent.value, "task": task.goal},
        ).format()

        t_dep = time.time()
        result = await self._execute_single_task(task, context)
        results[task.task_id] = result
        logger.info(
          "TIMING stage=agent_%s_dependent duration_ms=%d session=%s",
          task.agent.value, int((time.time() - t_dep) * 1000), session_id,
        )

        yield SSEMessage(
          event=SSEEventType.AGENT_RESULT,
          data={
            "agent": task.agent.value,
            "status": result.status.value,
            "summary": result.summary,
            "data": result.data,
          },
        ).format()

        for ui_event in extract_ui_components(task.agent.value, result.data):
          yield ui_event

      # --- REFLECT: Validate and correct results ---
      t_reflect = time.time()
      async for sse in self._reflect(
        session_id, message, results, state_ctx, conversation_summary,
      ):
        yield sse
      logger.info(
        "TIMING stage=reflector duration_ms=%d session=%s",
        int((time.time() - t_reflect) * 1000), session_id,
      )

      # --- SYNTHESIZE ---
      yield SSEMessage(
        event=SSEEventType.THINKING,
        data={
          "agent": "orchestrator",
          "thought": "正在综合所有专家结果，生成旅行方案...",
        },
      ).format()

      t_synth = time.time()
      full_response = ""
      async for chunk in synthesize_fn(
        message, results, state_ctx, history, personalization_ctx,
        context_summary=conversation_summary,
      ):
        full_response += chunk
        yield SSEMessage(
          event=SSEEventType.TEXT,
          data={"content": chunk},
        ).format()
      logger.info(
        "TIMING stage=synthesis duration_ms=%d session=%s",
        int((time.time() - t_synth) * 1000), session_id,
      )

      await session_memory.add_message(
        session_id, "assistant", full_response,
      )

      # Cache tasks and results for incremental planning on follow-ups
      self._previous_tasks[session_id] = tasks
      self._previous_results[session_id] = results

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
  # Reflection sub-loop
  # ------------------------------------------------------------------ #

  async def _reflect(
    self,
    session_id: str,
    message: str,
    results: dict[str, AgentResult],
    state_ctx: str,
    conversation_summary: str,
  ) -> AsyncGenerator[dict, None]:
    """Validate results and re-run agents if inconsistencies found."""
    # Skip reflection when most agents failed (can't fix rate-limit issues)
    success_count = sum(
      1 for r in results.values() if r.status == TaskStatus.SUCCESS
    )
    if success_count < 2:
      yield SSEMessage(
        event=SSEEventType.THINKING,
        data={
          "agent": "orchestrator",
          "thought": "部分专家暂时不可用，跳过结果验证。",
        },
      ).format()
      return

    reflection_round = 0
    MAX_REFLECTION_ROUNDS = 1

    while reflection_round < MAX_REFLECTION_ROUNDS:
      state = await state_pool.get(session_id)
      issues = preflight_validator.validate(results, state)

      has_errors = any(i.severity == "error" for i in issues)
      if has_errors:
        check = await consistency_checker.check(message, results, state_ctx)
        if not check.passed and check.state_corrections:
          await state_pool.update_from_dict(
            session_id, check.state_corrections,
          )
          state_ctx = await state_pool.to_prompt_context(session_id)

          yield SSEMessage(
            event=SSEEventType.THINKING,
            data={
              "agent": "orchestrator",
              "thought": "发现数据不一致，正在纠正...",
            },
          ).format()

          to_rerun = identify_affected_agents(check, results)
          for agent_name, _original in to_rerun:
            rerun_task = AgentTask(
              agent=AgentName(agent_name),
              goal="使用纠正后的参数重新查询",
            )

            display = AGENT_DISPLAY_NAMES.get(agent_name, agent_name)
            yield SSEMessage(
              event=SSEEventType.AGENT_START,
              data={
                "agent": agent_name,
                "task": f"正在纠正 {display} 的结果...",
              },
            ).format()

            new_result = await self._execute_single_task(
              rerun_task, {
                "state_context": state_ctx,
                "conversation_summary": conversation_summary,
              },
            )
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

      yield SSEMessage(
        event=SSEEventType.THINKING,
        data={
          "agent": "orchestrator",
          "thought": "所有结果已验证，未发现问题。",
        },
      ).format()
      break

  # ------------------------------------------------------------------ #
  # Incremental planning helpers
  # ------------------------------------------------------------------ #

  @staticmethod
  def _find_previous_result(
    prev_results: dict[str, AgentResult],
    agent: AgentName,
  ) -> AgentResult | None:
    """Find a previous result for a given agent name."""
    for result in prev_results.values():
      if result.agent == agent and result.status == TaskStatus.SUCCESS:
        return result
    return None

  # ------------------------------------------------------------------ #
  # Task execution
  # ------------------------------------------------------------------ #

  async def _execute_tasks_streaming(
    self,
    tasks: list[AgentTask],
    session_id: str,
    state_ctx: str,
    conversation_summary: str,
    results_out: dict[str, AgentResult],
  ) -> AsyncGenerator[dict, None]:
    """Run tasks in parallel, yielding SSE events as each agent completes.

    Results are stored into results_out dict as a side effect.
    """
    # Yield all AGENT_START messages immediately
    for t in tasks:
      yield SSEMessage(
        event=SSEEventType.AGENT_START,
        data={"agent": t.agent.value, "task": t.goal},
      ).format()

    context = {
      "state_context": state_ctx,
      "conversation_summary": conversation_summary,
    }

    # Launch all tasks concurrently
    future_to_task: dict[asyncio.Task, AgentTask] = {}
    for t in tasks:
      future = asyncio.create_task(self._execute_single_task(t, context))
      future_to_task[future] = t

    # Yield results as each agent completes (FIRST_COMPLETED)
    pending = set(future_to_task.keys())
    while pending:
      done, pending = await asyncio.wait(
        pending, return_when=asyncio.FIRST_COMPLETED,
      )
      for future in done:
        task = future_to_task[future]
        try:
          result = future.result()
        except Exception as exc:
          result = AgentResult(
            task_id=task.task_id,
            agent=task.agent,
            status=TaskStatus.FAILED,
            error=str(exc),
          )

        results_out[task.task_id] = result
        await session_memory.add_trace(session_id, {
          "agent": task.agent.value,
          "task_id": task.task_id,
          "goal": task.goal,
          "status": result.status.value,
          "summary": result.summary,
          "duration_ms": result.duration_ms,
          "error": result.error,
          "timestamp": time.time(),
        })

        display = AGENT_DISPLAY_NAMES.get(task.agent.value, task.agent.value)
        logger.info(
          "TIMING stage=agent_%s duration_ms=%d session=%s",
          task.agent.value, result.duration_ms or 0, session_id,
        )

        yield SSEMessage(
          event=SSEEventType.AGENT_RESULT,
          data={
            "agent": task.agent.value,
            "status": result.status.value,
            "summary": result.summary,
            "data": result.data,
          },
        ).format()

        for ui_event in extract_ui_components(task.agent.value, result.data):
          yield ui_event

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
      conv_summary = context.get("conversation_summary", "")
      if conv_summary:
        enriched_task = AgentTask(
          agent=task.agent,
          goal=f"{task.goal}\n\n[对话上下文]: {conv_summary}",
          depends_on=task.depends_on,
        )
      else:
        enriched_task = task

      settings = get_settings()
      return await asyncio.wait_for(
        agent.execute(enriched_task, context),
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
