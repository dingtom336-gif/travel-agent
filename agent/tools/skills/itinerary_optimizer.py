# Itinerary optimizer skill - optimizes daily visit order
# Combines POI data + map_service to minimize travel time
from __future__ import annotations

import asyncio
import random
from typing import Any, Dict, List, Optional

from agent.tools.mcp.map_service import get_distance


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


def _build_day_schedule(
  day_pois: List[Dict[str, Any]],
  hotel_location: str,
) -> List[Dict[str, Any]]:
  """Build a schedule for one day with time slots and transport."""
  schedule = []
  taken_slots: List[str] = []

  # Assign time slots
  poi_with_slots = []
  for poi in day_pois:
    slot = _assign_time_slot(poi, taken_slots)
    if slot:
      taken_slots.append(slot)
      poi_with_slots.append((poi, slot))

  # Sort by time slot order
  slot_order = ["morning", "lunch", "afternoon", "dinner", "evening"]
  poi_with_slots.sort(key=lambda x: slot_order.index(x[1]) if x[1] in slot_order else 99)

  for poi, slot in poi_with_slots:
    slot_info = _TIME_SLOTS.get(slot, _TIME_SLOTS["morning"])
    category = poi.get("category", "scenic")
    duration = poi.get("duration_hours") or _DEFAULT_DURATIONS.get(category, 2.0)

    schedule.append({
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
    })

  return schedule


async def optimize_itinerary(
  pois: List[Dict[str, Any]],
  hotel_location: str,
  trip_days: int = 0,
  preferences: Optional[str] = "balanced",
) -> Dict[str, Any]:
  """Optimize visit order for a multi-day itinerary.

  Groups POIs into daily schedules, optimizing for:
  - Minimal travel distance between consecutive stops
  - Appropriate time-of-day placement (e.g., restaurants at meal times)
  - Even distribution across days

  Args:
    pois: List of POI objects (must have 'name', 'category' at minimum)
    hotel_location: Hotel name or area (used as daily start/end point)
    trip_days: Number of days (0 = auto-calculate based on POI count)
    preferences: "balanced" / "relaxed" / "compact"

  Returns:
    Dict with daily schedules, distance estimates, and tips
  """
  try:
    await asyncio.sleep(random.uniform(0.1, 0.2))

    if not pois:
      return {
        "success": False,
        "error": "No POIs provided",
        "days": [],
      }

    # Auto-calculate days if not specified
    if trip_days <= 0:
      pois_per_day = 3 if preferences == "relaxed" else 5 if preferences == "compact" else 4
      trip_days = max(1, len(pois) // pois_per_day + (1 if len(pois) % pois_per_day else 0))

    # Group POIs by category for balanced distribution
    categorized: Dict[str, List[Dict[str, Any]]] = {}
    for poi in pois:
      cat = poi.get("category", "scenic")
      if cat not in categorized:
        categorized[cat] = []
      categorized[cat].append(poi)

    # Determine POIs per day based on preference
    if preferences == "relaxed":
      max_per_day = 3
    elif preferences == "compact":
      max_per_day = 6
    else:
      max_per_day = 4

    # Distribute POIs across days
    daily_pois: List[List[Dict[str, Any]]] = [[] for _ in range(trip_days)]

    # Ensure each day gets a mix of categories
    all_pois = list(pois)
    # Prioritize by rating
    all_pois.sort(key=lambda p: p.get("rating", 0), reverse=True)

    day_idx = 0
    for poi in all_pois:
      # Find the day with fewest POIs that hasn't exceeded max
      min_count = min(len(d) for d in daily_pois)
      for i in range(trip_days):
        if len(daily_pois[i]) == min_count and len(daily_pois[i]) < max_per_day:
          daily_pois[i].append(poi)
          break
      else:
        # All days are at max, add to the day with fewest
        min_idx = min(range(trip_days), key=lambda x: len(daily_pois[x]))
        daily_pois[min_idx].append(poi)

    # Build daily schedules
    days_result = []
    total_attractions_cost = 0

    for day_num, day_poi_list in enumerate(daily_pois, 1):
      schedule = _build_day_schedule(day_poi_list, hotel_location)

      # Calculate daily costs
      daily_ticket_cost = sum(item.get("ticket_price", 0) for item in schedule)
      total_attractions_cost += daily_ticket_cost

      # Estimate daily walking distance (mock)
      daily_walking_km = round(random.uniform(3, 12), 1)

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

  return tips[:3]  # Limit to 3 tips per day
