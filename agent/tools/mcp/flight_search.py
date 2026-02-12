# Flight search MCP tool - enhanced mock with realistic route/price data
# No free flight API in China; mock quality approximates real market data.
# LLM (DeepSeek) supplements with booking advice. Future: 携程/去哪儿 commercial API.
from __future__ import annotations

import asyncio
import random
from typing import Any, Dict, List, Optional


# Airline data pool - major Chinese + common international carriers
_AIRLINES = [
  # Chinese majors
  {"code": "CA", "name": "中国国际航空", "name_en": "Air China"},
  {"code": "MU", "name": "中国东方航空", "name_en": "China Eastern"},
  {"code": "CZ", "name": "中国南方航空", "name_en": "China Southern"},
  {"code": "HU", "name": "海南航空", "name_en": "Hainan Airlines"},
  {"code": "3U", "name": "四川航空", "name_en": "Sichuan Airlines"},
  {"code": "ZH", "name": "深圳航空", "name_en": "Shenzhen Airlines"},
  {"code": "MF", "name": "厦门航空", "name_en": "Xiamen Airlines"},
  {"code": "FM", "name": "上海航空", "name_en": "Shanghai Airlines"},
  # Chinese LCC
  {"code": "9C", "name": "春秋航空", "name_en": "Spring Airlines"},
  {"code": "HO", "name": "吉祥航空", "name_en": "Juneyao Airlines"},
  {"code": "GJ", "name": "长龙航空", "name_en": "Loong Air"},
  # Japan
  {"code": "NH", "name": "全日空", "name_en": "ANA"},
  {"code": "JL", "name": "日本航空", "name_en": "JAL"},
  {"code": "MM", "name": "乐桃航空", "name_en": "Peach Aviation"},
  # Korea
  {"code": "KE", "name": "大韩航空", "name_en": "Korean Air"},
  {"code": "OZ", "name": "韩亚航空", "name_en": "Asiana Airlines"},
  {"code": "TW", "name": "德威航空", "name_en": "T'way Air"},
  # Southeast Asia
  {"code": "SQ", "name": "新加坡航空", "name_en": "Singapore Airlines"},
  {"code": "TG", "name": "泰国国际航空", "name_en": "Thai Airways"},
  {"code": "FD", "name": "泰国亚航", "name_en": "Thai AirAsia"},
  {"code": "VN", "name": "越南航空", "name_en": "Vietnam Airlines"},
  {"code": "QR", "name": "菲律宾航空", "name_en": "Philippine Airlines"},
  # Greater China
  {"code": "CX", "name": "国泰航空", "name_en": "Cathay Pacific"},
  {"code": "BR", "name": "长荣航空", "name_en": "EVA Air"},
]

# Route data: duration_h (hours) and base_price (CNY economy, market average 2025-2026)
# Sources: 携程/去哪儿 published fare ranges for reference
_ROUTES: Dict[str, Dict[str, Any]] = {
  # === Domestic China ===
  "北京-上海": {"h": 2.5, "price": 800},
  "北京-广州": {"h": 3.5, "price": 1200},
  "北京-深圳": {"h": 3.5, "price": 1200},
  "北京-成都": {"h": 3.0, "price": 1000},
  "北京-杭州": {"h": 2.5, "price": 850},
  "北京-西安": {"h": 2.5, "price": 750},
  "北京-三亚": {"h": 4.0, "price": 1500},
  "北京-昆明": {"h": 3.5, "price": 1300},
  "北京-重庆": {"h": 3.0, "price": 1100},
  "北京-南京": {"h": 2.0, "price": 700},
  "北京-厦门": {"h": 3.0, "price": 1100},
  "北京-哈尔滨": {"h": 2.0, "price": 650},
  "上海-广州": {"h": 2.5, "price": 900},
  "上海-深圳": {"h": 2.5, "price": 900},
  "上海-成都": {"h": 3.0, "price": 1100},
  "上海-三亚": {"h": 3.5, "price": 1400},
  "上海-昆明": {"h": 3.5, "price": 1200},
  "上海-西安": {"h": 2.5, "price": 900},
  "上海-重庆": {"h": 3.0, "price": 1000},
  "上海-厦门": {"h": 2.0, "price": 700},
  "广州-成都": {"h": 2.5, "price": 900},
  "广州-重庆": {"h": 2.5, "price": 850},
  "广州-三亚": {"h": 1.5, "price": 600},
  "广州-昆明": {"h": 2.0, "price": 700},
  "深圳-成都": {"h": 3.0, "price": 1000},
  "成都-三亚": {"h": 3.0, "price": 1100},
  "成都-昆明": {"h": 1.5, "price": 500},
  # === China → Japan ===
  "北京-东京": {"h": 3.5, "price": 2500},
  "北京-大阪": {"h": 3.5, "price": 2300},
  "上海-东京": {"h": 3.0, "price": 2200},
  "上海-大阪": {"h": 2.5, "price": 2000},
  "上海-名古屋": {"h": 2.5, "price": 1900},
  "广州-东京": {"h": 4.0, "price": 2800},
  "广州-大阪": {"h": 3.5, "price": 2500},
  "成都-东京": {"h": 5.0, "price": 3000},
  "成都-大阪": {"h": 4.5, "price": 2800},
  "深圳-东京": {"h": 4.0, "price": 2700},
  "杭州-东京": {"h": 3.0, "price": 2100},
  "杭州-大阪": {"h": 2.5, "price": 1900},
  # === China → Korea ===
  "北京-首尔": {"h": 2.0, "price": 1800},
  "上海-首尔": {"h": 2.0, "price": 1600},
  "广州-首尔": {"h": 3.5, "price": 2200},
  "成都-首尔": {"h": 4.0, "price": 2400},
  "青岛-首尔": {"h": 1.5, "price": 1200},
  "上海-釜山": {"h": 2.0, "price": 1500},
  # === China → SE Asia ===
  "北京-曼谷": {"h": 5.0, "price": 2800},
  "上海-曼谷": {"h": 4.5, "price": 2500},
  "广州-曼谷": {"h": 3.0, "price": 1800},
  "成都-曼谷": {"h": 3.5, "price": 2000},
  "昆明-曼谷": {"h": 2.5, "price": 1200},
  "广州-清迈": {"h": 3.0, "price": 1600},
  "北京-新加坡": {"h": 6.5, "price": 3200},
  "上海-新加坡": {"h": 5.5, "price": 3000},
  "广州-新加坡": {"h": 4.0, "price": 2200},
  "广州-河内": {"h": 2.0, "price": 1200},
  "广州-胡志明": {"h": 2.5, "price": 1500},
  "上海-河内": {"h": 3.5, "price": 1800},
  "上海-马尼拉": {"h": 4.0, "price": 2000},
  "广州-马尼拉": {"h": 3.0, "price": 1600},
  "上海-巴厘岛": {"h": 6.0, "price": 3200},
  "广州-吉隆坡": {"h": 4.0, "price": 2000},
  # === China → HK/TW ===
  "上海-香港": {"h": 2.5, "price": 1200},
  "北京-香港": {"h": 3.5, "price": 1500},
  "上海-台北": {"h": 2.0, "price": 1400},
  "北京-台北": {"h": 3.0, "price": 1800},
}

# Cabin class multipliers (relative to economy base)
_CABIN_MULTIPLIER = {
  "economy": 1.0,
  "premium_economy": 1.6,
  "business": 3.2,
  "first": 5.5,
}

# Airlines likely to operate each route region (for realistic matching)
_ROUTE_AIRLINES: Dict[str, List[str]] = {
  "domestic": ["CA", "MU", "CZ", "HU", "3U", "ZH", "MF", "FM", "9C", "HO", "GJ"],
  "japan": ["CA", "MU", "CZ", "NH", "JL", "MM", "9C", "HO"],
  "korea": ["CA", "MU", "CZ", "KE", "OZ", "TW", "9C", "HO"],
  "sea": ["CA", "MU", "CZ", "HU", "SQ", "TG", "FD", "VN", "QR"],
  "hktw": ["CA", "MU", "CZ", "CX", "BR", "HU", "HO"],
}

_AIRLINE_MAP = {a["code"]: a for a in _AIRLINES}


def _route_region(departure: str, arrival: str) -> str:
  """Determine route region for airline selection."""
  japan = {"东京", "大阪", "名古屋", "京都", "福冈", "札幌", "冲绳"}
  korea = {"首尔", "釜山", "济州"}
  sea = {"曼谷", "清迈", "新加坡", "河内", "胡志明", "马尼拉", "巴厘岛", "吉隆坡", "芭提雅"}
  hktw = {"香港", "台北", "澳门"}
  cities = {departure, arrival}
  if cities & japan:
    return "japan"
  if cities & korea:
    return "korea"
  if cities & sea:
    return "sea"
  if cities & hktw:
    return "hktw"
  return "domestic"


def _get_route_info(departure: str, arrival: str) -> Dict[str, Any]:
  """Lookup route duration and base price. Falls back to distance estimate."""
  key = f"{departure}-{arrival}"
  rev = f"{arrival}-{departure}"
  route = _ROUTES.get(key) or _ROUTES.get(rev)
  if route:
    return {"h": route["h"], "price": route["price"], "known": True}
  # Estimate for unknown routes
  return {"h": round(random.uniform(2.0, 6.0), 1), "price": random.randint(1000, 3500), "known": False}


def _pick_airline(departure: str, arrival: str) -> Dict[str, str]:
  """Pick a route-appropriate airline."""
  region = _route_region(departure, arrival)
  codes = _ROUTE_AIRLINES.get(region, _ROUTE_AIRLINES["domestic"])
  code = random.choice(codes)
  return _AIRLINE_MAP.get(code, _AIRLINES[0])


def _generate_flight(
  departure: str,
  arrival: str,
  date: str,
  cabin: str = "economy",
) -> Dict[str, Any]:
  """Generate a single realistic flight record."""
  airline = _pick_airline(departure, arrival)
  flight_num = f"{airline['code']}{random.randint(100, 9999)}"

  dep_hour = random.randint(6, 21)
  dep_min = random.choice([0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55])
  route = _get_route_info(departure, arrival)
  # ±15 min variation
  duration_h = route["h"] + random.uniform(-0.25, 0.25)
  duration_h = max(1.0, round(duration_h, 1))

  arr_hour = dep_hour + int(duration_h)
  arr_min = (dep_min + int((duration_h % 1) * 60)) % 60
  arr_hour += (dep_min + int((duration_h % 1) * 60)) // 60
  next_day = arr_hour >= 24
  arr_hour = arr_hour % 24

  # Price: base ±20% (tighter than before for realism)
  base_price = route["price"]
  price_variation = random.uniform(0.8, 1.2)
  # LCC discount
  if airline["code"] in ("9C", "HO", "MM", "FD", "TW", "GJ"):
    price_variation *= random.uniform(0.6, 0.8)
  cabin_mult = _CABIN_MULTIPLIER.get(cabin, 1.0)
  final_price = int(base_price * price_variation * cabin_mult)

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
    "stops": 0 if random.random() > 0.2 else 1,
    "aircraft_type": random.choice(["B737-800", "A320neo", "B787-9", "A350-900", "B777-300ER"]),
    "on_time_rate": f"{on_time_rate}%",
    "baggage_allowance": "23kg" if cabin == "economy" else "32kg",
    "refundable": cabin != "economy",
    "seats_remaining": random.randint(1, 30),
    "source": "estimated",
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
    # Enhanced mock fallback (realistic route-based data)
    await asyncio.sleep(random.uniform(0.05, 0.15))

    num_results = min(max_results, random.randint(3, 5))
    flights = []
    seen_airlines: set[str] = set()
    for _ in range(num_results + 3):  # generate extra, deduplicate
      flight = _generate_flight(departure, arrival, date, cabin)
      # Avoid duplicate airlines in results
      if flight["airline_code"] not in seen_airlines:
        seen_airlines.add(flight["airline_code"])
        flight["total_price"] = flight["price"] * passengers
        flights.append(flight)
      if len(flights) >= num_results:
        break

    flights.sort(key=lambda f: f["price"])

    prices = [f["price"] for f in flights]
    return {
      "success": True,
      "source": "estimated",
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
      "note": "价格为参考估算，实际以航司/OTA当日报价为准",
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
