# Itinerary Agent – trip schedule orchestration specialist
from __future__ import annotations

import json
import time
from typing import Any

from agent.models import AgentName, AgentResult, AgentTask, TaskStatus
from agent.teams.base import BaseAgent

SYSTEM_PROMPT = """You are the Itinerary Agent of TravelMind.
Your job is to compile results from other agents into a coherent day-by-day travel plan.

Given upstream results (transport, POI, hotel, weather, etc.) AND optimized itinerary data, produce:
1. A day-by-day schedule with timeline (morning / afternoon / evening).
2. Estimated time and distance between stops.
3. Tips for each day.

Respond in the same language as the user's message.
Format the itinerary in clear markdown with headers per day."""


class ItineraryAgent(BaseAgent):
  name = AgentName.ITINERARY
  description = "Compiles a day-by-day travel itinerary from upstream agent results."

  async def execute(self, task: AgentTask, context: dict[str, Any]) -> AgentResult:
    try:
      start = time.time()

      # Extract parameters
      params = task.params or {}
      destination = params.get("destination", "")
      hotel_location = params.get("hotel_location") or params.get("hotel", destination)
      trip_days = params.get("days") or params.get("duration_days", 0)
      preference = params.get("preference", "balanced")

      tool_data = {}

      # Get upstream POI data from context
      upstream = context.get("upstream_results", {})
      pois_data = self._extract_pois_from_upstream(upstream)

      # Optimize itinerary if we have POI data
      if pois_data:
        try:
          itinerary_result = await self.call_tool(
            "optimize_itinerary",
            pois=pois_data,
            hotel_location=hotel_location,
            trip_days=trip_days,
            preferences=preference,
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

      # Build prompt with all data
      prompt = self._build_prompt(task, context, tool_data)
      response = await self._call_claude(SYSTEM_PROMPT, prompt)

      return self._make_result(
        task,
        summary=f"Itinerary compiled for {task.goal}",
        data={"response": response, "tool_data": tool_data},
        start_time=start,
      )
    except Exception as exc:
      return self._make_result(
        task,
        summary="Itinerary generation failed",
        status=TaskStatus.FAILED,
        error=str(exc),
      )

  def _extract_pois_from_upstream(
    self, upstream: dict[str, Any]
  ) -> list[dict[str, Any]]:
    """Extract POI list from upstream agent results."""
    pois = []
    for agent_name, result_data in upstream.items():
      if isinstance(result_data, dict):
        # Check for tool_data -> pois -> results
        tool_data = result_data.get("tool_data", {})
        if isinstance(tool_data, dict):
          poi_data = tool_data.get("pois", {})
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
    for poi in pois[:5]:  # Limit to 5 for route planning
      name = poi.get("name", "")
      if name:
        waypoints.append(name)
    if hotel_location and len(waypoints) > 1:
      waypoints.append(hotel_location)  # Return to hotel
    return waypoints

  def _build_prompt(
    self,
    task: AgentTask,
    context: dict[str, Any],
    tool_data: dict[str, Any],
  ) -> str:
    """Compose prompt from task goal + context + tool results."""
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
          # Only include response text, not full tool_data (too verbose)
          response_text = result_data.get("response", str(result_data))
          parts.append(str(response_text)[:1500])
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
