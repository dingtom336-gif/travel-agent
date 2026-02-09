# Integration tests – SSE pipeline from API endpoint to event stream
# Mocks Orchestrator internals to verify SSE event format and ordering
from __future__ import annotations

import json
import time
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from agent.main import app
from agent.models import (
  AgentName,
  AgentResult,
  AgentTask,
  SSEEventType,
  SSEMessage,
  SessionState,
  TaskStatus,
)


# ───────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────

def _parse_sse_events(raw_text: str) -> list[dict[str, Any]]:
  """Parse raw SSE text into list of {event, data} dicts."""
  events: list[dict[str, Any]] = []
  current_event = ""
  current_data = ""
  for line in raw_text.split("\n"):
    line = line.rstrip("\r")
    if line.startswith("event: "):
      current_event = line[7:]
    elif line.startswith("data: "):
      current_data = line[6:]
    elif line == "" and current_event:
      try:
        data = json.loads(current_data) if current_data else {}
      except json.JSONDecodeError:
        data = {"raw": current_data}
      events.append({"event": current_event, "data": data})
      current_event = ""
      current_data = ""
  return events


async def _mock_handle_message(
  session_id: str | None = None,
  message: str = "",
) -> AsyncGenerator[dict, None]:
  """Simulate OrchestratorAgent.handle_message yielding proper SSE events."""
  sid = session_id or "test-session-123"

  yield SSEMessage(
    event=SSEEventType.THINKING,
    data={"agent": "orchestrator", "thought": "Analyzing request..."},
  ).format()

  yield SSEMessage(
    event=SSEEventType.AGENT_START,
    data={"agent": "transport", "task": "Search flights"},
  ).format()

  yield SSEMessage(
    event=SSEEventType.AGENT_RESULT,
    data={
      "agent": "transport",
      "status": "success",
      "summary": "Found 3 flights",
      "data": {"response": "Flight results", "tool_data": {}},
    },
  ).format()

  yield SSEMessage(
    event=SSEEventType.TEXT,
    data={"content": "Here is your travel plan."},
  ).format()

  yield SSEMessage(
    event=SSEEventType.DONE,
    data={"session_id": sid},
  ).format()


# ───────────────────────────────────────────────
# SSE Endpoint Integration Tests
# ───────────────────────────────────────────────

class TestSSEEndpoint:
  """Integration tests for /api/chat/stream endpoint."""

  @pytest.mark.asyncio
  async def test_stream_returns_200_and_event_stream(self):
    """POST /api/chat/stream returns 200 with text/event-stream content type."""
    with patch(
      "agent.orchestrator.agent.OrchestratorAgent.handle_message",
      side_effect=_mock_handle_message,
    ):
      transport = ASGITransport(app=app)
      async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
          "POST", "/api/chat/stream", json={"message": "plan a trip to Tokyo"},
        ) as resp:
          assert resp.status_code == 200
          raw = await resp.aread()
          text = raw.decode("utf-8")

      assert len(text) > 0

  @pytest.mark.asyncio
  async def test_stream_no_double_wrapping(self):
    """SSE output must not have double-wrapped format (data: event: ...)."""
    with patch(
      "agent.orchestrator.agent.OrchestratorAgent.handle_message",
      side_effect=_mock_handle_message,
    ):
      transport = ASGITransport(app=app)
      async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
          "POST", "/api/chat/stream", json={"message": "hello"},
        ) as resp:
          raw = await resp.aread()
          text = raw.decode("utf-8")

    assert "data: event:" not in text, f"Double-wrapped SSE: {text[:300]}"
    assert "data: data:" not in text, f"Double-wrapped data: {text[:300]}"

  @pytest.mark.asyncio
  async def test_stream_event_sequence(self):
    """SSE events follow the expected sequence: thinking -> agent_start -> agent_result -> text -> done."""
    with patch(
      "agent.orchestrator.agent.OrchestratorAgent.handle_message",
      side_effect=_mock_handle_message,
    ):
      transport = ASGITransport(app=app)
      async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
          "POST", "/api/chat/stream", json={"message": "plan trip"},
        ) as resp:
          raw = await resp.aread()
          text = raw.decode("utf-8")

    events = _parse_sse_events(text)
    event_types = [e["event"] for e in events]

    # Must start with thinking
    assert event_types[0] == "thinking"
    # Must end with done
    assert event_types[-1] == "done"
    # Must contain agent_start before agent_result
    if "agent_start" in event_types and "agent_result" in event_types:
      assert event_types.index("agent_start") < event_types.index("agent_result")
    # Must contain text before done
    if "text" in event_types:
      assert event_types.index("text") < event_types.index("done")

  @pytest.mark.asyncio
  async def test_stream_done_event_has_session_id(self):
    """The done event must contain a session_id."""
    with patch(
      "agent.orchestrator.agent.OrchestratorAgent.handle_message",
      side_effect=_mock_handle_message,
    ):
      transport = ASGITransport(app=app)
      async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
          "POST", "/api/chat/stream", json={"message": "hello"},
        ) as resp:
          raw = await resp.aread()
          text = raw.decode("utf-8")

    events = _parse_sse_events(text)
    done_events = [e for e in events if e["event"] == "done"]
    assert len(done_events) >= 1
    assert "session_id" in done_events[-1]["data"]

  @pytest.mark.asyncio
  async def test_stream_agent_result_has_structured_data(self):
    """agent_result events must contain agent, status, summary, data fields."""
    with patch(
      "agent.orchestrator.agent.OrchestratorAgent.handle_message",
      side_effect=_mock_handle_message,
    ):
      transport = ASGITransport(app=app)
      async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
          "POST", "/api/chat/stream", json={"message": "plan"},
        ) as resp:
          raw = await resp.aread()
          text = raw.decode("utf-8")

    events = _parse_sse_events(text)
    result_events = [e for e in events if e["event"] == "agent_result"]
    assert len(result_events) >= 1
    for evt in result_events:
      assert "agent" in evt["data"]
      assert "status" in evt["data"]
      assert "summary" in evt["data"]
      assert "data" in evt["data"]


# ───────────────────────────────────────────────
# SSE Event Format Tests
# ───────────────────────────────────────────────

class TestSSEEventFormat:
  """Unit tests for SSE event format consistency."""

  def test_all_event_types_valid(self):
    """All SSEEventType values are in the expected set."""
    expected = {"thinking", "agent_start", "agent_result", "text", "ui_component", "error", "done"}
    actual = {e.value for e in SSEEventType}
    assert actual == expected

  def test_sse_message_format_produces_dict(self):
    """SSEMessage.format() returns a dict for sse-starlette."""
    for evt_type in SSEEventType:
      msg = SSEMessage(event=evt_type, data={"test": True})
      result = msg.format()
      assert isinstance(result, dict)
      assert "event" in result
      assert "data" in result
      assert result["event"] == evt_type.value

  def test_sse_message_data_is_valid_json_string(self):
    """SSEMessage.format() data field is a valid JSON string."""
    msg = SSEMessage(
      event=SSEEventType.TEXT,
      data={"content": "Hello, world!"},
    )
    result = msg.format()
    parsed = json.loads(result["data"])
    assert parsed["content"] == "Hello, world!"

  def test_sse_message_preserves_unicode(self):
    """Chinese characters are not escaped in SSE data."""
    msg = SSEMessage(
      event=SSEEventType.TEXT,
      data={"content": "你好，世界！"},
    )
    result = msg.format()
    assert "你好" in result["data"]
    assert "\\u" not in result["data"]


# ───────────────────────────────────────────────
# Orchestrator handle_message Flow Tests
# ───────────────────────────────────────────────

class TestOrchestratorFlow:
  """Tests for OrchestratorAgent.handle_message flow logic."""

  @pytest.mark.asyncio
  async def test_simple_message_goes_through_synthesizer(self, mock_llm):
    """Simple messages bypass ReAct loop and use synthesizer directly."""
    from agent.orchestrator.agent import OrchestratorAgent

    orch = OrchestratorAgent()

    with patch(
      "agent.orchestrator.agent.classify_complexity",
      new_callable=AsyncMock,
      return_value="simple",
    ), patch(
      "agent.orchestrator.agent.extract_state",
      new_callable=AsyncMock,
    ), patch(
      "agent.orchestrator.agent.session_memory",
    ) as mock_session, patch(
      "agent.orchestrator.agent.state_pool",
    ) as mock_state, patch(
      "agent.orchestrator.agent.profile_manager",
    ) as mock_profile:
      mock_session.add_message = AsyncMock()
      mock_session.get_history = AsyncMock(return_value=[])
      mock_state.get = AsyncMock(return_value=None)
      mock_profile.get_personalization_context.return_value = ""

      # Mock synthesizer handle_simple
      async def fake_simple(*args, **kwargs):
        yield SSEMessage(
          event=SSEEventType.TEXT, data={"content": "Hello!"},
        ).format()
        yield SSEMessage(
          event=SSEEventType.DONE, data={"session_id": "s1"},
        ).format()

      orch._synthesizer.handle_simple = fake_simple

      events = []
      async for chunk in orch.handle_message("s1", "你好"):
        events.append(chunk)

    event_types = [json.loads(e["data"])
                   if isinstance(e.get("data"), str)
                   else e.get("data", {})
                   for e in events]
    # Should have text and done events
    assert any(e["event"] == "text" for e in events)
    assert any(e["event"] == "done" for e in events)

  @pytest.mark.asyncio
  async def test_complex_message_triggers_react_loop(self, mock_llm):
    """Complex messages go through the ReAct loop."""
    from agent.orchestrator.agent import OrchestratorAgent

    orch = OrchestratorAgent()

    with patch(
      "agent.orchestrator.agent.classify_complexity",
      new_callable=AsyncMock,
      return_value="complex",
    ), patch(
      "agent.orchestrator.agent.extract_state",
      new_callable=AsyncMock,
    ), patch(
      "agent.orchestrator.agent.session_memory",
    ) as mock_session, patch(
      "agent.orchestrator.agent.state_pool",
    ) as mock_state, patch(
      "agent.orchestrator.agent.profile_manager",
    ) as mock_profile:
      mock_session.add_message = AsyncMock()
      mock_session.get_history = AsyncMock(return_value=[])
      mock_state.get = AsyncMock(return_value=SessionState(destination="Tokyo"))
      mock_state.to_prompt_context = AsyncMock(return_value="dest: Tokyo")
      mock_profile.get_personalization_context.return_value = ""

      # Mock React engine to yield proper SSE events
      async def fake_react(*args, **kwargs):
        yield SSEMessage(
          event=SSEEventType.THINKING,
          data={"agent": "orchestrator", "thought": "Planning..."},
        ).format()
        yield SSEMessage(
          event=SSEEventType.TEXT,
          data={"content": "Here is your plan."},
        ).format()
        yield SSEMessage(
          event=SSEEventType.DONE,
          data={"session_id": "s1"},
        ).format()

      orch._react_engine.run = fake_react

      events = []
      async for chunk in orch.handle_message("s1", "帮我规划去东京的旅行"):
        events.append(chunk)

    event_types = [e["event"] for e in events]
    assert "thinking" in event_types
    assert "done" in event_types

  @pytest.mark.asyncio
  async def test_handle_message_generates_session_id_if_none(self, mock_llm):
    """handle_message creates session_id when None is passed."""
    from agent.orchestrator.agent import OrchestratorAgent

    orch = OrchestratorAgent()

    with patch(
      "agent.orchestrator.agent.classify_complexity",
      new_callable=AsyncMock,
      return_value="simple",
    ), patch(
      "agent.orchestrator.agent.extract_state",
      new_callable=AsyncMock,
    ), patch(
      "agent.orchestrator.agent.session_memory",
    ) as mock_session, patch(
      "agent.orchestrator.agent.state_pool",
    ) as mock_state, patch(
      "agent.orchestrator.agent.profile_manager",
    ) as mock_profile:
      mock_session.add_message = AsyncMock()
      mock_session.get_history = AsyncMock(return_value=[])
      mock_state.get = AsyncMock(return_value=None)
      mock_profile.get_personalization_context.return_value = ""

      async def fake_simple(*args, **kwargs):
        yield SSEMessage(
          event=SSEEventType.DONE, data={"session_id": "generated"},
        ).format()

      orch._synthesizer.handle_simple = fake_simple

      events = []
      async for chunk in orch.handle_message(None, "hello"):
        events.append(chunk)

    # session_memory.add_message should have been called with a non-None session_id
    call_args = mock_session.add_message.call_args[0]
    assert call_args[0] is not None  # session_id
    assert len(call_args[0]) > 0

  @pytest.mark.asyncio
  async def test_handle_message_catches_exceptions(self, mock_llm):
    """handle_message yields error + done events on uncaught exceptions."""
    from agent.orchestrator.agent import OrchestratorAgent

    orch = OrchestratorAgent()

    with patch(
      "agent.orchestrator.agent.session_memory",
    ) as mock_session:
      mock_session.add_message = AsyncMock(side_effect=RuntimeError("DB crashed"))

      events = []
      async for chunk in orch.handle_message("s1", "hello"):
        events.append(chunk)

    event_types = [e["event"] for e in events]
    assert "error" in event_types
    assert "done" in event_types


# ───────────────────────────────────────────────
# ReactEngine Unit Tests
# ───────────────────────────────────────────────

class TestReactEngine:
  """Tests for ReactEngine task execution and caching."""

  @pytest.mark.asyncio
  async def test_execute_single_task_timeout(self, mock_llm):
    """_execute_single_task returns FAILED on timeout."""
    from agent.orchestrator.react_loop import ReactEngine

    engine = ReactEngine()
    task = AgentTask(
      task_id="t1",
      agent=AgentName.TRANSPORT,
      goal="Search flights",
    )

    # Mock agent that sleeps forever
    async def slow_execute(t, ctx):
      import asyncio
      await asyncio.sleep(100)

    mock_agent = MagicMock()
    mock_agent.execute = slow_execute

    with patch(
      "agent.orchestrator.react_loop.AGENT_REGISTRY",
      {AgentName.TRANSPORT: mock_agent},
    ), patch(
      "agent.orchestrator.react_loop.get_settings",
    ) as gs:
      gs.return_value.LLM_TASK_TIMEOUT = 0.1  # 100ms timeout

      result = await engine._execute_single_task(task, {"state_context": ""})

    assert result.status == TaskStatus.FAILED
    assert "timed out" in result.error

  @pytest.mark.asyncio
  async def test_execute_single_task_missing_agent(self, mock_llm):
    """_execute_single_task returns FAILED for unregistered agent."""
    from agent.orchestrator.react_loop import ReactEngine

    engine = ReactEngine()
    task = AgentTask(
      task_id="t1",
      agent=AgentName.CUSTOMER_SERVICE,
      goal="Help me",
    )

    with patch(
      "agent.orchestrator.react_loop.AGENT_REGISTRY",
      {},
    ):
      result = await engine._execute_single_task(task, {})

    assert result.status == TaskStatus.FAILED
    assert "No agent" in result.error

  def test_find_previous_result(self):
    """_find_previous_result finds matching successful result."""
    from agent.orchestrator.react_loop import ReactEngine

    results = {
      "t1": AgentResult(
        task_id="t1",
        agent=AgentName.TRANSPORT,
        status=TaskStatus.SUCCESS,
        summary="ok",
      ),
      "t2": AgentResult(
        task_id="t2",
        agent=AgentName.HOTEL,
        status=TaskStatus.FAILED,
        summary="fail",
      ),
    }

    found = ReactEngine._find_previous_result(results, AgentName.TRANSPORT)
    assert found is not None
    assert found.task_id == "t1"

    # Failed result should not be found
    found = ReactEngine._find_previous_result(results, AgentName.HOTEL)
    assert found is None

    # Non-existent agent
    found = ReactEngine._find_previous_result(results, AgentName.WEATHER)
    assert found is None


# ───────────────────────────────────────────────
# Health Check Endpoint
# ───────────────────────────────────────────────

class TestHealthEndpoint:
  """Tests for the /health endpoint."""

  @pytest.mark.asyncio
  async def test_health_returns_ok(self):
    """GET /health returns status ok."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
      resp = await client.get("/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "service" in body
    assert "version" in body
