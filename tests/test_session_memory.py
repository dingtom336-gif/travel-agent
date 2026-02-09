# SessionMemory unit tests – pure in-memory, no external deps
from __future__ import annotations

from unittest.mock import patch

import pytest

from agent.memory.session import SessionMemory


class TestSessionMemory:
    """Tests for SessionMemory short-term conversation storage."""

    def setup_method(self):
        self.mem = SessionMemory()

    @pytest.mark.asyncio
    async def test_get_history_empty(self):
        """New session returns an empty list."""
        assert await self.mem.get_history("new-session") == []

    @pytest.mark.asyncio
    async def test_add_and_get_message(self):
        """Messages are stored and retrievable in order."""
        await self.mem.add_message("s1", "user", "Hello")
        await self.mem.add_message("s1", "assistant", "Hi there!")

        history = await self.mem.get_history("s1")
        assert len(history) == 2
        assert history[0] == {"role": "user", "content": "Hello"}
        assert history[1] == {"role": "assistant", "content": "Hi there!"}

    @pytest.mark.asyncio
    async def test_add_and_get_trace(self):
        """Traces are stored and retrievable."""
        trace = {"agent": "poi", "status": "success", "duration_ms": 120}
        await self.mem.add_trace("s1", trace)

        traces = await self.mem.get_traces("s1")
        assert len(traces) == 1
        assert traces[0]["agent"] == "poi"

    @pytest.mark.asyncio
    async def test_get_traces_empty(self):
        """New session returns empty traces."""
        assert await self.mem.get_traces("no-such-session") == []

    @pytest.mark.asyncio
    async def test_clear_session(self):
        """Clear removes both messages and traces."""
        await self.mem.add_message("s1", "user", "Test")
        await self.mem.add_trace("s1", {"agent": "weather"})

        await self.mem.clear("s1")

        assert await self.mem.get_history("s1") == []
        assert await self.mem.get_traces("s1") == []

    @pytest.mark.asyncio
    async def test_multiple_sessions(self):
        """Different session_ids are isolated from each other."""
        await self.mem.add_message("s1", "user", "Session 1 msg")
        await self.mem.add_message("s2", "user", "Session 2 msg")

        h1 = await self.mem.get_history("s1")
        h2 = await self.mem.get_history("s2")

        assert len(h1) == 1
        assert len(h2) == 1
        assert h1[0]["content"] == "Session 1 msg"
        assert h2[0]["content"] == "Session 2 msg"

    @pytest.mark.asyncio
    async def test_list_sessions(self):
        """list_sessions returns all session IDs with history."""
        await self.mem.add_message("a", "user", "hi")
        await self.mem.add_message("b", "user", "hi")
        assert set(self.mem.list_sessions()) == {"a", "b"}

    @pytest.mark.asyncio
    async def test_exists(self):
        """exists returns True only for sessions with history."""
        assert not self.mem.exists("s1")
        await self.mem.add_message("s1", "user", "hi")
        assert self.mem.exists("s1")

    @pytest.mark.asyncio
    async def test_truncation(self):
        """History is truncated to MAX_SESSION_TURNS * 2 messages."""
        with patch("agent.memory.session.get_settings") as mock_settings:
            mock_settings.return_value.MAX_SESSION_TURNS = 2
            mock_settings.return_value.SESSION_TTL_SECONDS = 7200
            mock_settings.return_value.SESSION_MAX_COUNT = 1000
            mock_settings.return_value.TRACE_MAX_PER_SESSION = 200
            mem = SessionMemory()

            # Add 3 full turns (6 messages) — should keep only last 4
            for i in range(3):
                await mem.add_message("s1", "user", f"q{i}")
                await mem.add_message("s1", "assistant", f"a{i}")

            history = await mem.get_history("s1")
            assert len(history) == 4
            assert history[0]["content"] == "q1"
            assert history[-1]["content"] == "a2"

    @pytest.mark.asyncio
    async def test_get_history_returns_copy(self):
        """get_history returns a copy, not a reference to internal data."""
        await self.mem.add_message("s1", "user", "original")
        history = await self.mem.get_history("s1")
        history.append({"role": "user", "content": "injected"})
        assert len(await self.mem.get_history("s1")) == 1
