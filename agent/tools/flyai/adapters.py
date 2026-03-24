# Convert FlyAI raw responses to TravelMind standard tool formats
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


def _parse_price(price_str: Optional[str]) -> int:
  """Extract numeric price from strings like '¥400.0' or '618'."""
  if not price_str:
    return 0
  nums = re.findall(r"[\d.]+", str(price_str))
  if nums:
    return int(float(nums[0]))
  return 0


def _parse_duration_minutes(dur_str: Optional[str]) -> float:
  """Parse '140分钟', '195', or '2h30m' to hours."""
  if not dur_str:
    return 0
  s = str(dur_str).strip()
  # Pure number = minutes
  if re.fullmatch(r"\d+", s):
    return int(s) / 60
  mins = re.findall(r"(\d+)\s*分钟", s)
  if mins:
    return int(mins[0]) / 60
  hours = re.findall(r"(\d+)\s*[hH小时]", s)
  extra_mins = re.findall(r"(\d+)\s*[mM分]", s)
  h = int(hours[0]) if hours else 0
  m = int(extra_mins[0]) if extra_mins else 0
  return h + m / 60 if (h or m) else 0


def _star_to_int(star_str: Optional[str]) -> int:
  """Convert star description to numeric rating."""
  if not star_str:
    return 3
  mapping = {"豪华型": 5, "高档型": 4, "舒适型": 3, "经济型": 2}
  for key, val in mapping.items():
    if key in str(star_str):
      return val
  nums = re.findall(r"(\d)", str(star_str))
  if nums:
    return min(5, int(nums[0]))
  return 3


def _estimate_flight_price(duration_h: float, cabin: str = "economy") -> int:
  """Estimate flight price from duration when API returns no price."""
  # ~400 CNY/h for economy domestic, adjusted by cabin
  base = max(200, int(duration_h * 400))
  cabin_mult = {"economy": 1.0, "premium_economy": 1.6, "business": 3.2, "first": 5.5}
  return int(base * cabin_mult.get(cabin, 1.0))


def _estimate_hotel_price(stars: int) -> int:
  """Estimate hotel price from star rating when API returns no price."""
  base = {5: 1800, 4: 700, 3: 350, 2: 200, 1: 100}
  return base.get(stars, 500)


def convert_flights(
  raw_items: List[Dict[str, Any]],
  departure: str,
  arrival: str,
  date: str,
  cabin: str = "economy",
  passengers: int = 1,
) -> List[Dict[str, Any]]:
  """Convert FlyAI flight results to TravelMind standard format."""
  results = []
  for item in raw_items:
    try:
      journeys = item.get("journeys", [])
      if not journeys:
        continue
      journey = journeys[0]
      segments = journey.get("segments", [])
      if not segments:
        continue
      seg = segments[0]

      price = _parse_price(item.get("adultPrice"))
      duration_h = _parse_duration_minutes(item.get("totalDuration") or journey.get("totalDuration"))
      if duration_h == 0:
        duration_h = _parse_duration_minutes(seg.get("duration"))

      dep_time = ""
      arr_time = ""
      dep_dt = seg.get("depDateTime", "")
      arr_dt = seg.get("arrDateTime", "")
      if dep_dt and len(dep_dt) >= 16:
        dep_time = dep_dt[11:16]
      if arr_dt and len(arr_dt) >= 16:
        arr_time = arr_dt[11:16]

      # Check if arrival is next day
      if dep_dt and arr_dt and dep_dt[:10] != arr_dt[:10]:
        arr_time += "+1"

      flight_number = seg.get("marketingTransportNo", "")
      airline_name = seg.get("marketingTransportName", "")
      airline_code = flight_number[:2] if len(flight_number) >= 2 else ""

      stops = 0
      if len(segments) > 1:
        stops = len(segments) - 1
      journey_type = journey.get("journeyType", "")
      if "中转" in journey_type:
        stops = max(stops, 1)

      # Estimate price when API returns 0 (experience key limitation)
      if price == 0 and duration_h > 0:
        price = _estimate_flight_price(duration_h, cabin)

      results.append({
        "airline": airline_name,
        "airline_en": "",
        "airline_code": airline_code,
        "flight_number": flight_number,
        "departure_city": seg.get("depCityName", departure),
        "arrival_city": seg.get("arrCityName", arrival),
        "date": dep_dt[:10] if dep_dt else date,
        "departure_time": dep_time,
        "arrival_time": arr_time,
        "departure_airport": seg.get("depStationName", ""),
        "arrival_airport": seg.get("arrStationName", ""),
        "departure_terminal": seg.get("depTerm", ""),
        "arrival_terminal": seg.get("arrTerm", ""),
        "duration_hours": round(duration_h, 1),
        "duration_display": f"{int(duration_h)}h{int((duration_h % 1) * 60)}m",
        "cabin_class": seg.get("seatClassName", cabin),
        "price": price,
        "total_price": price * passengers,
        "currency": "CNY",
        "stops": stops,
        "seats_remaining": 0,
        "source": "flyai",
        "booking_url": item.get("jumpUrl", ""),
      })
    except Exception:
      continue
  return results


def convert_hotels(
  raw_items: List[Dict[str, Any]],
  city: str,
  checkin: str,
  checkout: str,
) -> List[Dict[str, Any]]:
  """Convert FlyAI hotel results to TravelMind standard format."""
  results = []
  for item in raw_items:
    try:
      price = _parse_price(item.get("price"))
      score = 0.0
      try:
        score = float(item.get("score", 0))
      except (ValueError, TypeError):
        pass
      stars = _star_to_int(item.get("star"))

      lat = 0.0
      lng = 0.0
      try:
        lat = float(item.get("latitude", 0))
        lng = float(item.get("longitude", 0))
      except (ValueError, TypeError):
        pass

      # Estimate price when API returns 0 (experience key limitation)
      if price == 0:
        price = _estimate_hotel_price(stars)

      results.append({
        "name": item.get("name", ""),
        "name_en": "",
        "stars": stars,
        "rating": score,
        "review_count": 0,
        "area": item.get("interestsPoi", ""),
        "address": item.get("address", ""),
        "brand": item.get("brandName", ""),
        "price_per_night": price,
        "currency": "CNY",
        "checkin": checkin,
        "checkout": checkout,
        "facilities": [],
        "room_types": [],
        "breakfast_included": False,
        "free_cancellation": True,
        "distance_to_center": "",
        "image_url": item.get("mainPic", ""),
        "booking_url": item.get("detailUrl", ""),
        "source": "flyai",
      })
      if lat and lng:
        results[-1]["coordinates"] = {"lat": lat, "lng": lng}
    except Exception:
      continue
  return results


# Map TravelMind categories to FlyAI POI categories
_CATEGORY_TO_FLYAI: Dict[str, str] = {
  "scenic": "自然风光",
  "museum": "博物馆",
  "park": "公园乐园",
  "activity": "主题乐园",
  "shopping": "市集",
}


def get_flyai_poi_category(category: Optional[str]) -> Optional[str]:
  """Map TravelMind category to FlyAI category string."""
  if not category:
    return None
  return _CATEGORY_TO_FLYAI.get(category)


def convert_pois(
  raw_items: List[Dict[str, Any]],
  city: str,
) -> List[Dict[str, Any]]:
  """Convert FlyAI POI results to TravelMind standard format."""
  results = []
  for item in raw_items:
    try:
      ticket_info = item.get("ticketInfo") or {}
      price = _parse_price(ticket_info.get("price"))
      free_status = item.get("freePoiStatus", "")
      if free_status == "FREE":
        price = 0

      results.append({
        "name": item.get("name", ""),
        "name_en": "",
        "category": "scenic",
        "rating": 0,
        "price": price,
        "hours": "",
        "desc": item.get("address", ""),
        "city": city,
        "popularity": 0,
        "recommended_duration": "2h",
        "best_time": "全天皆宜",
        "tips": [],
        "image_url": item.get("mainPic", ""),
        "booking_url": item.get("jumpUrl", ""),
        "ticket_name": ticket_info.get("ticketName", ""),
        "source": "flyai",
      })
    except Exception:
      continue
  return results
