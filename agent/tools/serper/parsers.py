# Parsers to extract structured travel data from Serper API results
from __future__ import annotations

import re
from typing import Any, Dict, List


_AIRLINE_NAMES = [
  "国航", "东航", "南航", "海航", "川航", "深航", "厦航", "上航",
  "春秋", "吉祥", "长龙", "全日空", "日航", "乐桃",
  "大韩", "韩亚", "德威", "新航", "泰航", "亚航",
  "越航", "菲航", "国泰", "长荣", "ANA", "JAL",
]

# Flight number pattern: 2-letter code + 3-4 digits
_FLIGHT_NUM_RE = re.compile(r"\b([A-Z\d]{2})\s?(\d{3,4})\b")


def parse_flight_results(
  data: Dict[str, Any],
  departure: str,
  arrival: str,
  date: str,
  cabin: str = "economy",
) -> List[Dict[str, Any]]:
  """Extract flight info from Serper search results.

  Parses answerBox, knowledgeGraph, and organic results for flight data.
  Returns a list in the same format as the flight_search tool.
  """
  flights: List[Dict[str, Any]] = []

  # 1. Try answerBox / knowledgeGraph first (more structured)
  for key in ("answerBox", "knowledgeGraph"):
    box = data.get(key, {})
    if not box:
      continue
    text = f"{box.get('title', '')} {box.get('snippet', '')} {box.get('answer', '')}"
    flight = _extract_flight_from_text(text, departure, arrival, date, cabin)
    if flight:
      flight["source"] = "serper"
      flights.append(flight)

  # 2. Organic results
  organic = data.get("organic", [])
  for item in organic[:8]:
    title = item.get("title", "")
    snippet = item.get("snippet", "")
    text = f"{title} {snippet}"
    flight = _extract_flight_from_text(text, departure, arrival, date, cabin)
    if flight:
      flight["source"] = item.get("link", "serper")
      flights.append(flight)

  flights.sort(key=lambda f: (f["price"] == 0, f["price"]))
  return flights[:5]


def _extract_flight_from_text(
  text: str,
  departure: str,
  arrival: str,
  date: str,
  cabin: str,
) -> Dict[str, Any] | None:
  """Try to extract a single flight record from text. Returns None if not flight-related."""
  # Must contain at least one flight-related keyword
  if not any(kw in text for kw in ["航", "机票", "飞", "flight", "票价", "直飞", "经停"]):
    return None

  # Price (optional now - keep result even without price)
  price = 0
  price_match = re.search(r"[¥￥]?\s*(\d{3,5})\s*(?:元|起|CNY|RMB)?", text)
  if price_match:
    price = int(price_match.group(1))

  # Airline
  airline = ""
  for name in _AIRLINE_NAMES:
    if name in text:
      airline = name
      break
  if not airline:
    airline_match = re.search(r"([\u4e00-\u9fff]{2,6}航空?)", text)
    airline = airline_match.group(1) if airline_match else ""

  # Flight number
  flight_number = ""
  fn_match = _FLIGHT_NUM_RE.search(text)
  if fn_match:
    flight_number = f"{fn_match.group(1)}{fn_match.group(2)}"

  # Time
  time_match = re.search(r"(\d{1,2}:\d{2})\s*[-–→]\s*(\d{1,2}:\d{2})", text)
  dep_time = time_match.group(1) if time_match else ""
  arr_time = time_match.group(2) if time_match else ""

  # Duration
  dur_match = re.search(r"(\d+)\s*[hH小时]\s*(\d+)?\s*[mM分]?", text)
  if dur_match:
    h = int(dur_match.group(1))
    m = int(dur_match.group(2) or 0)
    duration_h = round(h + m / 60, 1)
  else:
    duration_h = 0

  # Stops
  stops = 0
  if any(kw in text for kw in ["经停", "中转", "转机", "1 stop"]):
    stops = 1

  return {
    "airline": airline or "航空公司",
    "flight_number": flight_number,
    "departure_city": departure,
    "arrival_city": arrival,
    "date": date,
    "departure_time": dep_time,
    "arrival_time": arr_time,
    "duration_hours": duration_h,
    "duration_display": f"{int(duration_h)}h{int((duration_h % 1) * 60)}m" if duration_h else "",
    "cabin_class": cabin,
    "price": price,
    "currency": "CNY",
    "stops": stops,
  }


def parse_hotel_results(
  data: Dict[str, Any],
  city: str,
  checkin: str,
  checkout: str,
) -> List[Dict[str, Any]]:
  """Extract hotel info from Serper search/places results.

  Handles both organic search results and places API results.
  """
  hotels: List[Dict[str, Any]] = []

  # Try places results first
  places = data.get("places", [])
  for place in places[:6]:
    name = place.get("title", "")
    rating = place.get("rating", 0)
    if not rating:
      continue

    # Extract price from description or cid
    price = 0
    price_str = place.get("price", "")
    if price_str:
      pm = re.search(r"(\d+)", str(price_str))
      price = int(pm.group(1)) if pm else 0

    hotels.append({
      "name": name,
      "stars": min(5, max(3, round(rating))),
      "rating": round(rating, 1),
      "area": place.get("address", city),
      "price_per_night": price or 800,
      "currency": "CNY",
      "checkin": checkin,
      "checkout": checkout,
      "facilities": ["免费WiFi"],
      "source": place.get("cid", ""),
    })

  # Also parse organic results
  organic = data.get("organic", [])
  for item in organic[:6]:
    title = item.get("title", "")
    snippet = item.get("snippet", "")
    text = f"{title} {snippet}"

    # Skip non-hotel results
    if not any(kw in text for kw in ["酒店", "hotel", "度假", "民宿", "旅馆"]):
      continue

    price_match = re.search(r"[¥￥]?\s*(\d{2,5})\s*(?:元|/晚|起)?", text)
    price = int(price_match.group(1)) if price_match else 0

    rating_match = re.search(r"(\d\.\d)\s*分?", text)
    rating = float(rating_match.group(1)) if rating_match else 4.0

    hotels.append({
      "name": title[:50],
      "stars": min(5, max(3, round(rating))),
      "rating": round(rating, 1),
      "area": city,
      "price_per_night": price or 800,
      "currency": "CNY",
      "checkin": checkin,
      "checkout": checkout,
      "facilities": ["免费WiFi"],
      "source": item.get("link", ""),
    })

  # Deduplicate by name
  seen: set[str] = set()
  unique: List[Dict[str, Any]] = []
  for h in hotels:
    if h["name"] not in seen:
      seen.add(h["name"])
      unique.append(h)
  return unique[:5]


def parse_poi_results(
  data: Dict[str, Any],
  city: str,
) -> List[Dict[str, Any]]:
  """Extract POI info from Serper places/search results."""
  pois: List[Dict[str, Any]] = []

  # Places API results
  places = data.get("places", [])
  for place in places[:10]:
    name = place.get("title", "")
    rating = place.get("rating", 0)
    if not name:
      continue

    pois.append({
      "name": name,
      "category": _guess_poi_category(name, place.get("category", "")),
      "rating": round(rating, 1) if rating else 4.0,
      "price": 0,
      "hours": place.get("hours", ""),
      "desc": place.get("description", "") or place.get("address", ""),
      "city": city,
      "coordinates": {
        "lat": place.get("latitude", 0),
        "lng": place.get("longitude", 0),
      },
      "source": place.get("cid", ""),
    })

  # Organic results as fallback
  if len(pois) < 3:
    organic = data.get("organic", [])
    for item in organic[:8]:
      title = item.get("title", "")
      snippet = item.get("snippet", "")
      pois.append({
        "name": title[:40],
        "category": _guess_poi_category(title, snippet),
        "rating": 4.0,
        "price": 0,
        "hours": "",
        "desc": snippet[:100] if snippet else "",
        "city": city,
        "source": item.get("link", ""),
      })

  return pois[:10]


def parse_weather_results(
  data: Dict[str, Any],
  city: str,
  date: str,
) -> Dict[str, Any] | None:
  """Extract weather info from Serper knowledge graph / answer box."""
  # Check knowledge graph
  kg = data.get("knowledgeGraph", {})
  answer_box = data.get("answerBox", {})

  # Try answer box first (often has weather data)
  if answer_box:
    snippet = answer_box.get("snippet", "") or answer_box.get("answer", "")
    temp_match = re.search(r"(\d+)\s*°?\s*[Cc]", snippet)
    if temp_match:
      temp = int(temp_match.group(1))
      condition = _extract_weather_condition(snippet)
      return {
        "city": city,
        "date": date,
        "condition": condition,
        "temp_high": temp + 3,
        "temp_low": temp - 3,
        "humidity": 60,
        "source": "serper",
      }

  # Try organic results
  for item in data.get("organic", [])[:5]:
    snippet = item.get("snippet", "")
    temp_match = re.search(r"(\d+)\s*[-~]\s*(\d+)\s*°?\s*[Cc]?", snippet)
    if temp_match:
      low = int(temp_match.group(1))
      high = int(temp_match.group(2))
      condition = _extract_weather_condition(snippet)
      return {
        "city": city,
        "date": date,
        "condition": condition,
        "temp_high": high,
        "temp_low": low,
        "humidity": 60,
        "source": "serper",
      }

  return None


def _guess_poi_category(name: str, desc: str = "") -> str:
  """Guess POI category from name and description."""
  text = f"{name} {desc}"
  if any(kw in text for kw in ["餐", "食", "饭", "面", "菜", "料理", "cafe", "restaurant"]):
    return "restaurant"
  if any(kw in text for kw in ["商场", "购物", "百货", "市场", "mall", "shop"]):
    return "shopping"
  if any(kw in text for kw in ["博物", "美术", "museum", "gallery"]):
    return "museum"
  if any(kw in text for kw in ["公园", "花园", "garden", "park"]):
    return "park"
  if any(kw in text for kw in ["乐园", "体验", "活动", "adventure"]):
    return "activity"
  return "scenic"


def _extract_weather_condition(text: str) -> str:
  """Extract weather condition from text."""
  if any(kw in text for kw in ["雪", "snow"]):
    return "雪"
  if any(kw in text for kw in ["雨", "rain", "shower"]):
    return "雨"
  if any(kw in text for kw in ["多云", "阴", "cloud", "overcast"]):
    return "多云"
  return "晴"
