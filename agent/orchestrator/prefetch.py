# Tool data prefetching and incremental state detection helpers
# Extracted from theater.py to keep orchestration logic separate from data gathering.
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


# Fields that count toward incremental state-change detection
_INCREMENTAL_FIELDS = (
  "destination", "origin", "start_date", "end_date",
  "duration_days", "travelers", "budget", "preferences", "constraints",
)


def _detect_state_changes(
  old_state: Optional[Any],
  new_state: Optional[Any],
) -> dict[str, tuple[Any, Any]]:
  """Compare two SessionState objects, return changed fields as {field: (old, new)}."""
  if old_state is None or new_state is None:
    return {}
  changes: dict[str, tuple[Any, Any]] = {}
  for field in _INCREMENTAL_FIELDS:
    old_val = getattr(old_state, field, None)
    new_val = getattr(new_state, field, None)
    if old_val != new_val and new_val is not None:
      changes[field] = (old_val, new_val)
  return changes


def _format_state_changes(changes: dict[str, tuple[Any, Any]]) -> str:
  """Format state changes into readable text for the incremental prompt."""
  lines: list[str] = []
  for field, (old_val, new_val) in changes.items():
    if old_val is not None:
      lines.append(f"- {field}: {old_val} → {new_val}")
    else:
      lines.append(f"- {field}: (新增) {new_val}")
  return "\n".join(lines) if lines else "无明显参数变化"


def _snapshot_state(state: Optional[Any]) -> Optional[Any]:
  """Create a shallow copy of state fields for later comparison."""
  if state is None:
    return None
  from agent.models import SessionState
  snap = SessionState()
  for field in _INCREMENTAL_FIELDS:
    val = getattr(state, field, None)
    if val is not None:
      setattr(snap, field, val)
  return snap


def _guess_affected_sections(changes: dict[str, tuple[Any, Any]]) -> list[str]:
  """Map state field changes to likely affected SECTION names."""
  affected: set[str] = set()
  field_to_sections: dict[str, list[str]] = {
    "budget": ["hotel", "transport", "poi"],
    "duration_days": ["itinerary", "hotel"],
    "start_date": ["weather", "transport", "itinerary"],
    "end_date": ["weather", "itinerary"],
    "travelers": ["hotel", "transport"],
    "origin": ["transport"],
    "preferences": ["poi", "itinerary"],
    "constraints": ["poi", "itinerary"],
  }
  for field in changes:
    for section in field_to_sections.get(field, ["itinerary"]):
      affected.add(section)
  # Always include itinerary as it's the most commonly affected
  affected.add("itinerary")
  return list(affected)[:3]


async def gather_tool_data(state: Optional[Any]) -> dict[str, Any]:
  """Call mock tools in parallel to collect supplementary data.

  This pre-gathers data that enriches the mega prompt. Since tools are
  mock-based, they're fast. Real API integration would add timeouts here.
  """
  if state is None:
    return {}

  tool_data: dict[str, Any] = {}
  tasks: list[tuple[str, Any]] = []

  dest = getattr(state, "destination", None)
  origin = getattr(state, "origin", None)
  start_date = getattr(state, "start_date", None)
  duration = getattr(state, "duration_days", None)
  travelers = getattr(state, "travelers", None) or 1
  budget = getattr(state, "budget", None)

  if dest:
    # Weather data
    try:
      from agent.tools.mcp.weather_api import get_weather_forecast
      tasks.append(("weather", get_weather_forecast(
        city=dest,
        start_date=start_date or "2026-04-01",
        days=duration or 5,
      )))
    except Exception:
      pass

    # POI data
    try:
      from agent.tools.mcp.poi_search import search_pois
      tasks.append(("pois", search_pois(
        city=dest,
        category=None,
        limit=10,
      )))
    except Exception:
      pass

    # Hotel data – needs checkin/checkout dates
    try:
      from agent.tools.mcp.hotel_search import search_hotels
      checkin = start_date or "2026-04-01"
      # Calculate checkout from duration
      try:
        from datetime import datetime, timedelta
        ci = datetime.strptime(checkin, "%Y-%m-%d")
        checkout = (ci + timedelta(days=duration or 3)).strftime("%Y-%m-%d")
      except Exception:
        checkout = "2026-04-04"
      tasks.append(("hotels", search_hotels(
        city=dest,
        checkin=checkin,
        checkout=checkout,
        guests=travelers,
      )))
    except Exception:
      pass

    # Transport data
    if origin:
      try:
        from agent.tools.mcp.flight_search import search_flights
        tasks.append(("flights", search_flights(
          departure=origin,
          arrival=dest,
          date=start_date or "",
          passengers=travelers,
        )))
      except Exception:
        pass

  # Run all tool calls in parallel
  if tasks:
    names = [t[0] for t in tasks]
    coros = [t[1] for t in tasks]
    try:
      results = await asyncio.gather(*coros, return_exceptions=True)
      for name, result in zip(names, results):
        if isinstance(result, Exception):
          logger.warning("Tool %s failed: %s", name, result)
        else:
          tool_data[name] = result
    except Exception as exc:
      logger.warning("gather_tool_data error: %s", exc)

  return tool_data
