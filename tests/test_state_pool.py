# StatePool unit tests – pure in-memory, no external deps
from __future__ import annotations

import pytest

from agent.memory.state_pool import StatePool
from agent.models import SessionState


class TestStatePool:
    """Tests for StatePool travel parameter storage."""

    def setup_method(self):
        self.pool = StatePool()

    @pytest.mark.asyncio
    async def test_get_empty_state(self):
        """New session returns a blank SessionState with all None fields."""
        state = await self.pool.get("new-session")
        assert isinstance(state, SessionState)
        assert state.destination is None
        assert state.origin is None
        assert state.budget is None
        assert state.travelers is None

    @pytest.mark.asyncio
    async def test_update_state(self):
        """update sets fields and get returns the updated state."""
        await self.pool.update("s1", destination="东京", travelers=2)
        state = await self.pool.get("s1")
        assert state.destination == "东京"
        assert state.travelers == 2

    @pytest.mark.asyncio
    async def test_update_partial(self):
        """Partial update does not affect other existing fields."""
        await self.pool.update("s1", destination="东京", budget="5000元")
        await self.pool.update("s1", travelers=3)

        state = await self.pool.get("s1")
        assert state.destination == "东京"
        assert state.budget == "5000元"
        assert state.travelers == 3

    @pytest.mark.asyncio
    async def test_update_ignores_none_values(self):
        """Passing None for a value does not overwrite the existing value."""
        await self.pool.update("s1", destination="东京")
        await self.pool.update("s1", destination=None, budget="3000")

        state = await self.pool.get("s1")
        assert state.destination == "东京"
        assert state.budget == "3000"

    @pytest.mark.asyncio
    async def test_update_ignores_unknown_fields(self):
        """Unknown field names are silently ignored."""
        await self.pool.update("s1", destination="大阪", nonexistent_field="oops")
        state = await self.pool.get("s1")
        assert state.destination == "大阪"
        assert not hasattr(state, "nonexistent_field")

    @pytest.mark.asyncio
    async def test_clear_state(self):
        """clear removes the session state; next get returns a fresh default."""
        await self.pool.update("s1", destination="巴厘岛")
        await self.pool.clear("s1")

        state = await self.pool.get("s1")
        assert state.destination is None

    @pytest.mark.asyncio
    async def test_update_from_dict(self):
        """update_from_dict works like update but from a plain dict."""
        await self.pool.update_from_dict("s1", {"destination": "首尔", "duration_days": 5})
        state = await self.pool.get("s1")
        assert state.destination == "首尔"
        assert state.duration_days == 5

    @pytest.mark.asyncio
    async def test_to_prompt_context_empty(self):
        """Empty state produces a default fallback string."""
        ctx = await self.pool.to_prompt_context("empty-session")
        assert ctx == "No travel parameters extracted yet."

    @pytest.mark.asyncio
    async def test_to_prompt_context_with_data(self):
        """Populated state produces a human-readable summary."""
        await self.pool.update("s1", destination="东京", travelers=2, budget="10000元")
        ctx = await self.pool.to_prompt_context("s1")
        assert "Destination: 东京" in ctx
        assert "Travelers: 2" in ctx
        assert "Budget: 10000元" in ctx

    @pytest.mark.asyncio
    async def test_multiple_sessions_isolated(self):
        """Different sessions have independent state."""
        await self.pool.update("s1", destination="东京")
        await self.pool.update("s2", destination="大阪")

        s1 = await self.pool.get("s1")
        s2 = await self.pool.get("s2")
        assert s1.destination == "东京"
        assert s2.destination == "大阪"
