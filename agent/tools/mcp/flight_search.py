# Flight search MCP tool - mock implementation
# Returns realistic flight data for development/testing
from __future__ import annotations

import asyncio
import random
from typing import Any, Dict, List, Optional


# Mock airline data pool
_AIRLINES = [
  {"code": "CA", "name": "中国国际航空", "name_en": "Air China"},
  {"code": "MU", "name": "中国东方航空", "name_en": "China Eastern"},
  {"code": "CZ", "name": "中国南方航空", "name_en": "China Southern"},
  {"code": "HU", "name": "海南航空", "name_en": "Hainan Airlines"},
  {"code": "3U", "name": "四川航空", "name_en": "Sichuan Airlines"},
  {"code": "ZH", "name": "深圳航空", "name_en": "Shenzhen Airlines"},
  {"code": "NH", "name": "全日空", "name_en": "ANA"},
  {"code": "JL", "name": "日本航空", "name_en": "JAL"},
  {"code": "KE", "name": "大韩航空", "name_en": "Korean Air"},
  {"code": "SQ", "name": "新加坡航空", "name_en": "Singapore Airlines"},
  {"code": "TG", "name": "泰国国际航空", "name_en": "Thai Airways"},
  {"code": "CX", "name": "国泰航空", "name_en": "Cathay Pacific"},
]

# Approximate flight durations (hours) between city pairs
_ROUTE_DURATIONS: Dict[str, float] = {
  "北京-上海": 2.5,
  "北京-广州": 3.5,
  "北京-深圳": 3.5,
  "北京-成都": 3.0,
  "北京-东京": 3.5,
  "北京-大阪": 3.5,
  "北京-首尔": 2.0,
  "北京-曼谷": 5.0,
  "北京-新加坡": 6.5,
  "上海-广州": 2.5,
  "上海-深圳": 2.5,
  "上海-成都": 3.0,
  "上海-东京": 3.0,
  "上海-大阪": 2.5,
  "上海-首尔": 2.0,
  "上海-曼谷": 4.5,
  "上海-新加坡": 5.5,
  "广州-东京": 4.0,
  "广州-大阪": 3.5,
  "广州-曼谷": 3.0,
  "广州-新加坡": 4.0,
  "成都-东京": 5.0,
  "成都-曼谷": 3.5,
}

# Base prices (CNY) for routes
_BASE_PRICES: Dict[str, int] = {
  "北京-上海": 800,
  "北京-广州": 1200,
  "北京-深圳": 1200,
  "北京-成都": 1000,
  "北京-东京": 2500,
  "北京-大阪": 2300,
  "北京-首尔": 1800,
  "北京-曼谷": 2800,
  "北京-新加坡": 3200,
  "上海-广州": 900,
  "上海-深圳": 900,
  "上海-成都": 1100,
  "上海-东京": 2200,
  "上海-大阪": 2000,
  "上海-首尔": 1600,
  "上海-曼谷": 2500,
  "上海-新加坡": 3000,
  "广州-东京": 2800,
  "广州-大阪": 2500,
  "广州-曼谷": 1800,
  "广州-新加坡": 2200,
  "成都-东京": 3000,
  "成都-曼谷": 2000,
}

# Cabin class multipliers
_CABIN_MULTIPLIER = {
  "economy": 1.0,
  "premium_economy": 1.6,
  "business": 3.2,
  "first": 5.5,
}


def _get_duration(departure: str, arrival: str) -> float:
  """Lookup or estimate flight duration in hours."""
  key = f"{departure}-{arrival}"
  reverse_key = f"{arrival}-{departure}"
  if key in _ROUTE_DURATIONS:
    return _ROUTE_DURATIONS[key]
  if reverse_key in _ROUTE_DURATIONS:
    return _ROUTE_DURATIONS[reverse_key]
  # Fallback: random reasonable duration
  return round(random.uniform(2.0, 7.0), 1)


def _get_base_price(departure: str, arrival: str) -> int:
  """Lookup or estimate base ticket price (CNY)."""
  key = f"{departure}-{arrival}"
  reverse_key = f"{arrival}-{departure}"
  if key in _BASE_PRICES:
    return _BASE_PRICES[key]
  if reverse_key in _BASE_PRICES:
    return _BASE_PRICES[reverse_key]
  return random.randint(800, 4000)


def _generate_flight(
  departure: str,
  arrival: str,
  date: str,
  cabin: str = "economy",
) -> Dict[str, Any]:
  """Generate a single mock flight record."""
  airline = random.choice(_AIRLINES)
  flight_num = f"{airline['code']}{random.randint(100, 9999)}"

  dep_hour = random.randint(6, 21)
  dep_min = random.choice([0, 10, 15, 25, 30, 35, 40, 45, 50, 55])
  duration_h = _get_duration(departure, arrival)
  # Add small random variation (+-20 min)
  duration_h += random.uniform(-0.3, 0.3)
  duration_h = max(1.0, round(duration_h, 1))

  arr_hour = dep_hour + int(duration_h)
  arr_min = (dep_min + int((duration_h % 1) * 60)) % 60
  arr_hour += (dep_min + int((duration_h % 1) * 60)) // 60
  next_day = arr_hour >= 24
  arr_hour = arr_hour % 24

  base_price = _get_base_price(departure, arrival)
  # Price variation: +-30%
  price_variation = random.uniform(0.7, 1.3)
  cabin_mult = _CABIN_MULTIPLIER.get(cabin, 1.0)
  final_price = int(base_price * price_variation * cabin_mult)

  # Punctuality rate
  on_time_rate = random.randint(75, 98)

  return {
    "airline": airline["name"],
    "airline_en": airline["name_en"],
    "airline_code": airline["code"],
    "flight_number": flight_num,
    "departure_city": departure,
    "arrival_city": arrival,
    "date": date,
    "departure_time": f"{dep_hour:02d}:{dep_min:02d}",
    "arrival_time": f"{arr_hour:02d}:{arr_min:02d}" + ("+1" if next_day else ""),
    "duration_hours": duration_h,
    "duration_display": f"{int(duration_h)}h{int((duration_h % 1) * 60)}m",
    "cabin_class": cabin,
    "price": final_price,
    "currency": "CNY",
    "stops": 0 if random.random() > 0.25 else 1,
    "aircraft_type": random.choice(["B737-800", "A320neo", "B787-9", "A350-900", "B777-300ER"]),
    "on_time_rate": f"{on_time_rate}%",
    "baggage_allowance": "23kg" if cabin == "economy" else "32kg",
    "refundable": cabin != "economy",
    "seats_remaining": random.randint(1, 30),
  }


async def search_flights(
  departure: str,
  arrival: str,
  date: str,
  passengers: int = 1,
  cabin: str = "economy",
  max_results: int = 5,
) -> Dict[str, Any]:
  """Search flights between two cities.

  Args:
    departure: Departure city name (e.g. "北京", "上海")
    arrival: Arrival city name (e.g. "东京", "大阪")
    date: Travel date in YYYY-MM-DD format
    passengers: Number of passengers (default 1)
    cabin: Cabin class: economy / premium_economy / business / first
    max_results: Maximum number of results to return (3-5)

  Returns:
    Dict with flight list, search metadata, and price summary
  """
  # Try Serper real search first
  try:
    from agent.tools.serper.client import search as serper_search
    from agent.tools.serper.parsers import parse_flight_results
    query = f"{departure}到{arrival}机票 {date} {cabin}"
    raw = await serper_search(query)
    if "error" not in raw:
      flights = parse_flight_results(raw, departure, arrival, date, cabin)
      if flights:
        for f in flights:
          f["total_price"] = f["price"] * passengers
        prices = [f["price"] for f in flights]
        return {
          "success": True,
          "source": "serper",
          "query": {"departure": departure, "arrival": arrival, "date": date, "passengers": passengers, "cabin": cabin},
          "results": flights[:max_results],
          "total_count": len(flights),
          "price_summary": {"min_price": min(prices), "max_price": max(prices), "avg_price": int(sum(prices) / len(prices)), "currency": "CNY"},
        }
  except Exception:
    pass  # Fall through to mock

  try:
    # Mock fallback
    await asyncio.sleep(random.uniform(0.1, 0.3))

    num_results = min(max_results, random.randint(3, 5))
    flights = []
    for _ in range(num_results):
      flight = _generate_flight(departure, arrival, date, cabin)
      flight["total_price"] = flight["price"] * passengers
      flights.append(flight)

    # Sort by price
    flights.sort(key=lambda f: f["price"])

    prices = [f["price"] for f in flights]
    return {
      "success": True,
      "query": {
        "departure": departure,
        "arrival": arrival,
        "date": date,
        "passengers": passengers,
        "cabin": cabin,
      },
      "results": flights,
      "total_count": len(flights),
      "price_summary": {
        "min_price": min(prices),
        "max_price": max(prices),
        "avg_price": int(sum(prices) / len(prices)),
        "currency": "CNY",
      },
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
      "results": [],
      "total_count": 0,
    }
