# Timeout behavior tests – verifies agents don't hang forever
# Zero LLM token cost: uses mock agents with asyncio.sleep
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from agent.models import AgentName, AgentResult, AgentTask, TaskStatus
from agent.orchestrator.agent import OrchestratorAgent


class SlowAgent:
    """Fake agent that sleeps forever — simulates a hung LLM call."""

    async def execute(self, task, context):
        await asyncio.sleep(999)


class FastAgent:
    """Fake agent that returns immediately."""

    def __init__(self, result: AgentResult):
        self._result = result

    async def execute(self, task, context):
        return self._result


@pytest.mark.asyncio
async def test_slow_agent_times_out():
    """Agent exceeding LLM_TASK_TIMEOUT returns FAILED, not hangs."""
    orch = OrchestratorAgent()
    task = AgentTask(agent=AgentName.WEATHER, goal="test timeout")
    context = {"state_context": ""}

    with patch.dict(
        "agent.orchestrator.react_loop.AGENT_REGISTRY",
        {AgentName.WEATHER: SlowAgent()},
    ):
        with patch("agent.orchestrator.react_loop.get_settings") as mock_settings:
            mock_settings.return_value.LLM_TASK_TIMEOUT = 0.5
            result = await orch._execute_single_task(task, context)

    assert result.status == TaskStatus.FAILED
    assert "timed out" in result.error.lower()


@pytest.mark.asyncio
async def test_normal_agent_completes():
    """Agent completing within timeout returns SUCCESS."""
    orch = OrchestratorAgent()
    task = AgentTask(agent=AgentName.WEATHER, goal="test ok")
    context = {"state_context": ""}

    fast_result = AgentResult(
        task_id=task.task_id,
        agent=AgentName.WEATHER,
        status=TaskStatus.SUCCESS,
        summary="Sunny",
    )

    with patch.dict(
        "agent.orchestrator.react_loop.AGENT_REGISTRY",
        {AgentName.WEATHER: FastAgent(fast_result)},
    ):
        with patch("agent.orchestrator.react_loop.get_settings") as mock_settings:
            mock_settings.return_value.LLM_TASK_TIMEOUT = 10.0
            result = await orch._execute_single_task(task, context)

    assert result.status == TaskStatus.SUCCESS
    assert result.summary == "Sunny"
