# Transit optimizer skill - combines flight_search + map_service
# Finds the optimal transport option based on user preferences
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from agent.tools.mcp.flight_search import search_flights
from agent.tools.mcp.map_service import get_distance


# Preference weights for scoring
_PREFERENCE_WEIGHTS = {
  "price": {"price": 0.6, "time": 0.2, "comfort": 0.2},
  "time": {"price": 0.2, "time": 0.6, "comfort": 0.2},
  "comfort": {"price": 0.2, "time": 0.2, "comfort": 0.6},
  "balanced": {"price": 0.34, "time": 0.33, "comfort": 0.33},
}

# Comfort scores by mode
_COMFORT_SCORES = {
  "flight": 0.8,
  "train": 0.9,
  "driving": 0.6,
  "bus": 0.4,
}


def _score_option(
  option: Dict[str, Any],
  all_options: List[Dict[str, Any]],
  weights: Dict[str, float],
) -> float:
  """Score a transport option relative to all options.

  Normalizes price and time across all options, then applies weights.
  Returns score 0-100 (higher is better).
  """
  prices = [o["price"] for o in all_options if o.get("price")]
  times = [o["duration_hours"] for o in all_options if o.get("duration_hours")]

  if not prices or not times:
    return 50

  # Invert price (lower price = higher score)
  min_p, max_p = min(prices), max(prices)
  if max_p > min_p:
    price_score = 1 - (option.get("price", max_p) - min_p) / (max_p - min_p)
  else:
    price_score = 1.0

  # Invert time (shorter = higher score)
  min_t, max_t = min(times), max(times)
  if max_t > min_t:
    time_score = 1 - (option.get("duration_hours", max_t) - min_t) / (max_t - min_t)
  else:
    time_score = 1.0

  comfort_score = option.get("comfort_score", 0.5)

  total = (
    weights.get("price", 0.34) * price_score +
    weights.get("time", 0.33) * time_score +
    weights.get("comfort", 0.33) * comfort_score
  )
  return round(total * 100, 1)


async def optimize_transit(
  departure: str,
  arrival: str,
  date: str,
  preferences: Optional[str] = "balanced",
  passengers: int = 1,
) -> Dict[str, Any]:
  """Find the optimal transport option between two cities.

  Combines flight search with ground transport options and ranks them
  based on user preferences (price / time / comfort / balanced).

  Args:
    departure: Departure city
    arrival: Arrival city
    date: Travel date (YYYY-MM-DD)
    preferences: Priority: "price" / "time" / "comfort" / "balanced"
    passengers: Number of travelers

  Returns:
    Dict with ranked transport options and recommendation
  """
  try:
    # Run searches in parallel
    flight_task = search_flights(
      departure, arrival, date, passengers=passengers, max_results=3
    )
    train_task = get_distance(departure, arrival, mode="train")
    drive_task = get_distance(departure, arrival, mode="driving")

    flight_result, train_result, drive_result = await asyncio.gather(
      flight_task, train_task, drive_task
    )

    all_options: List[Dict[str, Any]] = []

    # Process flight results
    if flight_result.get("success") and flight_result.get("results"):
      for flight in flight_result["results"][:3]:
        all_options.append({
          "mode": "flight",
          "mode_display": "飞机",
          "detail": f"{flight['airline']} {flight['flight_number']}",
          "departure_time": flight["departure_time"],
          "arrival_time": flight["arrival_time"],
          "duration_hours": flight["duration_hours"],
          "duration_display": flight["duration_display"],
          "price": flight["total_price"],
          "price_per_person": flight["price"],
          "currency": "CNY",
          "comfort_score": _COMFORT_SCORES["flight"],
          "stops": flight.get("stops", 0),
          "extra_info": {
            "cabin": flight.get("cabin_class", "economy"),
            "baggage": flight.get("baggage_allowance", "23kg"),
            "refundable": flight.get("refundable", False),
          },
        })

    # Process train option
    if train_result.get("success"):
      train_price = train_result.get("estimated_cost", 0) * passengers
      all_options.append({
        "mode": "train",
        "mode_display": "高铁/火车",
        "detail": f"{departure}→{arrival} 高铁",
        "departure_time": "多班次可选",
        "arrival_time": "-",
        "duration_hours": train_result.get("duration_hours", 0),
        "duration_display": train_result.get("duration_display", ""),
        "price": int(train_price),
        "price_per_person": train_result.get("estimated_cost", 0),
        "currency": "CNY",
        "comfort_score": _COMFORT_SCORES["train"],
        "stops": 0,
        "extra_info": {
          "distance_km": train_result.get("distance_km", 0),
          "seat_type": "二等座",
        },
      })

    # Process driving option
    if drive_result.get("success"):
      drive_cost = drive_result.get("estimated_cost", 0)
      all_options.append({
        "mode": "driving",
        "mode_display": "自驾",
        "detail": f"{departure}→{arrival} 自驾",
        "departure_time": "灵活出发",
        "arrival_time": "-",
        "duration_hours": drive_result.get("duration_hours", 0),
        "duration_display": drive_result.get("duration_display", ""),
        "price": int(drive_cost),
        "price_per_person": int(drive_cost / max(passengers, 1)),
        "currency": "CNY",
        "comfort_score": _COMFORT_SCORES["driving"],
        "stops": 0,
        "extra_info": {
          "distance_km": drive_result.get("distance_km", 0),
          "note": "费用含油费及过路费估算",
        },
      })

    # Score and rank
    weights = _PREFERENCE_WEIGHTS.get(preferences or "balanced", _PREFERENCE_WEIGHTS["balanced"])
    for option in all_options:
      option["score"] = _score_option(option, all_options, weights)

    all_options.sort(key=lambda o: o["score"], reverse=True)

    # Build recommendation
    recommendation = None
    if all_options:
      best = all_options[0]
      recommendation = (
        f"推荐选择{best['mode_display']}（{best['detail']}），"
        f"耗时约{best['duration_display']}，"
        f"总价约¥{best['price']}，"
        f"综合评分{best['score']}分"
      )

    return {
      "success": True,
      "query": {
        "departure": departure,
        "arrival": arrival,
        "date": date,
        "passengers": passengers,
        "preferences": preferences,
      },
      "options": all_options,
      "recommendation": recommendation,
      "total_options": len(all_options),
    }
  except Exception as exc:
    return {
      "success": False,
      "error": str(exc),
      "query": {
        "departure": departure,
        "arrival": arrival,
        "date": date,
      },
      "options": [],
    }
