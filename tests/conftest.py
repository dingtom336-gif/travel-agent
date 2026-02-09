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
