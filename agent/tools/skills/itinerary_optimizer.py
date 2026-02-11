# Itinerary optimizer skill - optimizes daily visit order
# Uses geographic clustering (Haversine) to group nearby POIs per day
from __future__ import annotations

import asyncio
import math
import random
from typing import Any, Dict, List, Optional


# Time slot preferences for different POI categories
_TIME_SLOT_PREFERENCE: Dict[str, List[str]] = {
  "scenic": ["morning", "afternoon"],
  "museum": ["morning", "afternoon"],
  "park": ["morning", "afternoon"],
  "restaurant": ["lunch", "dinner"],
  "shopping": ["afternoon", "evening"],
  "activity": ["morning", "afternoon", "evening"],
}

# Time slot time ranges
_TIME_SLOTS = {
  "morning": {"start": "09:00", "end": "12:00", "label": "上午"},
  "lunch": {"start": "12:00", "end": "14:00", "label": "午餐"},
  "afternoon": {"start": "14:00", "end": "17:00", "label": "下午"},
  "dinner": {"start": "17:30", "end": "19:30", "label": "晚餐"},
  "evening": {"start": "19:30", "end": "22:00", "label": "晚间"},
}

# Default visit durations by category (hours)
_DEFAULT_DURATIONS: Dict[str, float] = {
  "scenic": 2.0,
  "museum": 2.5,
  "park": 1.5,
  "restaurant": 1.5,
  "shopping": 2.0,
  "activity": 3.0,
}

# Road network factor: straight-line distance * factor ≈ walking distance
_ROAD_FACTOR = 1.3


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
  """Calculate distance in km between two coordinates using Haversine formula."""
  R = 6371.0
  dlat = math.radians(lat2 - lat1)
  dlng = math.radians(lng2 - lng1)
  a = (
    math.sin(dlat / 2) ** 2
    + math.cos(math.radians(lat1))
    * math.cos(math.radians(lat2))
    * math.sin(dlng / 2) ** 2
  )
  return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _get_coords(poi: Dict[str, Any]) -> Optional[tuple[float, float]]:
  """Extract (lat, lng) from a POI dict, return None if missing."""
  coords = poi.get("coordinates", {})
  if isinstance(coords, dict) and "lat" in coords and "lng" in coords:
    return (coords["lat"], coords["lng"])
  return None


def _assign_time_slot(poi: Dict[str, Any], taken_slots: List[str]) -> Optional[str]:
  """Assign a time slot to a POI based on its category and availability."""
  category = poi.get("category", "scenic")
  preferred = _TIME_SLOT_PREFERENCE.get(category, ["morning", "afternoon"])

  for slot in preferred:
    if slot not in taken_slots:
      return slot

  # Fallback: any available slot
  all_slots = ["morning", "lunch", "afternoon", "dinner", "evening"]
  for slot in all_slots:
    if slot not in taken_slots:
      return slot

  return None


def _order_pois_nearest_neighbor(
  pois: List[Dict[str, Any]],
  start_coords: Optional[tuple[float, float]],
) -> List[Dict[str, Any]]:
  """Order POIs using nearest-neighbor heuristic from start point."""
  if not start_coords or len(pois) <= 1:
    return pois

  remaining = list(pois)
  ordered: List[Dict[str, Any]] = []
  current = start_coords

  while remaining:
    best_idx = 0
    best_dist = float("inf")
    for i, poi in enumerate(remaining):
      pc = _get_coords(poi)
      if pc:
        d = _haversine(current[0], current[1], pc[0], pc[1])
        if d < best_dist:
          best_dist = d
          best_idx = i
    chosen = remaining.pop(best_idx)
    ordered.append(chosen)
    pc = _get_coords(chosen)
    if pc:
      current = pc

  return ordered


def _build_day_schedule(
  day_pois: List[Dict[str, Any]],
  hotel_location: str,
  hotel_coords: Optional[tuple[float, float]],
) -> List[Dict[str, Any]]:
  """Build a schedule for one day with time slots and transport."""
  # Order POIs geographically first (nearest-neighbor from hotel)
  ordered_pois = _order_pois_nearest_neighbor(day_pois, hotel_coords)

  schedule = []
  taken_slots: List[str] = []

  # Assign time slots
  poi_with_slots = []
  for poi in ordered_pois:
    slot = _assign_time_slot(poi, taken_slots)
    if slot:
      taken_slots.append(slot)
      poi_with_slots.append((poi, slot))

  # Sort by time slot order
  slot_order = ["morning", "lunch", "afternoon", "dinner", "evening"]
  poi_with_slots.sort(key=lambda x: slot_order.index(x[1]) if x[1] in slot_order else 99)

  prev_coords = hotel_coords
  for poi, slot in poi_with_slots:
    slot_info = _TIME_SLOTS.get(slot, _TIME_SLOTS["morning"])
    category = poi.get("category", "scenic")
    duration = poi.get("duration_hours") or _DEFAULT_DURATIONS.get(category, 2.0)

    # Calculate distance from previous stop
    dist_from_prev_km = 0.0
    poi_coords = _get_coords(poi)
    if prev_coords and poi_coords:
      dist_from_prev_km = round(_haversine(prev_coords[0], prev_coords[1], poi_coords[0], poi_coords[1]) * _ROAD_FACTOR, 1)
    prev_coords = poi_coords or prev_coords

    entry: Dict[str, Any] = {
      "poi_name": poi.get("name", "未知景点"),
      "poi_name_en": poi.get("name_en", ""),
      "category": category,
      "time_slot": slot,
      "time_slot_label": slot_info["label"],
      "start_time": slot_info["start"],
      "end_time": slot_info["end"],
      "estimated_duration_hours": duration,
      "ticket_price": poi.get("price", 0),
      "tips": poi.get("tips", []),
      "rating": poi.get("rating", 0),
      "distance_from_prev_km": dist_from_prev_km,
    }
    # Pass coordinates for route_map rendering
    if poi_coords:
      entry["lat"] = poi_coords[0]
      entry["lng"] = poi_coords[1]

    schedule.append(entry)

  return schedule


def _cluster_pois_by_distance(
  pois: List[Dict[str, Any]],
  hotel_coords: Optional[tuple[float, float]],
  trip_days: int,
  max_per_day: int,
) -> List[List[Dict[str, Any]]]:
  """Cluster POIs into daily groups based on geographic proximity to hotel."""
  daily: List[List[Dict[str, Any]]] = [[] for _ in range(trip_days)]

  if not hotel_coords:
    # Fallback: round-robin by rating
    sorted_pois = sorted(pois, key=lambda p: p.get("rating", 0), reverse=True)
    for i, poi in enumerate(sorted_pois):
      daily[i % trip_days].append(poi)
    return daily

  # Calculate distance from hotel for each POI
  poi_dists: List[tuple[Dict[str, Any], float]] = []
  for poi in pois:
    pc = _get_coords(poi)
    if pc:
      d = _haversine(hotel_coords[0], hotel_coords[1], pc[0], pc[1])
    else:
      d = 999.0
    poi_dists.append((poi, d))

  # Sort by distance from hotel (nearest first)
  poi_dists.sort(key=lambda x: x[1])

  # Greedy assignment: put POI in the day whose centroid is closest
  # Day 0 = nearest POIs, Day N = farthest, but we balance count
  centroids: List[Optional[tuple[float, float]]] = [None] * trip_days

  for poi, _dist in poi_dists:
    # Find best day: closest centroid + not full
    best_day = 0
    best_score = float("inf")
    poi_c = _get_coords(poi)

    for d in range(trip_days):
      if len(daily[d]) >= max_per_day:
        continue
      if centroids[d] is None:
        # Empty day: score by day index * base distance (spread evenly)
        score = _dist + d * 0.5
      elif poi_c:
        score = _haversine(centroids[d][0], centroids[d][1], poi_c[0], poi_c[1])
      else:
        score = len(daily[d])
      if score < best_score:
        best_score = score
        best_day = d

    daily[best_day].append(poi)
    # Update centroid
    day_coords = [_get_coords(p) for p in daily[best_day] if _get_coords(p)]
    if day_coords:
      avg_lat = sum(c[0] for c in day_coords) / len(day_coords)
      avg_lng = sum(c[1] for c in day_coords) / len(day_coords)
      centroids[best_day] = (avg_lat, avg_lng)

  return daily


async def optimize_itinerary(
  pois: List[Dict[str, Any]],
  hotel_location: str,
  trip_days: int = 0,
  preferences: Optional[str] = "balanced",
  hotel_coordinates: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
  """Optimize visit order for a multi-day itinerary.

  Groups POIs into daily schedules using geographic clustering, then
  orders each day's POIs as a nearest-neighbor loop from the hotel.

  Args:
    pois: List of POI objects (must have 'name', 'category' at minimum)
    hotel_location: Hotel name or area (used as daily start/end point)
    trip_days: Number of days (0 = auto-calculate based on POI count)
    preferences: "balanced" / "relaxed" / "compact"
    hotel_coordinates: {"lat": float, "lng": float} of the hotel

  Returns:
    Dict with daily schedules, distance estimates, and tips
  """
  try:
    await asyncio.sleep(random.uniform(0.05, 0.15))

    if not pois:
      return {
        "success": False,
        "error": "No POIs provided",
        "days": [],
      }

    # Parse hotel coordinates
    hotel_coords: Optional[tuple[float, float]] = None
    if hotel_coordinates and "lat" in hotel_coordinates and "lng" in hotel_coordinates:
      hotel_coords = (hotel_coordinates["lat"], hotel_coordinates["lng"])

    # Auto-calculate days if not specified
    if trip_days <= 0:
      pois_per_day = 3 if preferences == "relaxed" else 5 if preferences == "compact" else 4
      trip_days = max(1, len(pois) // pois_per_day + (1 if len(pois) % pois_per_day else 0))

    # Determine POIs per day based on preference
    if preferences == "relaxed":
      max_per_day = 3
    elif preferences == "compact":
      max_per_day = 6
    else:
      max_per_day = 4

    # Cluster POIs by geographic proximity
    daily_pois = _cluster_pois_by_distance(pois, hotel_coords, trip_days, max_per_day)

    # Build daily schedules
    days_result = []
    total_attractions_cost = 0

    for day_num, day_poi_list in enumerate(daily_pois, 1):
      schedule = _build_day_schedule(day_poi_list, hotel_location, hotel_coords)

      # Calculate daily costs
      daily_ticket_cost = sum(item.get("ticket_price", 0) for item in schedule)
      total_attractions_cost += daily_ticket_cost

      # Calculate walking distance from per-stop distances
      daily_walking_km = sum(item.get("distance_from_prev_km", 0) for item in schedule)
      # Add return-to-hotel distance
      if schedule and hotel_coords:
        last_item = schedule[-1]
        if "lat" in last_item and "lng" in last_item:
          daily_walking_km += _haversine(last_item["lat"], last_item["lng"], hotel_coords[0], hotel_coords[1]) * _ROAD_FACTOR
      daily_walking_km = round(daily_walking_km, 1)

      day_info = {
        "day": day_num,
        "schedule": schedule,
        "poi_count": len(schedule),
        "estimated_walking_km": daily_walking_km,
        "estimated_ticket_cost": daily_ticket_cost,
        "start_point": hotel_location,
        "end_point": hotel_location,
        "day_tips": _generate_day_tips(schedule, day_num, trip_days),
      }
      days_result.append(day_info)

    # Overall tips
    overall_tips = []
    if preferences == "relaxed":
      overall_tips.append("已安排宽松行程，每天有充足的休息和自由时间")
    elif preferences == "compact":
      overall_tips.append("紧凑行程，建议穿舒适的步行鞋，注意体力分配")
    else:
      overall_tips.append("均衡行程，兼顾游览体验和休息")

    if total_attractions_cost > 0:
      overall_tips.append(f"门票预估总计¥{total_attractions_cost}，建议提前网上购票")

    return {
      "success": True,
      "query": {
        "total_pois": len(pois),
        "trip_days": trip_days,
        "hotel_location": hotel_location,
        "preferences": preferences,
      },
      "days": days_result,
      "summary": {
        "total_days": trip_days,
        "total_pois": sum(len(d["schedule"]) for d in days_result),
        "total_ticket_cost": total_attractions_cost,
        "avg_pois_per_day": round(len(pois) / max(trip_days, 1), 1),
        "currency": "CNY",
      },
      "tips": overall_tips,
    }
  except Exception as exc:
    return {
      "success": False,
      "error": str(exc),
      "days": [],
    }


def _generate_day_tips(
  schedule: List[Dict[str, Any]],
  day_num: int,
  total_days: int,
) -> List[str]:
  """Generate tips for a specific day."""
  tips = []

  categories = [item.get("category", "") for item in schedule]
  if "museum" in categories:
    tips.append("博物馆建议上午参观，精力最充沛")
  if "park" in categories:
    tips.append("公园适合早晨散步，空气清新")
  if "shopping" in categories:
    tips.append("购物建议安排在下午或傍晚，店铺折扣可能更多")

  if day_num == 1:
    tips.append("第一天建议安排较轻松的行程，适应当地节奏")
  elif day_num == total_days:
    tips.append("最后一天注意预留去机场/车站的时间")

  return tips[:3]
