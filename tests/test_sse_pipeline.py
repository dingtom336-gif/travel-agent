# SSE pipeline integration tests – real HTTP → EventSourceResponse → raw bytes
# Zero LLM token cost: llm_chat is mocked in conftest
from __future__ import annotations

import time

import pytest
from httpx import ASGITransport, AsyncClient

from agent.main import app


@pytest.mark.asyncio
async def test_chat_stream_format_and_timing(mock_llm):
    """POST /api/chat/stream: correct SSE format, has done event, completes fast.

    Combined into one test to avoid sse_starlette's AppStatus global state
    leaking between tests (known issue with test clients).
    """
    transport = ASGITransport(app=app)
    start = time.monotonic()
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
            "POST", "/api/chat/stream", json={"message": "hi"},
        ) as resp:
            assert resp.status_code == 200
            raw = await resp.aread()
            text = raw.decode("utf-8")
    elapsed = time.monotonic() - start

    # 1. Must NOT have double-wrapped format
    assert "data: event:" not in text, (
        f"Double-wrapped SSE detected. Raw:\n{text[:500]}"
    )
    assert "data: data:" not in text, (
        f"Double-wrapped data detected. Raw:\n{text[:500]}"
    )

    # 2. Must have proper event types
    assert "event: done" in text, f"Missing done event. Raw:\n{text[:500]}"

    # 3. With mocked LLM, should complete fast
    assert elapsed < 30, f"Stream took {elapsed:.1f}s — expected < 30s with mock LLM"


@pytest.mark.asyncio
async def test_non_streaming_endpoint(mock_llm):
    """POST /api/chat should return a proper JSON response."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/chat", json={"message": "hi"})
        assert resp.status_code == 200
        body = resp.json()
        assert "session_id" in body
        assert "message" in body
        # Message should be readable text, not JSON
        assert not body["message"].startswith("{"), (
            f"Response looks like raw JSON: {body['message'][:100]}"
        )
