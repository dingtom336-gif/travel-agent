# UI Mapper – converts tool raw data to frontend component formats
from __future__ import annotations

import hashlib
import json
import logging
import urllib.parse
from typing import Any, Dict, List

from agent.models import SSEEventType, SSEMessage

logger = logging.getLogger(__name__)


def _generate_image_url(name: str, category: str = "travel") -> str:
  """Generate a deterministic image URL using picsum.photos seeded by name hash."""
  seed = hashlib.md5(f"{name}-{category}".encode()).hexdigest()[:10]
  return f"https://picsum.photos/seed/{seed}/400/250"


def extract_ui_components(
  agent_name: str,
  result_data: Dict[str, Any],
) -> List[dict]:
  """Extract UI component SSE events from agent result tool_data.

  Returns list of SSE-formatted dicts ready to yield.
  """
  tool_data = result_data.get("tool_data", {})
  if not tool_data:
    return []

  events: List[dict] = []
  try:
    if agent_name == "transport":
      events.extend(_map_transport(tool_data))
    elif agent_name == "hotel":
      events.extend(_map_hotels(tool_data))
    elif agent_name == "poi":
      events.extend(_map_pois(tool_data))
    elif agent_name == "weather":
      events.extend(_map_weather(tool_data))
    elif agent_name == "itinerary":
      events.extend(_map_itinerary(tool_data))
    elif agent_name == "budget":
      events.extend(_map_budget(tool_data))
  except Exception as exc:
    logger.warning("UI mapper error for %s: %s", agent_name, exc)

  return events


def _make_ui_event(comp_type: str, data: dict) -> dict:
  """Build a single ui_component SSE event."""
  return SSEMessage(
    event=SSEEventType.UI_COMPONENT,
    data={"type": comp_type, "status": "loaded", "data": data},
  ).format()


def _map_transport(tool_data: Dict[str, Any]) -> List[dict]:
  """Map transport tool_data to flight_card events."""
  events = []
  # Try transit results first, then direct flights
  flights_raw = []
  transit = tool_data.get("transit", {})
  if isinstance(transit, dict):
    flights_raw = transit.get("results", [])
  if not flights_raw:
    flights_obj = tool_data.get("flights", {})
    if isinstance(flights_obj, dict):
      flights_raw = flights_obj.get("results", [])

  for f in flights_raw[:3]:
    events.append(_make_ui_event("flight_card", {
      "airline": f.get("airline", ""),
      "flightNo": f.get("flight_number", ""),
      "departure": f.get("departure_city", ""),
      "arrival": f.get("arrival_city", ""),
      "departTime": f.get("departure_time", ""),
      "arriveTime": f.get("arrival_time", ""),
      "duration": f.get("duration_display", ""),
      "price": f.get("price", 0),
      "currency": f.get("currency", "CNY"),
    }))
  return events


def _map_hotels(tool_data: Dict[str, Any]) -> List[dict]:
  """Map hotel tool_data to hotel_card events."""
  events = []
  hotels_obj = tool_data.get("hotels", {})
  hotels_raw = hotels_obj.get("results", []) if isinstance(hotels_obj, dict) else []

  for h in hotels_raw[:3]:
    events.append(_make_ui_event("hotel_card", {
      "name": h.get("name", ""),
      "rating": h.get("rating", 0),
      "stars": h.get("stars", 0),
      "location": h.get("area", h.get("location", "")),
      "pricePerNight": h.get("price_per_night", 0),
      "currency": h.get("currency", "CNY"),
      "amenities": h.get("facilities", [])[:6],
      "imageUrl": h.get("image_url") or _generate_image_url(h.get("name", ""), "hotel"),
    }))
  return events


def _map_pois(tool_data: Dict[str, Any]) -> List[dict]:
  """Map POI tool_data to poi_card events."""
  events = []
  pois_obj = tool_data.get("pois", {})
  pois_raw = pois_obj.get("results", []) if isinstance(pois_obj, dict) else []

  for p in pois_raw[:4]:
    events.append(_make_ui_event("poi_card", {
      "name": p.get("name", ""),
      "type": p.get("category", "scenic"),
      "rating": p.get("rating", 0),
      "description": p.get("desc", ""),
      "openingHours": p.get("hours", ""),
      "ticketPrice": p.get("price", 0),
      "currency": "CNY",
      "imageUrl": p.get("image_url") or _generate_image_url(p.get("name", ""), p.get("category", "scenic")),
    }))
  return events


def _map_weather(tool_data: Dict[str, Any]) -> List[dict]:
  """Map weather tool_data to weather_card events."""
  events = []
  forecast_obj = tool_data.get("forecast", {})
  forecast_raw = []
  if isinstance(forecast_obj, dict):
    forecast_raw = forecast_obj.get("forecast", [])

  for w in forecast_raw[:5]:
    events.append(_make_ui_event("weather_card", {
      "city": forecast_obj.get("query", {}).get("city", ""),
      "date": w.get("date", ""),
      "temperature": {"high": w.get("temp_high", w.get("high_temp", 0)), "low": w.get("temp_low", w.get("low_temp", 0))},
      "condition": w.get("condition", ""),
      "humidity": w.get("humidity", 0),
      "suggestion": w.get("travel_advice", w.get("clothing_advice", "")),
    }))
  return events


def _map_itinerary(tool_data: Dict[str, Any]) -> List[dict]:
  """Map itinerary tool_data to timeline_card events."""
  events = []
  itinerary = tool_data.get("optimized_itinerary", {})
  days = itinerary.get("days", []) if isinstance(itinerary, dict) else []

  for day_info in days:
    items = []
    for item in day_info.get("schedule", []):
      category = item.get("category", "attraction")
      type_map = {
        "scenic": "attraction", "restaurant": "food",
        "shopping": "activity", "activity": "activity",
        "museum": "attraction", "park": "attraction",
      }
      items.append({
        "time": item.get("start_time", ""),
        "title": item.get("poi_name", ""),
        "description": ", ".join(item.get("tips", [])) or category,
        "type": type_map.get(category, "attraction"),
        "duration": f"{item.get('estimated_duration_hours', 2)}h",
      })
    events.append(_make_ui_event("timeline_card", {
      "day": day_info.get("day", 0),
      "date": "",
      "title": f"Day {day_info.get('day', 0)}",
      "items": items,
    }))

  # Extract route map from POI coordinates across all days
  route_points = []
  for day_info in days:
    for item in day_info.get("schedule", []):
      lat = item.get("lat") or item.get("latitude")
      lng = item.get("lng") or item.get("longitude") or item.get("lon")
      if lat and lng:
        route_points.append({
          "lat": float(lat),
          "lng": float(lng),
          "label": item.get("poi_name", ""),
        })
  if len(route_points) >= 2:
    events.append(_make_ui_event("route_map", {
      "points": route_points,
      "title": "行程路线图",
    }))

  return events


def _map_budget(tool_data: Dict[str, Any]) -> List[dict]:
  """Map budget tool_data to budget_chart event."""
  allocation = tool_data.get("budget_allocation", {})
  if not isinstance(allocation, dict) or not allocation.get("success"):
    return []

  alloc = allocation.get("allocation", {})
  items = []
  cat_map = {
    "transport": "transport", "accommodation": "accommodation",
    "food": "food", "activities": "ticket", "misc": "other",
  }
  for key, amount in alloc.items():
    if key in cat_map and isinstance(amount, (int, float)):
      items.append({
        "id": key,
        "category": cat_map.get(key, "other"),
        "name": key.capitalize(),
        "amount": amount,
        "currency": allocation.get("currency", "CNY"),
      })

  total = allocation.get("total_budget", sum(i["amount"] for i in items))
  spent = sum(i["amount"] for i in items)

  return [_make_ui_event("budget_chart", {
    "totalBudget": total,
    "totalSpent": spent,
    "currency": allocation.get("currency", "CNY"),
    "items": items,
  })]


def truncate_tool_data_for_synthesis(result_data: Dict[str, Any]) -> str:
  """Build a compact key-facts summary of tool_data for synthesis prompt.

  Instead of dumping raw JSON and truncating, extract critical fields
  per agent type so the Synthesizer LLM can reference specific details
  (flight numbers, hotel names, prices, etc.) without data loss.
  """
  tool_data = result_data.get("tool_data", {})
  if not tool_data:
    return ""
  try:
    lines: List[str] = []

    # -- Flights --
    for key in ("transit", "flights"):
      obj = tool_data.get(key, {})
      results = obj.get("results", []) if isinstance(obj, dict) else []
      for f in results:
        parts = [
          f.get("flight_number", ""),
          f.get("airline", ""),
          f"{f.get('departure_city', '')}→{f.get('arrival_city', '')}",
          f"{f.get('departure_time', '')}-{f.get('arrival_time', '')}",
          f.get("duration_display", ""),
          f"¥{f.get('price', 0)}",
        ]
        lines.append("✈ " + " | ".join(p for p in parts if p and p != "→" and p != "-" and p != "¥0"))

    # -- Hotels --
    hotels_obj = tool_data.get("hotels", {})
    hotels = hotels_obj.get("results", []) if isinstance(hotels_obj, dict) else []
    for h in hotels:
      parts = [
        h.get("name", ""),
        f"{h.get('stars', '')}星" if h.get("stars") else "",
        f"评分{h.get('rating', '')}" if h.get("rating") else "",
        h.get("area", h.get("location", "")),
        f"¥{h.get('price_per_night', 0)}/晚" if h.get("price_per_night") else "",
      ]
      lines.append("🏨 " + " | ".join(p for p in parts if p and p != "星" and p != "¥0/晚"))

    # -- POIs --
    pois_obj = tool_data.get("pois", {})
    pois = pois_obj.get("results", []) if isinstance(pois_obj, dict) else []
    for p in pois:
      parts = [
        p.get("name", ""),
        p.get("category", ""),
        f"评分{p.get('rating', '')}" if p.get("rating") else "",
        f"¥{p.get('price', 0)}" if p.get("price") else "免费",
        p.get("hours", ""),
      ]
      lines.append("📍 " + " | ".join(p_item for p_item in parts if p_item))

    # -- Weather --
    forecast_obj = tool_data.get("forecast", {})
    if isinstance(forecast_obj, dict):
      city = forecast_obj.get("query", {}).get("city", "")
      for w in forecast_obj.get("forecast", []):
        parts = [
          city,
          w.get("date", ""),
          w.get("condition", ""),
          f"{w.get('temp_low', w.get('low_temp', ''))}~{w.get('temp_high', w.get('high_temp', ''))}°C",
        ]
        lines.append("🌤 " + " | ".join(p for p in parts if p and p != "~°C"))

    # -- Budget --
    budget = tool_data.get("budget_allocation", {})
    if isinstance(budget, dict) and budget.get("success"):
      alloc = budget.get("allocation", {})
      total = budget.get("total_budget", 0)
      items = [f"{k}:¥{v}" for k, v in alloc.items() if isinstance(v, (int, float))]
      if items:
        lines.append(f"💰 总预算¥{total} → " + ", ".join(items))

    # -- Itinerary --
    itin = tool_data.get("optimized_itinerary", {})
    if isinstance(itin, dict):
      for day in itin.get("days", []):
        pois_names = [s.get("poi_name", "") for s in day.get("schedule", []) if s.get("poi_name")]
        if pois_names:
          lines.append(f"📅 Day{day.get('day', '?')}: " + " → ".join(pois_names))

    # -- Fallback: unknown data types not covered above --
    if not lines:
      raw = json.dumps(tool_data, ensure_ascii=False, default=str)
      if len(raw) > 3000:
        raw = raw[:3000] + "..."
      return f"\nStructured data: {raw}"

    return "\nKey facts:\n" + "\n".join(lines)
  except Exception:
    return ""
