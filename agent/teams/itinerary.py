# Itinerary Agent – trip schedule orchestration specialist
from __future__ import annotations

import json
from typing import Any

from agent.models import AgentName, AgentTask
from agent.teams.base import BaseAgent


class ItineraryAgent(BaseAgent):
  name = AgentName.ITINERARY
  description = "Compiles a day-by-day travel itinerary from upstream agent results."
  _success_label = "Itinerary compiled"
  _failure_label = "Itinerary generation failed"

  system_prompt = """You are the Itinerary Agent of TravelMind.
Your job is to compile results from other agents into a coherent day-by-day travel plan.

Given upstream results (transport, POI, hotel, weather, etc.) AND optimized itinerary data, produce:
1. A day-by-day schedule with timeline (morning / afternoon / evening).
2. Estimated time and distance between stops.
3. Tips for each day.

CRITICAL RULES for geographic optimization:
- Group geographically close locations on the same day to minimize transit time.
- For multi-city trips, arrange cities by geographic proximity to minimize backtracking.
  Example: 北京→天津→济南→南京→上海 (good), NOT 北京→上海→天津 (bad backtracking).
- Each day's route should form a logical geographic loop from the hotel.
- Consider actual geographic distance: nearby cities first, distant cities later.
- NEVER put geographically distant cities between two close ones.

Respond in the same language as the user's message.
Format the itinerary in clear markdown with headers per day."""

  async def _run_tools(
    self, task: AgentTask, context: dict[str, Any],
  ) -> dict[str, Any]:
    params = task.params or {}
    destination = params.get("destination", "")
    hotel_location = params.get("hotel_location") or params.get("hotel", destination)
    trip_days = params.get("days") or params.get("duration_days", 0)
    preference = params.get("preference", "balanced")

    tool_data: dict[str, Any] = {}

    # Get upstream data from context
    upstream = context.get("upstream_results", {})
    pois_data = self._extract_pois_from_upstream(upstream)

    # Extract hotel info from upstream (structured data)
    hotel_coordinates = None
    hotel_upstream = upstream.get("hotel", {})
    if isinstance(hotel_upstream, dict):
      hotel_td = hotel_upstream.get("tool_data", {})
      if isinstance(hotel_td, dict):
        hotels_results = hotel_td.get("hotels", {})
        if isinstance(hotels_results, dict):
          hotel_list = hotels_results.get("results", [])
          if hotel_list:
            top_hotel = hotel_list[0]
            hotel_location = top_hotel.get("name", hotel_location)
            hotel_coordinates = top_hotel.get("coordinates")

    # Optimize itinerary if we have POI data
    if pois_data:
      try:
        kwargs: dict[str, Any] = {
          "pois": pois_data,
          "hotel_location": hotel_location,
          "trip_days": trip_days,
          "preferences": preference,
        }
        if hotel_coordinates:
          kwargs["hotel_coordinates"] = hotel_coordinates
        itinerary_result = await self.call_tool(
          "optimize_itinerary", **kwargs,
        )
        tool_data["optimized_itinerary"] = itinerary_result
      except Exception:
        pass

    # Get route plan if we have locations
    if destination:
      try:
        waypoints = self._extract_waypoints(pois_data, hotel_location)
        if len(waypoints) >= 2:
          route_result = await self.call_tool(
            "plan_route",
            waypoints=waypoints,
            mode="walking",
          )
          tool_data["route"] = route_result
      except Exception:
        pass

    return tool_data

  def _build_prompt(
    self,
    task: AgentTask,
    context: dict[str, Any],
    tool_data: dict[str, Any],
  ) -> str:
    """Override to include upstream agent results."""
    parts = [f"Task: {task.goal}"]
    if task.params:
      parts.append(f"Parameters: {task.params}")

    # Include upstream agent results
    upstream = context.get("upstream_results", {})
    if upstream:
      parts.append("=== Upstream Agent Results ===")
      for agent_name, result_data in upstream.items():
        parts.append(f"--- {agent_name} ---")
        if isinstance(result_data, dict):
          response_text = result_data.get("response", "")
          if response_text:
            parts.append(str(response_text)[:1500])
          else:
            parts.append(str(result_data)[:1500])
        else:
          parts.append(str(result_data)[:1500])

    if tool_data:
      parts.append("=== Tool Results ===")
      for tool_name, result in tool_data.items():
        parts.append(f"--- {tool_name} ---")
        parts.append(json.dumps(result, ensure_ascii=False, default=str)[:3000])

    state_ctx = context.get("state_context", "")
    if state_ctx:
      parts.append(f"Current travel state:\n{state_ctx}")

    return "\n\n".join(parts)

  def _extract_pois_from_upstream(
    self, upstream: dict[str, Any],
  ) -> list[dict[str, Any]]:
    """Extract POI list from upstream agent results."""
    pois: list[dict[str, Any]] = []
    for _agent_name, result_data in upstream.items():
      if isinstance(result_data, dict):
        td = result_data.get("tool_data", {})
        if isinstance(td, dict):
          poi_data = td.get("pois", {})
          if isinstance(poi_data, dict) and poi_data.get("results"):
            pois.extend(poi_data["results"])
    return pois

  def _extract_waypoints(
    self,
    pois: list[dict[str, Any]],
    hotel_location: str,
  ) -> list[str]:
    """Extract waypoint names from POIs for route planning."""
    waypoints = [hotel_location] if hotel_location else []
    for poi in pois[:5]:
      name = poi.get("name", "")
      if name:
        waypoints.append(name)
    if hotel_location and len(waypoints) > 1:
      waypoints.append(hotel_location)
    return waypoints
