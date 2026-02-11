# Parsers to extract structured travel data from Serper API results
from __future__ import annotations

import re
from typing import Any, Dict, List


def parse_flight_results(
  data: Dict[str, Any],
  departure: str,
  arrival: str,
  date: str,
  cabin: str = "economy",
) -> List[Dict[str, Any]]:
  """Extract flight info from Serper search results.

  Parses organic results and knowledge graph for flight data.
  Returns a list in the same format as the mock flight_search tool.
  """
  flights: List[Dict[str, Any]] = []
  organic = data.get("organic", [])

  for item in organic[:8]:
    title = item.get("title", "")
    snippet = item.get("snippet", "")
    text = f"{title} {snippet}"

    # Try to extract price
    price_match = re.search(r"[¥￥]?\s*(\d{3,5})\s*(?:元|起|CNY)?", text)
    if not price_match:
      continue

    price = int(price_match.group(1))

    # Try to extract airline
    airline = ""
    for name in ["国航", "东航", "南航", "海航", "川航", "全日空", "日航", "春秋", "吉祥"]:
      if name in text:
        airline = name
        break
    if not airline:
      airline_match = re.search(r"([\u4e00-\u9fff]{2,6}航空?)", text)
      airline = airline_match.group(1) if airline_match else "航空公司"

    # Try to extract time
    time_match = re.search(r"(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})", text)
    dep_time = time_match.group(1) if time_match else "08:00"
    arr_time = time_match.group(2) if time_match else "11:00"

    # Duration
    dur_match = re.search(r"(\d+)[hH小时]\s*(\d+)?", text)
    if dur_match:
      h = int(dur_match.group(1))
      m = int(dur_match.group(2) or 0)
      duration_h = round(h + m / 60, 1)
    else:
      duration_h = 3.0

    flights.append({
      "airline": airline,
      "flight_number": "",
      "departure_city": departure,
      "arrival_city": arrival,
      "date": date,
      "departure_time": dep_time,
      "arrival_time": arr_time,
      "duration_hours": duration_h,
      "duration_display": f"{int(duration_h)}h{int((duration_h % 1) * 60)}m",
      "cabin_class": cabin,
      "price": price,
      "currency": "CNY",
      "stops": 0,
      "source": item.get("link", ""),
    })

  flights.sort(key=lambda f: f["price"])
  return flights[:5]


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
