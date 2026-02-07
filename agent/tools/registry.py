# Tool registry - central registration and lookup for all tools
# Provides unified access to MCP tools and Skills
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

# --- MCP Atomic Tools ---
from agent.tools.mcp.flight_search import search_flights
from agent.tools.mcp.hotel_search import search_hotels
from agent.tools.mcp.poi_search import search_pois
from agent.tools.mcp.weather_api import get_weather, get_weather_forecast
from agent.tools.mcp.map_service import get_distance, plan_route
from agent.tools.mcp.currency import convert_currency, list_supported_currencies

# --- Composite Skills ---
from agent.tools.skills.transit_optimizer import optimize_transit
from agent.tools.skills.budget_allocator import allocate_budget
from agent.tools.skills.itinerary_optimizer import optimize_itinerary


# Tool metadata type
ToolMeta = Dict[str, Any]

# Master tool registry: name -> {function, type, description, agent_bindings}
_REGISTRY: Dict[str, ToolMeta] = {}


def _register(
  name: str,
  func: Callable[..., Any],
  tool_type: str,
  description: str,
  agents: List[str],
) -> None:
  """Register a tool in the global registry."""
  _REGISTRY[name] = {
    "name": name,
    "function": func,
    "type": tool_type,       # "mcp" or "skill"
    "description": description,
    "agents": agents,        # which agents can use this tool
  }


# ──────────────────────────────────────
# Register MCP Atomic Tools
# ──────────────────────────────────────

_register(
  name="search_flights",
  func=search_flights,
  tool_type="mcp",
  description="Search flights between two cities with price and schedule info",
  agents=["transport", "itinerary"],
)

_register(
  name="search_hotels",
  func=search_hotels,
  tool_type="mcp",
  description="Search hotels in a city with rating, price, and facilities",
  agents=["hotel", "itinerary"],
)

_register(
  name="search_pois",
  func=search_pois,
  tool_type="mcp",
  description="Search attractions, restaurants, shopping spots in a city",
  agents=["poi", "itinerary"],
)

_register(
  name="get_weather",
  func=get_weather,
  tool_type="mcp",
  description="Get weather forecast for a specific city and date",
  agents=["weather", "itinerary"],
)

_register(
  name="get_weather_forecast",
  func=get_weather_forecast,
  tool_type="mcp",
  description="Get multi-day weather forecast for a city",
  agents=["weather", "itinerary"],
)

_register(
  name="get_distance",
  func=get_distance,
  tool_type="mcp",
  description="Calculate distance and travel time between two locations",
  agents=["transport", "itinerary"],
)

_register(
  name="plan_route",
  func=plan_route,
  tool_type="mcp",
  description="Plan optimal route through multiple waypoints",
  agents=["transport", "itinerary"],
)

_register(
  name="convert_currency",
  func=convert_currency,
  tool_type="mcp",
  description="Convert amount between currencies using exchange rates",
  agents=["budget"],
)

_register(
  name="list_supported_currencies",
  func=list_supported_currencies,
  tool_type="mcp",
  description="List all supported currencies with exchange rates",
  agents=["budget"],
)

# ──────────────────────────────────────
# Register Composite Skills
# ──────────────────────────────────────

_register(
  name="optimize_transit",
  func=optimize_transit,
  tool_type="skill",
  description="Find optimal transport option combining flights, trains, and driving",
  agents=["transport"],
)

_register(
  name="allocate_budget",
  func=allocate_budget,
  tool_type="skill",
  description="Allocate travel budget across categories (transport, hotel, food, etc.)",
  agents=["budget"],
)

_register(
  name="optimize_itinerary",
  func=optimize_itinerary,
  tool_type="skill",
  description="Optimize daily visit order for minimal travel and time-slot matching",
  agents=["itinerary"],
)


# ──────────────────────────────────────
# Public API
# ──────────────────────────────────────

def get_tool(name: str) -> Optional[Callable[..., Any]]:
  """Get a tool function by name.

  Args:
    name: Tool name (e.g. "search_flights")

  Returns:
    The async tool function, or None if not found
  """
  meta = _REGISTRY.get(name)
  return meta["function"] if meta else None


def get_tool_meta(name: str) -> Optional[ToolMeta]:
  """Get full tool metadata by name.

  Args:
    name: Tool name

  Returns:
    Dict with name, function, type, description, agents
  """
  return _REGISTRY.get(name)


def list_tools(tool_type: Optional[str] = None) -> List[Dict[str, str]]:
  """List all registered tools.

  Args:
    tool_type: Filter by type ("mcp" or "skill"). None = all.

  Returns:
    List of dicts with name, type, description
  """
  result = []
  for name, meta in _REGISTRY.items():
    if tool_type and meta["type"] != tool_type:
      continue
    result.append({
      "name": meta["name"],
      "type": meta["type"],
      "description": meta["description"],
      "agents": meta["agents"],
    })
  return result


def get_tools_for_agent(agent_name: str) -> Dict[str, Callable[..., Any]]:
  """Get all tools available for a specific agent.

  Args:
    agent_name: Agent name (e.g. "transport", "hotel")

  Returns:
    Dict mapping tool name -> tool function
  """
  tools = {}
  for name, meta in _REGISTRY.items():
    if agent_name in meta["agents"]:
      tools[name] = meta["function"]
  return tools


def get_tool_descriptions_for_agent(agent_name: str) -> List[Dict[str, str]]:
  """Get tool descriptions for a specific agent (useful for prompts).

  Args:
    agent_name: Agent name

  Returns:
    List of dicts with name and description
  """
  descriptions = []
  for name, meta in _REGISTRY.items():
    if agent_name in meta["agents"]:
      descriptions.append({
        "name": meta["name"],
        "description": meta["description"],
        "type": meta["type"],
      })
  return descriptions
