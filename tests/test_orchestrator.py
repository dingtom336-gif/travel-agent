# Orchestrator component tests – planner, router, state_extractor, context
from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from agent.models import AgentName, AgentTask, SessionState


# ───────────────────────────────────────────────
# Planner
# ───────────────────────────────────────────────

class TestPlanner:
  """Tests for orchestrator.planner.decompose_tasks and helpers."""

  @pytest.mark.asyncio
  async def test_decompose_returns_agent_tasks(self, mock_llm):
    """decompose_tasks returns a list of AgentTask objects."""
    from agent.orchestrator.planner import decompose_tasks

    mock_llm.return_value = json.dumps([
      {"agent": "transport", "goal": "搜索航班", "params": {"departure": "北京"}, "depends_on": []},
      {"agent": "hotel", "goal": "搜索酒店", "params": {"city": "东京"}, "depends_on": []},
    ])

    tasks = await decompose_tasks("帮我规划去东京的旅行")

    assert len(tasks) == 2
    assert all(isinstance(t, AgentTask) for t in tasks)
    assert tasks[0].agent == AgentName.TRANSPORT
    assert tasks[1].agent == AgentName.HOTEL
    assert tasks[0].goal == "搜索航班"

  @pytest.mark.asyncio
  async def test_decompose_falls_back_to_mock_plan_when_llm_returns_none(self, mock_llm):
    """decompose_tasks uses MOCK_PLAN when LLM returns None."""
    from agent.orchestrator.planner import decompose_tasks, MOCK_PLAN

    mock_llm.return_value = None

    tasks = await decompose_tasks("帮我规划旅行")

    assert len(tasks) == len(MOCK_PLAN)

  @pytest.mark.asyncio
  async def test_decompose_falls_back_on_llm_exception(self, mock_llm):
    """decompose_tasks uses MOCK_PLAN when LLM raises."""
    from agent.orchestrator.planner import decompose_tasks, MOCK_PLAN

    mock_llm.side_effect = RuntimeError("API error")

    tasks = await decompose_tasks("帮我规划旅行")

    assert len(tasks) == len(MOCK_PLAN)

  @pytest.mark.asyncio
  async def test_decompose_handles_markdown_fences(self, mock_llm):
    """decompose_tasks strips ```json fences from LLM response."""
    from agent.orchestrator.planner import decompose_tasks

    mock_llm.return_value = '```json\n[{"agent": "weather", "goal": "查天气", "params": {}, "depends_on": []}]\n```'

    tasks = await decompose_tasks("东京天气怎么样")

    assert len(tasks) == 1
    assert tasks[0].agent == AgentName.WEATHER

  @pytest.mark.asyncio
  async def test_decompose_skips_invalid_agents(self, mock_llm):
    """decompose_tasks skips tasks with unrecognized agent names."""
    from agent.orchestrator.planner import decompose_tasks

    mock_llm.return_value = json.dumps([
      {"agent": "transport", "goal": "搜索航班", "params": {}, "depends_on": []},
      {"agent": "invalid_agent", "goal": "做不了", "params": {}, "depends_on": []},
    ])

    tasks = await decompose_tasks("帮我规划旅行")

    assert len(tasks) == 1
    assert tasks[0].agent == AgentName.TRANSPORT

  @pytest.mark.asyncio
  async def test_decompose_returns_empty_for_greeting(self, mock_llm):
    """decompose_tasks returns [] when LLM returns empty array."""
    from agent.orchestrator.planner import decompose_tasks

    mock_llm.return_value = "[]"

    tasks = await decompose_tasks("你好")

    assert tasks == []

  @pytest.mark.asyncio
  async def test_decompose_with_state_context(self, mock_llm):
    """decompose_tasks passes state context to LLM prompt."""
    from agent.orchestrator.planner import decompose_tasks

    mock_llm.return_value = json.dumps([
      {"agent": "poi", "goal": "推荐景点", "params": {}, "depends_on": []},
    ])

    tasks = await decompose_tasks(
      "推荐一些景点",
      state_context="destination: Tokyo",
    )

    assert len(tasks) == 1
    # Verify the LLM was called with state context in the prompt
    call_args = mock_llm.call_args
    user_content = call_args[1]["messages"][0]["content"]
    assert "Tokyo" in user_content

  @pytest.mark.asyncio
  async def test_decompose_with_conversation_history(self, mock_llm):
    """decompose_tasks includes conversation history in prompt."""
    from agent.orchestrator.planner import decompose_tasks

    mock_llm.return_value = json.dumps([
      {"agent": "transport", "goal": "搜索航班", "params": {}, "depends_on": []},
    ])

    history = [
      {"role": "user", "content": "我想去东京"},
      {"role": "assistant", "content": "好的，您打算什么时候去？"},
    ]

    tasks = await decompose_tasks("下周一出发", conversation_history=history)

    call_args = mock_llm.call_args
    user_content = call_args[1]["messages"][0]["content"]
    assert "东京" in user_content

  @pytest.mark.asyncio
  async def test_decompose_with_reuse_previous(self, mock_llm):
    """decompose_tasks parses reuse_previous field."""
    from agent.orchestrator.planner import decompose_tasks

    mock_llm.return_value = json.dumps([
      {"agent": "transport", "goal": "搜索航班", "params": {}, "depends_on": [], "reuse_previous": True},
      {"agent": "hotel", "goal": "搜索酒店", "params": {}, "depends_on": []},
    ])

    tasks = await decompose_tasks("改成住五星级酒店")

    assert tasks[0].reuse_previous is True
    assert tasks[1].reuse_previous is False

  def test_parse_tasks_handles_depends_on(self):
    """_parse_tasks preserves depends_on field."""
    from agent.orchestrator.planner import _parse_tasks

    raw = [
      {"agent": "transport", "goal": "查交通", "params": {}, "depends_on": []},
      {"agent": "itinerary", "goal": "编排行程", "params": {}, "depends_on": ["transport", "poi"]},
    ]

    tasks = _parse_tasks(raw)

    assert tasks[1].depends_on == ["transport", "poi"]


# ───────────────────────────────────────────────
# Router
# ───────────────────────────────────────────────

class TestRouter:
  """Tests for orchestrator.router.classify_complexity."""

  @pytest.mark.asyncio
  async def test_classify_simple_via_llm(self, mock_llm):
    """classify_complexity returns 'simple' when LLM says so."""
    from agent.orchestrator.router import classify_complexity

    mock_llm.return_value = "simple"

    result = await classify_complexity("你好")

    assert result == "simple"

  @pytest.mark.asyncio
  async def test_classify_complex_via_llm(self, mock_llm):
    """classify_complexity returns 'complex' when LLM says so."""
    from agent.orchestrator.router import classify_complexity

    mock_llm.return_value = "complex"

    result = await classify_complexity("帮我规划去东京的5天旅行")

    assert result == "complex"

  @pytest.mark.asyncio
  async def test_classify_defaults_to_complex_on_unclear(self, mock_llm):
    """classify_complexity defaults to 'complex' on unexpected LLM output."""
    from agent.orchestrator.router import classify_complexity

    mock_llm.return_value = "maybe_complex"

    result = await classify_complexity("不知道该怎么分类")

    assert result == "complex"

  @pytest.mark.asyncio
  async def test_classify_falls_back_to_heuristic_on_none(self, mock_llm):
    """classify_complexity uses heuristic when LLM returns None."""
    from agent.orchestrator.router import classify_complexity

    mock_llm.return_value = None

    result = await classify_complexity("你好")

    assert result == "simple"

  @pytest.mark.asyncio
  async def test_classify_falls_back_to_heuristic_on_exception(self, mock_llm):
    """classify_complexity uses heuristic when LLM raises."""
    from agent.orchestrator.router import classify_complexity

    mock_llm.side_effect = RuntimeError("API down")

    # Use a message long enough (>=10 chars) so keyword check is triggered
    result = await classify_complexity("帮我规划一下去东京的旅行方案")

    assert result == "complex"

  @pytest.mark.asyncio
  async def test_classify_includes_history_in_prompt(self, mock_llm):
    """classify_complexity includes conversation history in prompt."""
    from agent.orchestrator.router import classify_complexity

    mock_llm.return_value = "complex"

    history = [
      {"role": "user", "content": "我想去日本"},
      {"role": "assistant", "content": "好的，几天？"},
    ]

    await classify_complexity("5天", conversation_history=history)

    call_args = mock_llm.call_args
    user_content = call_args[1]["messages"][0]["content"]
    assert "日本" in user_content


class TestHeuristicClassify:
  """Tests for router._heuristic_classify."""

  def test_greeting_is_simple(self):
    from agent.orchestrator.router import _heuristic_classify
    assert _heuristic_classify("你好") == "simple"
    assert _heuristic_classify("hi") == "simple"
    assert _heuristic_classify("thanks") == "simple"

  def test_travel_keywords_are_complex(self):
    from agent.orchestrator.router import _heuristic_classify
    assert _heuristic_classify("帮我规划去东京的旅行") == "complex"
    # Short messages (<10 chars) without context default to simple
    # even with keywords, so test with longer messages
    assert _heuristic_classify("帮我搜索一下机票信息") == "complex"
    assert _heuristic_classify("帮我推荐一些好的酒店") == "complex"

  def test_short_without_context_is_simple(self):
    from agent.orchestrator.router import _heuristic_classify
    assert _heuristic_classify("嗯嗯") == "simple"

  def test_short_with_travel_context_is_complex(self):
    from agent.orchestrator.router import _heuristic_classify
    assert _heuristic_classify("5天", has_travel_context=True) == "complex"

  def test_short_greeting_with_context_is_simple(self):
    from agent.orchestrator.router import _heuristic_classify
    assert _heuristic_classify("谢谢", has_travel_context=True) == "simple"


# ───────────────────────────────────────────────
# State Extractor
# ───────────────────────────────────────────────

class TestStateExtractor:
  """Tests for orchestrator.state_extractor."""

  @pytest.mark.asyncio
  async def test_extract_state_updates_pool(self, mock_llm):
    """extract_state updates state_pool from LLM JSON response."""
    from agent.orchestrator.state_extractor import extract_state

    mock_llm.return_value = json.dumps({
      "destination": "东京",
      "duration_days": 5,
      "travelers": null_safe(None),
    })

    with patch("agent.orchestrator.state_extractor.state_pool") as mock_pool:
      mock_pool.update_from_dict = AsyncMock()
      await extract_state("s1", "我想去东京玩5天")

      mock_pool.update_from_dict.assert_called_once()
      call_args = mock_pool.update_from_dict.call_args[0]
      assert call_args[0] == "s1"
      assert call_args[1]["destination"] == "东京"
      assert call_args[1]["duration_days"] == 5
      # null values should be filtered out
      assert "travelers" not in call_args[1]

  @pytest.mark.asyncio
  async def test_extract_state_falls_back_to_heuristic(self, mock_llm):
    """extract_state uses heuristic when LLM returns None."""
    from agent.orchestrator.state_extractor import extract_state

    mock_llm.return_value = None

    with patch("agent.orchestrator.state_extractor.state_pool") as mock_pool:
      mock_pool.update_from_dict = AsyncMock()
      await extract_state("s1", "我想去日本玩5天")

      mock_pool.update_from_dict.assert_called_once()
      data = mock_pool.update_from_dict.call_args[0][1]
      assert data["destination"] == "日本"
      assert data["duration_days"] == 5

  @pytest.mark.asyncio
  async def test_extract_state_handles_llm_exception(self, mock_llm):
    """extract_state falls back to heuristic on LLM error."""
    from agent.orchestrator.state_extractor import extract_state

    mock_llm.side_effect = RuntimeError("API down")

    with patch("agent.orchestrator.state_extractor.state_pool") as mock_pool:
      mock_pool.update_from_dict = AsyncMock()
      # Should not raise
      await extract_state("s1", "我想去东京")

  @pytest.mark.asyncio
  async def test_extract_state_strips_markdown_fences(self, mock_llm):
    """extract_state strips ```json fences from LLM response."""
    from agent.orchestrator.state_extractor import extract_state

    mock_llm.return_value = '```json\n{"destination": "大阪"}\n```'

    with patch("agent.orchestrator.state_extractor.state_pool") as mock_pool:
      mock_pool.update_from_dict = AsyncMock()
      await extract_state("s1", "改去大阪")

      data = mock_pool.update_from_dict.call_args[0][1]
      assert data["destination"] == "大阪"

  @pytest.mark.asyncio
  async def test_extract_state_includes_existing_state_in_prompt(self, mock_llm):
    """extract_state passes existing state to LLM for context."""
    from agent.orchestrator.state_extractor import extract_state

    mock_llm.return_value = '{"budget": "10000元"}'

    existing = SessionState(destination="东京", duration_days=5)

    with patch("agent.orchestrator.state_extractor.state_pool") as mock_pool:
      mock_pool.update_from_dict = AsyncMock()
      await extract_state("s1", "预算一万", existing_state=existing)

    call_args = mock_llm.call_args
    user_content = call_args[1]["messages"][0]["content"]
    assert "东京" in user_content
    assert "duration_days: 5" in user_content


class TestHeuristicExtract:
  """Tests for state_extractor.heuristic_extract."""

  @pytest.mark.asyncio
  async def test_extracts_destination(self):
    from agent.orchestrator.state_extractor import heuristic_extract

    with patch("agent.orchestrator.state_extractor.state_pool") as mock_pool:
      mock_pool.update_from_dict = AsyncMock()
      await heuristic_extract("s1", "我想去日本")

      data = mock_pool.update_from_dict.call_args[0][1]
      assert data["destination"] == "日本"

  @pytest.mark.asyncio
  async def test_extracts_origin(self):
    from agent.orchestrator.state_extractor import heuristic_extract

    with patch("agent.orchestrator.state_extractor.state_pool") as mock_pool:
      mock_pool.update_from_dict = AsyncMock()
      await heuristic_extract("s1", "从上海出发")

      data = mock_pool.update_from_dict.call_args[0][1]
      assert data["origin"] == "上海"

  @pytest.mark.asyncio
  async def test_extracts_duration(self):
    from agent.orchestrator.state_extractor import heuristic_extract

    with patch("agent.orchestrator.state_extractor.state_pool") as mock_pool:
      mock_pool.update_from_dict = AsyncMock()
      await heuristic_extract("s1", "玩7天")

      data = mock_pool.update_from_dict.call_args[0][1]
      assert data["duration_days"] == 7

  @pytest.mark.asyncio
  async def test_extracts_budget(self):
    from agent.orchestrator.state_extractor import heuristic_extract

    with patch("agent.orchestrator.state_extractor.state_pool") as mock_pool:
      mock_pool.update_from_dict = AsyncMock()
      await heuristic_extract("s1", "预算2万")

      data = mock_pool.update_from_dict.call_args[0][1]
      assert data["budget"] == "20000元"

  @pytest.mark.asyncio
  async def test_does_not_overwrite_destination_without_change_intent(self):
    from agent.orchestrator.state_extractor import heuristic_extract

    existing = SessionState(destination="东京")

    with patch("agent.orchestrator.state_extractor.state_pool") as mock_pool:
      mock_pool.update_from_dict = AsyncMock()
      # Mentions a city but no change intent
      await heuristic_extract("s1", "北京有什么好玩的", existing_state=existing)

      if mock_pool.update_from_dict.called:
        data = mock_pool.update_from_dict.call_args[0][1]
        assert data.get("destination") != "北京"

  @pytest.mark.asyncio
  async def test_origin_not_treated_as_destination(self):
    from agent.orchestrator.state_extractor import heuristic_extract

    with patch("agent.orchestrator.state_extractor.state_pool") as mock_pool:
      mock_pool.update_from_dict = AsyncMock()
      await heuristic_extract("s1", "从上海去东京")

      data = mock_pool.update_from_dict.call_args[0][1]
      assert data["origin"] == "上海"
      assert data["destination"] == "东京"


class TestGetLastAssistantMessage:
  """Tests for _get_last_assistant_message helper."""

  def test_returns_last_assistant(self):
    from agent.orchestrator.state_extractor import _get_last_assistant_message

    history = [
      {"role": "user", "content": "hi"},
      {"role": "assistant", "content": "first reply"},
      {"role": "user", "content": "another question"},
      {"role": "assistant", "content": "last reply"},
    ]
    assert _get_last_assistant_message(history) == "last reply"

  def test_returns_empty_when_no_assistant(self):
    from agent.orchestrator.state_extractor import _get_last_assistant_message

    history = [{"role": "user", "content": "hi"}]
    assert _get_last_assistant_message(history) == ""


# ───────────────────────────────────────────────
# Context Builder
# ───────────────────────────────────────────────

class TestContextBuilder:
  """Tests for orchestrator.context module."""

  @pytest.mark.asyncio
  async def test_build_context_empty_history(self, mock_llm):
    """build_context_with_summary returns '' for empty history."""
    from agent.orchestrator.context import build_context_with_summary

    result = await build_context_with_summary([])

    assert result == ""

  @pytest.mark.asyncio
  async def test_build_context_short_history(self, mock_llm):
    """build_context_with_summary keeps short history verbatim."""
    from agent.orchestrator.context import build_context_with_summary

    history = [
      {"role": "user", "content": "hi"},
      {"role": "assistant", "content": "hello"},
    ]

    result = await build_context_with_summary(history)

    assert "user: hi" in result
    assert "assistant: hello" in result

  @pytest.mark.asyncio
  async def test_build_context_long_history_summarizes(self, mock_llm):
    """build_context_with_summary summarizes older messages."""
    from agent.orchestrator.context import build_context_with_summary

    history = [
      {"role": "user", "content": "message 1"},
      {"role": "assistant", "content": "reply 1"},
      {"role": "user", "content": "message 2"},
      {"role": "assistant", "content": "reply 2"},
      {"role": "user", "content": "message 3"},
      {"role": "assistant", "content": "reply 3"},
    ]

    result = await build_context_with_summary(history)

    assert "[Earlier conversation summary]" in result
    assert "[Recent messages]" in result
    # Recent messages should contain the last 4
    assert "message 2" in result or "reply 2" in result
    assert "message 3" in result
    assert "reply 3" in result

  @pytest.mark.asyncio
  async def test_summarize_history_fallback_on_error(self, mock_llm):
    """summarize_history falls back to truncation on LLM error."""
    from agent.orchestrator.context import summarize_history

    mock_llm.side_effect = RuntimeError("API error")

    messages = [
      {"role": "user", "content": "old message 1"},
      {"role": "assistant", "content": "old reply 1"},
    ]

    result = await summarize_history(messages)

    assert "old message 1" in result or "old reply 1" in result

  @pytest.mark.asyncio
  async def test_summarize_history_fallback_on_none(self, mock_llm):
    """summarize_history falls back to truncation when LLM returns None."""
    from agent.orchestrator.context import summarize_history

    mock_llm.return_value = None

    messages = [
      {"role": "user", "content": "question about Tokyo"},
    ]

    result = await summarize_history(messages)

    assert "question about Tokyo" in result


class TestBuildMessages:
  """Tests for context.build_messages."""

  def test_basic_conversion(self):
    from agent.orchestrator.context import build_messages

    history = [
      {"role": "user", "content": "hello"},
      {"role": "assistant", "content": "hi"},
    ]

    messages = build_messages(history)

    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"

  def test_ensures_starts_with_user(self):
    from agent.orchestrator.context import build_messages

    history = [
      {"role": "assistant", "content": "stray reply"},
      {"role": "user", "content": "hello"},
      {"role": "assistant", "content": "hi"},
    ]

    messages = build_messages(history)

    assert messages[0]["role"] == "user"

  def test_empty_history_returns_default(self):
    from agent.orchestrator.context import build_messages

    messages = build_messages([])

    assert len(messages) == 1
    assert messages[0]["role"] == "user"

  def test_truncates_to_20_messages(self):
    from agent.orchestrator.context import build_messages

    # Build 30 messages
    history = []
    for i in range(15):
      history.append({"role": "user", "content": f"msg {i}"})
      history.append({"role": "assistant", "content": f"reply {i}"})

    messages = build_messages(history)

    assert len(messages) <= 20

  def test_filters_non_user_assistant_roles(self):
    from agent.orchestrator.context import build_messages

    history = [
      {"role": "system", "content": "system prompt"},
      {"role": "user", "content": "hello"},
      {"role": "assistant", "content": "hi"},
    ]

    messages = build_messages(history)

    assert all(m["role"] in ("user", "assistant") for m in messages)


# Helper to produce null in JSON without using None directly in json.dumps
def null_safe(val: Any) -> Any:
  return val
