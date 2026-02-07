# SSE protocol unit tests – verifies format() returns dict, not str
# Zero LLM token cost: no API calls involved
from __future__ import annotations

import json

from agent.models import SSEEventType, SSEMessage


class TestSSEMessageFormat:
    """SSEMessage.format() must return dict for sse-starlette."""

    def test_returns_dict_not_str(self):
        """format() must return dict — prevents double-wrapping by EventSourceResponse."""
        msg = SSEMessage(event=SSEEventType.TEXT, data={"content": "hello"})
        result = msg.format()
        assert isinstance(result, dict), f"Expected dict, got {type(result).__name__}"
        assert "event" in result
        assert "data" in result

    def test_all_event_types_produce_valid_format(self):
        """Every SSEEventType produces a dict with parseable JSON data."""
        for evt in SSEEventType:
            msg = SSEMessage(event=evt, data={"test": True})
            result = msg.format()
            assert result["event"] == evt.value, f"Event mismatch for {evt}"
            parsed = json.loads(result["data"])
            assert parsed["test"] is True

    def test_unicode_preserved(self):
        """Chinese characters must not be escaped."""
        msg = SSEMessage(event=SSEEventType.TEXT, data={"content": "你好世界"})
        result = msg.format()
        assert "你好世界" in result["data"]
        assert "\\u" not in result["data"]

    def test_dict_has_exactly_two_keys(self):
        """format() dict should have exactly 'event' and 'data' keys."""
        msg = SSEMessage(event=SSEEventType.DONE, data={"session_id": "abc"})
        result = msg.format()
        assert set(result.keys()) == {"event", "data"}
