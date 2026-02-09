# Agent layer unit tests – BaseAgent template + all subclass agents
from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.models import AgentName, AgentResult, AgentTask, TaskStatus
from agent.teams.base import BaseAgent
from agent.teams.transport import TransportAgent
from agent.teams.hotel import HotelAgent
from agent.teams.poi import POIAgent
from agent.teams.budget import BudgetAgent
from agent.teams.weather import WeatherAgent
from agent.teams.itinerary import ItineraryAgent
from agent.teams.knowledge import KnowledgeAgent
from agent.teams.customer_service import CustomerServiceAgent


# ───────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────

def _make_task(
  agent: AgentName,
  goal: str = "test goal",
  params: dict | None = None,
) -> AgentTask:
  return AgentTask(
    task_id="t1",
    agent=agent,
    goal=goal,
    params=params or {},
  )


def _default_context(**extra: Any) -> dict[str, Any]:
  return {"state_context": "destination: Tokyo", **extra}


def _patch_env_sim():
  """Patch the env simulator so call_tool skips fault injection."""
  mock_sim = MagicMock()
  mock_sim.is_fault_active.return_value = False
  return patch(
    "agent.simulator.env_simulator.get_env_simulator",
    return_value=mock_sim,
  )


# ───────────────────────────────────────────────
# BaseAgent template method tests
# ───────────────────────────────────────────────

class TestBaseAgentTemplate:
  """Tests for the BaseAgent.execute() template-method pipeline."""

  @pytest.mark.asyncio
  async def test_execute_happy_path(self, mock_llm):
    """execute() calls _run_tools -> _build_prompt -> _call_claude -> _post_process."""
    agent = TransportAgent()
    task = _make_task(AgentName.TRANSPORT, "Find flights to Tokyo")
    ctx = _default_context()

    result = await agent.execute(task, ctx)

    assert isinstance(result, AgentResult)
    assert result.status == TaskStatus.SUCCESS
    assert result.task_id == "t1"
    assert result.agent == AgentName.TRANSPORT
    assert "Transport recommendations generated" in result.summary
    assert result.duration_ms >= 0

  @pytest.mark.asyncio
  async def test_execute_returns_failure_on_exception(self, mock_llm):
    """execute() catches exceptions and returns FAILED result."""
    agent = TransportAgent()
    task = _make_task(AgentName.TRANSPORT, "Fail test")
    ctx = _default_context()

    # Make _run_tools raise
    async def boom(*a, **kw):
      raise RuntimeError("boom")

    agent._run_tools = boom  # type: ignore[assignment]

    result = await agent.execute(task, ctx)

    assert result.status == TaskStatus.FAILED
    assert "boom" in (result.error or "")
    assert "Transport search failed" in result.summary

  @pytest.mark.asyncio
  async def test_build_prompt_includes_task_and_context(self, mock_llm):
    """_build_prompt includes task goal, params, state context, and tool data."""
    agent = TransportAgent()
    task = _make_task(
      AgentName.TRANSPORT,
      "Find flights",
      params={"departure": "Beijing", "arrival": "Tokyo"},
    )
    ctx = _default_context()
    tool_data = {"flights": {"success": True, "results": []}}

    prompt = agent._build_prompt(task, ctx, tool_data)

    assert "Find flights" in prompt
    assert "Beijing" in prompt
    assert "Tokyo" in prompt
    assert "Tool Results" in prompt
    assert "flights" in prompt

  @pytest.mark.asyncio
  async def test_build_prompt_empty_tool_data(self, mock_llm):
    """_build_prompt omits tool section when tool_data is empty."""
    agent = TransportAgent()
    task = _make_task(AgentName.TRANSPORT, "Find flights")
    ctx = _default_context()

    prompt = agent._build_prompt(task, ctx, {})

    assert "Find flights" in prompt
    assert "Tool Results" not in prompt

  @pytest.mark.asyncio
  async def test_make_result_computes_duration(self):
    """_make_result calculates duration_ms from start_time."""
    import time
    agent = TransportAgent()
    task = _make_task(AgentName.TRANSPORT)
    start = time.time() - 0.5  # 500ms ago

    result = agent._make_result(task, summary="ok", start_time=start)

    assert result.duration_ms >= 400

  @pytest.mark.asyncio
  async def test_mock_response_on_llm_failure(self):
    """_call_claude returns mock response when LLM raises."""
    agent = TransportAgent()

    with patch("agent.teams.base.llm_chat", side_effect=Exception("API down")):
      with patch("agent.teams.base.get_settings") as gs:
        gs.return_value.LLM_AGENT_TOKENS = 1024
        resp = await agent._call_claude("sys", "user msg")

    assert "[MOCK" in resp
    assert "API down" in resp

  @pytest.mark.asyncio
  async def test_mock_response_on_llm_none(self):
    """_call_claude returns mock response when LLM returns None."""
    agent = TransportAgent()

    with patch("agent.teams.base.llm_chat", new_callable=AsyncMock, return_value=None):
      with patch("agent.teams.base.get_settings") as gs:
        gs.return_value.LLM_AGENT_TOKENS = 1024
        resp = await agent._call_claude("sys", "user msg")

    assert "[MOCK" in resp

  def test_apply_price_modifier_flat(self):
    """_apply_price_modifier scales price fields."""
    data = {"price": 100, "name": "Flight A"}
    result = BaseAgent._apply_price_modifier(data, 1.5)
    assert result["price"] == 150
    assert result["name"] == "Flight A"

  def test_apply_price_modifier_nested(self):
    """_apply_price_modifier scales nested results list."""
    data = {
      "results": [
        {"price_per_night": 200, "name": "Hotel A"},
        {"ticket_price": 50},
      ],
    }
    result = BaseAgent._apply_price_modifier(data, 2.0)
    assert result["results"][0]["price_per_night"] == 400
    assert result["results"][1]["ticket_price"] == 100


# ───────────────────────────────────────────────
# TransportAgent
# ───────────────────────────────────────────────

class TestTransportAgent:
  """Tests for TransportAgent._run_tools."""

  @pytest.mark.asyncio
  async def test_run_tools_calls_optimize_transit(self, mock_llm):
    """_run_tools calls optimize_transit when all params present."""
    agent = TransportAgent()
    task = _make_task(
      AgentName.TRANSPORT,
      "Find transport",
      params={"departure": "Beijing", "arrival": "Tokyo", "date": "2026-03-01"},
    )

    mock_tool = AsyncMock(return_value={"success": True, "routes": []})
    with patch.object(agent, "call_tool", mock_tool):
      data = await agent._run_tools(task, _default_context())

    mock_tool.assert_called_once()
    assert mock_tool.call_args[0][0] == "optimize_transit"
    assert "transit" in data

  @pytest.mark.asyncio
  async def test_run_tools_fallback_on_transit_error(self, mock_llm):
    """_run_tools falls back to search_flights + get_distance when transit fails."""
    agent = TransportAgent()
    task = _make_task(
      AgentName.TRANSPORT,
      "Find transport",
      params={"departure": "Beijing", "arrival": "Tokyo", "date": "2026-03-01"},
    )

    call_count = 0

    async def side_effect(name, **kw):
      nonlocal call_count
      call_count += 1
      if name == "optimize_transit":
        raise RuntimeError("transit down")
      return {"success": True}

    with patch.object(agent, "call_tool", side_effect=side_effect):
      data = await agent._run_tools(task, _default_context())

    # Should have called optimize_transit, then search_flights, then get_distance
    assert call_count == 3
    assert "flights" in data or "distance" in data

  @pytest.mark.asyncio
  async def test_run_tools_empty_when_missing_params(self, mock_llm):
    """_run_tools returns empty dict when departure/arrival/date missing."""
    agent = TransportAgent()
    task = _make_task(AgentName.TRANSPORT, "Find transport", params={})

    with patch.object(agent, "call_tool", new_callable=AsyncMock) as mock_tool:
      data = await agent._run_tools(task, _default_context())

    mock_tool.assert_not_called()
    assert data == {}


# ───────────────────────────────────────────────
# HotelAgent
# ───────────────────────────────────────────────

class TestHotelAgent:
  """Tests for HotelAgent._run_tools."""

  @pytest.mark.asyncio
  async def test_run_tools_calls_search_hotels(self, mock_llm):
    """_run_tools calls search_hotels with correct params."""
    agent = HotelAgent()
    task = _make_task(
      AgentName.HOTEL,
      "Find hotels",
      params={
        "city": "Tokyo",
        "checkin": "2026-03-01",
        "checkout": "2026-03-05",
        "guests": 2,
        "stars_min": 4,
        "price_max": 500,
      },
    )

    mock_tool = AsyncMock(return_value={"success": True, "results": []})
    with patch.object(agent, "call_tool", mock_tool):
      data = await agent._run_tools(task, _default_context())

    mock_tool.assert_called_once_with(
      "search_hotels",
      city="Tokyo",
      checkin="2026-03-01",
      checkout="2026-03-05",
      guests=2,
      stars_min=4,
      price_max=500,
    )
    assert "hotels" in data

  @pytest.mark.asyncio
  async def test_run_tools_empty_without_required_params(self, mock_llm):
    """_run_tools returns empty dict when city/checkin/checkout missing."""
    agent = HotelAgent()
    task = _make_task(AgentName.HOTEL, "Find hotels", params={"city": "Tokyo"})

    with patch.object(agent, "call_tool", new_callable=AsyncMock) as mock_tool:
      data = await agent._run_tools(task, _default_context())

    mock_tool.assert_not_called()
    assert data == {}

  @pytest.mark.asyncio
  async def test_run_tools_swallows_tool_exception(self, mock_llm):
    """_run_tools returns empty dict when search_hotels raises."""
    agent = HotelAgent()
    task = _make_task(
      AgentName.HOTEL,
      "Find hotels",
      params={"city": "Tokyo", "checkin": "2026-03-01", "checkout": "2026-03-05"},
    )

    mock_tool = AsyncMock(side_effect=RuntimeError("API down"))
    with patch.object(agent, "call_tool", mock_tool):
      data = await agent._run_tools(task, _default_context())

    assert data == {}


# ───────────────────────────────────────────────
# POIAgent
# ───────────────────────────────────────────────

class TestPOIAgent:
  """Tests for POIAgent._run_tools and _post_process."""

  @pytest.mark.asyncio
  async def test_run_tools_calls_search_pois(self, mock_llm):
    """_run_tools calls search_pois with city and limit."""
    agent = POIAgent()
    task = _make_task(
      AgentName.POI,
      "Find attractions",
      params={"city": "Tokyo", "category": "scenic", "limit": 5},
    )

    mock_tool = AsyncMock(return_value={"success": True, "results": [{"name": "Senso-ji"}]})
    with patch.object(agent, "call_tool", mock_tool):
      data = await agent._run_tools(task, _default_context())

    mock_tool.assert_called_once_with("search_pois", city="Tokyo", limit=5, category="scenic")
    assert "pois" in data

  def test_post_process_extracts_pois_from_response(self, mock_llm):
    """_post_process extracts POI JSON from LLM response when tools return empty."""
    agent = POIAgent()
    task = _make_task(AgentName.POI, "Find attractions", params={"city": "Tokyo"})

    response_with_json = """Here are some attractions:
```json
[{"name": "Senso-ji", "category": "scenic", "rating": 4.5, "hours": "06:00-17:00", "price": 0, "desc": "Ancient temple"}]
```"""

    result = agent._post_process(task, {}, {"pois": {"results": []}}, response_with_json)

    assert result["tool_data"]["pois"]["success"] is True
    assert result["tool_data"]["pois"]["results"][0]["name"] == "Senso-ji"

  def test_post_process_keeps_existing_pois(self, mock_llm):
    """_post_process does not overwrite when tools already returned POIs."""
    agent = POIAgent()
    task = _make_task(AgentName.POI, "Find attractions", params={"city": "Tokyo"})

    existing_pois = {"results": [{"name": "Real POI"}], "success": True}
    result = agent._post_process(task, {}, {"pois": existing_pois}, "some response")

    assert result["tool_data"]["pois"]["results"][0]["name"] == "Real POI"

  def test_extract_pois_from_response_json_block(self):
    """_extract_pois_from_response parses ```json blocks."""
    response = '```json\n[{"name": "A", "category": "scenic"}]\n```'
    pois = POIAgent._extract_pois_from_response(response)
    assert len(pois) == 1
    assert pois[0]["name"] == "A"

  def test_extract_pois_from_response_inline_json(self):
    """_extract_pois_from_response parses inline JSON arrays."""
    response = 'Some text [{"name": "B"}] more text'
    pois = POIAgent._extract_pois_from_response(response)
    assert len(pois) == 1
    assert pois[0]["name"] == "B"

  def test_extract_pois_from_response_invalid_json(self):
    """_extract_pois_from_response returns [] on invalid JSON."""
    pois = POIAgent._extract_pois_from_response("no json here")
    assert pois == []


# ───────────────────────────────────────────────
# BudgetAgent
# ───────────────────────────────────────────────

class TestBudgetAgent:
  """Tests for BudgetAgent._run_tools."""

  @pytest.mark.asyncio
  async def test_run_tools_calls_allocate_budget(self, mock_llm):
    """_run_tools calls allocate_budget when budget > 0."""
    agent = BudgetAgent()
    task = _make_task(
      AgentName.BUDGET,
      "Budget analysis",
      params={"budget": 10000, "days": 5, "destination": "Tokyo", "travelers": 2},
    )

    mock_tool = AsyncMock(return_value={"success": True})
    with patch.object(agent, "call_tool", mock_tool):
      data = await agent._run_tools(task, _default_context())

    assert mock_tool.call_args_list[0][0][0] == "allocate_budget"
    assert "budget_allocation" in data

  @pytest.mark.asyncio
  async def test_run_tools_calls_currency_converter(self, mock_llm):
    """_run_tools calls convert_currency when currency params given."""
    agent = BudgetAgent()
    task = _make_task(
      AgentName.BUDGET,
      "Budget analysis",
      params={
        "budget": 10000,
        "days": 5,
        "currency_from": "CNY",
        "currency_to": "JPY",
      },
    )

    mock_tool = AsyncMock(return_value={"success": True})
    with patch.object(agent, "call_tool", mock_tool):
      data = await agent._run_tools(task, _default_context())

    tool_names = [c[0][0] for c in mock_tool.call_args_list]
    assert "convert_currency" in tool_names
    assert "currency" in data

  @pytest.mark.asyncio
  async def test_run_tools_parses_chinese_budget_string(self, mock_llm):
    """_run_tools parses '1万' as 10000."""
    agent = BudgetAgent()
    task = _make_task(
      AgentName.BUDGET,
      "Budget analysis",
      params={"budget": "1万", "days": 3},
    )

    mock_tool = AsyncMock(return_value={"success": True})
    with patch.object(agent, "call_tool", mock_tool):
      data = await agent._run_tools(task, _default_context())

    # Should have called allocate_budget because parsed budget > 0
    assert mock_tool.call_count >= 1
    assert "budget_allocation" in data


# ───────────────────────────────────────────────
# WeatherAgent
# ───────────────────────────────────────────────

class TestWeatherAgent:
  """Tests for WeatherAgent._run_tools."""

  @pytest.mark.asyncio
  async def test_run_tools_calls_get_weather_forecast(self, mock_llm):
    """_run_tools calls get_weather_forecast with city and date."""
    agent = WeatherAgent()
    task = _make_task(
      AgentName.WEATHER,
      "Weather forecast",
      params={"city": "Tokyo", "date": "2026-03-01", "days": 3},
    )

    mock_tool = AsyncMock(return_value={"success": True, "forecast": []})
    with patch.object(agent, "call_tool", mock_tool):
      data = await agent._run_tools(task, _default_context())

    mock_tool.assert_called_once_with(
      "get_weather_forecast",
      city="Tokyo",
      start_date="2026-03-01",
      days=3,
    )
    assert "forecast" in data

  @pytest.mark.asyncio
  async def test_run_tools_fallback_to_single_weather(self, mock_llm):
    """_run_tools falls back to get_weather when forecast fails."""
    agent = WeatherAgent()
    task = _make_task(
      AgentName.WEATHER,
      "Weather forecast",
      params={"city": "Tokyo", "date": "2026-03-01"},
    )

    async def side_effect(name, **kw):
      if name == "get_weather_forecast":
        raise RuntimeError("forecast unavailable")
      return {"success": True, "temp": 15}

    with patch.object(agent, "call_tool", side_effect=side_effect):
      data = await agent._run_tools(task, _default_context())

    assert "weather" in data

  @pytest.mark.asyncio
  async def test_run_tools_empty_without_city_and_date(self, mock_llm):
    """_run_tools returns empty dict when city/date missing."""
    agent = WeatherAgent()
    task = _make_task(AgentName.WEATHER, "Weather", params={})

    with patch.object(agent, "call_tool", new_callable=AsyncMock) as mock_tool:
      data = await agent._run_tools(task, _default_context())

    mock_tool.assert_not_called()
    assert data == {}


# ───────────────────────────────────────────────
# ItineraryAgent
# ───────────────────────────────────────────────

class TestItineraryAgent:
  """Tests for ItineraryAgent._run_tools, _build_prompt, and helpers."""

  @pytest.mark.asyncio
  async def test_run_tools_calls_optimize_itinerary(self, mock_llm):
    """_run_tools calls optimize_itinerary when upstream POIs available."""
    agent = ItineraryAgent()
    upstream = {
      "poi": {
        "tool_data": {
          "pois": {
            "results": [
              {"name": "Senso-ji", "lat": 35.7, "lng": 139.8},
              {"name": "Tokyo Tower", "lat": 35.6, "lng": 139.7},
            ],
          },
        },
      },
    }
    task = _make_task(
      AgentName.ITINERARY,
      "Build itinerary",
      params={"destination": "Tokyo", "days": 3},
    )
    ctx = _default_context(upstream_results=upstream)

    mock_tool = AsyncMock(return_value={"success": True, "days": []})
    with patch.object(agent, "call_tool", mock_tool):
      data = await agent._run_tools(task, ctx)

    assert mock_tool.call_count >= 1
    tool_names = [c[0][0] for c in mock_tool.call_args_list]
    assert "optimize_itinerary" in tool_names

  def test_build_prompt_includes_upstream(self, mock_llm):
    """_build_prompt includes upstream agent results."""
    agent = ItineraryAgent()
    task = _make_task(AgentName.ITINERARY, "Build itinerary")
    ctx = _default_context(upstream_results={
      "poi": {"response": "Great attractions found"},
    })

    prompt = agent._build_prompt(task, ctx, {})

    assert "Upstream Agent Results" in prompt
    assert "Great attractions found" in prompt

  def test_extract_pois_from_upstream(self):
    """_extract_pois_from_upstream extracts POIs from upstream results."""
    agent = ItineraryAgent()
    upstream = {
      "poi": {
        "tool_data": {
          "pois": {
            "results": [{"name": "A"}, {"name": "B"}],
          },
        },
      },
    }
    pois = agent._extract_pois_from_upstream(upstream)
    assert len(pois) == 2
    assert pois[0]["name"] == "A"

  def test_extract_waypoints(self):
    """_extract_waypoints returns hotel + POI names + hotel."""
    agent = ItineraryAgent()
    pois = [{"name": "A"}, {"name": "B"}, {"name": "C"}]
    waypoints = agent._extract_waypoints(pois, "Hotel Tokyo")

    assert waypoints[0] == "Hotel Tokyo"
    assert waypoints[-1] == "Hotel Tokyo"
    assert "A" in waypoints
    assert "B" in waypoints


# ───────────────────────────────────────────────
# KnowledgeAgent
# ───────────────────────────────────────────────

class TestKnowledgeAgent:
  """Tests for KnowledgeAgent.execute (custom override)."""

  @pytest.mark.asyncio
  async def test_execute_calls_knowledge_base(self, mock_llm):
    """execute() queries knowledge_base and calls LLM."""
    agent = KnowledgeAgent()
    task = _make_task(
      AgentName.KNOWLEDGE,
      "Tell me about visa for Japan",
      params={"destination": "Japan", "category": "visa"},
    )

    mock_kb = MagicMock()
    mock_kb.get_visa_info.return_value = [
      {"title": "Japan Visa", "content": "30-day visa free"},
    ]
    mock_kb.get_culture_info.return_value = []
    mock_kb.get_food_info.return_value = []
    mock_kb.search.return_value = []
    mock_kb.format_results.return_value = "Japan Visa: 30-day visa free"

    with patch("agent.teams.knowledge.knowledge_base", mock_kb):
      result = await agent.execute(task, _default_context())

    assert result.status == TaskStatus.SUCCESS
    assert result.data["kb_hits"] >= 1
    assert "Japan Visa" in result.data["kb_titles"]
    mock_kb.get_visa_info.assert_called_once()

  @pytest.mark.asyncio
  async def test_execute_handles_exception(self, mock_llm):
    """execute() returns FAILED when knowledge_base raises."""
    agent = KnowledgeAgent()
    task = _make_task(
      AgentName.KNOWLEDGE,
      "Tell me about visa for Japan",
      params={"destination": "Japan"},
    )

    with patch("agent.teams.knowledge.knowledge_base") as mock_kb:
      mock_kb.get_visa_info.side_effect = RuntimeError("KB down")
      result = await agent.execute(task, _default_context())

    assert result.status == TaskStatus.FAILED
    assert "KB down" in (result.error or "")


# ───────────────────────────────────────────────
# CustomerServiceAgent
# ───────────────────────────────────────────────

class TestCustomerServiceAgent:
  """Tests for CustomerServiceAgent (stub agent with no tool overrides)."""

  @pytest.mark.asyncio
  async def test_execute_works_with_default_hooks(self, mock_llm):
    """Stub agent uses default _run_tools and _post_process."""
    agent = CustomerServiceAgent()
    task = _make_task(AgentName.CUSTOMER_SERVICE, "Help me cancel a booking")

    result = await agent.execute(task, _default_context())

    assert result.status == TaskStatus.SUCCESS
    assert "Customer service" in result.summary
    assert "response" in result.data

  @pytest.mark.asyncio
  async def test_name_and_description(self):
    """Verify agent name and description attributes."""
    agent = CustomerServiceAgent()
    assert agent.name == AgentName.CUSTOMER_SERVICE
    assert "support" in agent.description.lower() or "after-sales" in agent.description.lower()


# ───────────────────────────────────────────────
# call_tool with fault injection
# ───────────────────────────────────────────────

class TestCallTool:
  """Tests for BaseAgent.call_tool with fault injection."""

  @pytest.mark.asyncio
  async def test_call_tool_success(self):
    """call_tool delegates to the registered tool function."""
    agent = TransportAgent()
    mock_func = AsyncMock(return_value={"success": True, "price": 500})

    with patch(
      "agent.tools.registry.get_tools_for_agent",
      return_value={"search_flights": mock_func},
    ):
      with _patch_env_sim():
        result = await agent.call_tool("search_flights", departure="BJ")

    assert result["success"] is True
    mock_func.assert_called_once_with(departure="BJ")

  @pytest.mark.asyncio
  async def test_call_tool_unknown_tool_raises(self):
    """call_tool raises ValueError for unregistered tool."""
    agent = TransportAgent()

    with patch(
      "agent.tools.registry.get_tools_for_agent",
      return_value={},
    ):
      with _patch_env_sim():
        with pytest.raises(ValueError, match="not available"):
          await agent.call_tool("nonexistent_tool")

  @pytest.mark.asyncio
  async def test_call_tool_propagates_exception(self):
    """call_tool re-raises exceptions from the tool function."""
    agent = TransportAgent()
    mock_func = AsyncMock(side_effect=ConnectionError("timeout"))

    with patch(
      "agent.tools.registry.get_tools_for_agent",
      return_value={"search_flights": mock_func},
    ):
      with _patch_env_sim():
        with pytest.raises(ConnectionError, match="timeout"):
          await agent.call_tool("search_flights")
