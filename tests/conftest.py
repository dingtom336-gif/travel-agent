# Shared fixtures for TravelMind tests – zero LLM token cost
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def mock_llm(monkeypatch):
    """Replace llm_chat with a mock that returns a fixed string.

    This ensures tests never call the real DeepSeek API (zero token cost).
    """
    fake = AsyncMock(return_value="Mock LLM response for testing.")
    monkeypatch.setattr("agent.llm.llm_chat", fake)
    monkeypatch.setattr("agent.llm.client.llm_chat", fake)
    monkeypatch.setattr("agent.orchestrator.synthesis.llm_chat", fake, raising=False)
    monkeypatch.setattr("agent.orchestrator.planner.llm_chat", fake, raising=False)
    monkeypatch.setattr("agent.orchestrator.router.llm_chat", fake, raising=False)
    monkeypatch.setattr("agent.orchestrator.context.llm_chat", fake, raising=False)
    monkeypatch.setattr("agent.orchestrator.state_extractor.llm_chat", fake, raising=False)
    monkeypatch.setattr("agent.teams.base.llm_chat", fake, raising=False)
    return fake


@pytest.fixture(autouse=True)
def reset_sse_app_status():
    """Reset sse-starlette global AppStatus between tests.

    sse-starlette uses a module-level AppStatus with a global
    should_exit_event that leaks across event loops in different tests.
    """
    yield
    try:
        from sse_starlette.sse import AppStatus
        AppStatus.should_exit = False
        AppStatus.should_exit_event = None
    except (ImportError, AttributeError):
        pass
