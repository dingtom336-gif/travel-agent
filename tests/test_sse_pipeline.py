# SSE pipeline integration tests – real HTTP → EventSourceResponse → raw bytes
# Zero LLM token cost: llm_chat is mocked in conftest
from __future__ import annotations

import json
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


# --- Unit tests for data flow completeness (no HTTP, no event loop issues) ---

def test_agent_result_includes_data_field():
    """SSEMessage for agent_result must include 'data' field with structured data."""
    from agent.models import SSEEventType, SSEMessage

    msg = SSEMessage(
        event=SSEEventType.AGENT_RESULT,
        data={
            "agent": "transport",
            "status": "success",
            "summary": "Found 3 flights",
            "data": {"response": "text", "tool_data": {"flights": {"results": []}}},
        },
    ).format()

    assert isinstance(msg, dict), "SSEMessage.format() should return dict"
    payload = json.loads(msg["data"]) if isinstance(msg["data"], str) else msg["data"]
    assert "data" in payload, (
        "agent_result SSE event is missing 'data' field – "
        "structured tool data would be dropped!"
    )
    assert "agent" in payload
    assert "status" in payload
    assert "summary" in payload


def test_synthesize_uses_tool_data():
    """Synthesis helper should include truncated tool_data, not just summary."""
    from agent.orchestrator.ui_mapper import truncate_tool_data_for_synthesis

    result_data_with_tools = {
        "response": "Found 3 flights",
        "tool_data": {
            "flights": {
                "results": [
                    {"airline": "ANA", "price": 3500, "departure": "Beijing"},
                ]
            }
        },
    }

    summary = truncate_tool_data_for_synthesis(result_data_with_tools)
    assert summary, "truncate_tool_data_for_synthesis returned empty for valid tool_data"
    assert "ANA" in summary or "flights" in summary, (
        f"Synthesis summary does not contain tool data info: {summary}"
    )

    # Empty tool_data should return empty string
    empty_summary = truncate_tool_data_for_synthesis({"response": "ok"})
    assert empty_summary == "", (
        f"Expected empty string for no tool_data, got: {empty_summary}"
    )


def test_ui_mapper_extract_components():
    """ui_mapper should produce correct ui_component events for known agents."""
    from agent.orchestrator.ui_mapper import extract_ui_components

    # Transport agent with flight data
    result_data = {
        "tool_data": {
            "transit": {
                "results": [
                    {"airline": "ANA", "price": 3500, "departure": "Beijing", "arrival": "Tokyo"}
                ]
            }
        }
    }
    events = list(extract_ui_components("transport", result_data))
    for ev in events:
        assert isinstance(ev, dict), f"ui_component event should be dict, got {type(ev)}"
        assert "event" in ev, "ui_component event missing 'event' key"
        assert "data" in ev, "ui_component event missing 'data' key"

    # Unknown agent should produce no events
    events = list(extract_ui_components("unknown_agent", result_data))
    assert len(events) == 0, "Unknown agent should produce no ui_component events"

    # Empty tool_data should produce no events
    events = list(extract_ui_components("transport", {}))
    assert len(events) == 0, "Empty data should produce no ui_component events"


def test_ui_component_event_format():
    """ui_component SSE events must have type, data, status fields."""
    from agent.orchestrator.ui_mapper import extract_ui_components

    result_data = {
        "tool_data": {
            "hotels": {
                "results": [
                    {"name": "Park Hyatt", "stars": 5, "location": "Shinjuku", "price_per_night": 2800}
                ]
            }
        }
    }
    events = list(extract_ui_components("hotel", result_data))

    for ev in events:
        # Parse the data payload
        payload = json.loads(ev["data"]) if isinstance(ev["data"], str) else ev["data"]
        assert "type" in payload, "ui_component missing 'type' field"
        assert "data" in payload, "ui_component missing 'data' field"
        assert "status" in payload, "ui_component missing 'status' field"
        assert payload["type"] == "hotel_card", f"Expected hotel_card, got {payload['type']}"
