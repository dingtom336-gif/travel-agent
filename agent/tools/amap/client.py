# Amap (高德地图) Web Service API client
# Docs: https://lbs.amap.com/api/webservice/summary
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx

from agent.config.settings import get_settings

logger = logging.getLogger(__name__)

_BASE_URL = "https://restapi.amap.com/v3"
_TIMEOUT = 3.0


def _get_key() -> str:
  return get_settings().AMAP_API_KEY


async def geocode(address: str) -> Optional[Tuple[float, float]]:
  """Geocode an address to (lat, lng) via Amap API.

  Amap returns location as "lng,lat" string.
  """
  key = _get_key()
  if not key:
    return None

  try:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
      resp = await client.get(
        f"{_BASE_URL}/geocode/geo",
        params={"key": key, "address": address, "output": "json"},
      )
      resp.raise_for_status()
      data = resp.json()

    if data.get("status") != "1" or not data.get("geocodes"):
      logger.debug("Amap geocode no result for %s", address)
      return None

    location_str = data["geocodes"][0].get("location", "")
    if "," not in location_str:
      return None

    lng_s, lat_s = location_str.split(",")
    return (float(lat_s), float(lng_s))
  except Exception as exc:
    logger.warning("Amap geocode error: %s", exc)
    return None


async def search_poi(
  city: str,
  keywords: str,
  types: str = "",
  page_size: int = 10,
) -> List[Dict[str, Any]]:
  """Search POIs via Amap Place Text API.

  Args:
    city: City name (e.g. "东京", "北京")
    keywords: Search keywords (e.g. "景点", "酒店")
    types: Amap POI type codes (e.g. "100000" for hotels)
    page_size: Max results to return

  Returns:
    List of POI dicts with name, location, rating, etc.
  """
  key = _get_key()
  if not key:
    return []

  try:
    params: Dict[str, Any] = {
      "key": key,
      "keywords": keywords,
      "city": city,
      "extensions": "all",
      "offset": page_size,
      "page": 1,
      "output": "json",
    }
    if types:
      params["types"] = types

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
      resp = await client.get(f"{_BASE_URL}/place/text", params=params)
      resp.raise_for_status()
      data = resp.json()

    if data.get("status") != "1":
      logger.debug("Amap POI search failed: %s", data.get("info"))
      return []

    pois = data.get("pois", [])
    results: List[Dict[str, Any]] = []
    for poi in pois[:page_size]:
      location_str = poi.get("location", "")
      coords = _parse_location(location_str)

      result: Dict[str, Any] = {
        "name": poi.get("name", ""),
        "address": poi.get("address", ""),
        "type": poi.get("type", ""),
        "business_area": poi.get("business_area", ""),
        "tel": poi.get("tel", ""),
        "rating": _safe_float(poi.get("biz_ext", {}).get("rating", "0")),
        "cost": _safe_float(poi.get("biz_ext", {}).get("cost", "0")),
      }
      if coords:
        result["coordinates"] = {"lat": coords[0], "lng": coords[1]}

      # Extract photo URL if available
      photos = poi.get("photos", [])
      if photos and isinstance(photos, list) and photos[0].get("url"):
        result["image_url"] = photos[0]["url"]

      # Opening hours from biz_ext
      opentime = poi.get("biz_ext", {}).get("opentime", "")
      if opentime:
        result["opentime"] = opentime

      results.append(result)

    logger.info("Amap POI search: %s in %s → %d results", keywords, city, len(results))
    return results
  except Exception as exc:
    logger.warning("Amap POI search error: %s", exc)
    return []


async def plan_route(
  origin: Tuple[float, float],
  destination: Tuple[float, float],
  mode: str = "driving",
) -> Optional[Dict[str, Any]]:
  """Plan a route between two points via Amap Direction API.

  Args:
    origin: (lat, lng) of start point
    destination: (lat, lng) of end point
    mode: "driving", "walking", or "transit"

  Returns:
    Dict with distance (meters), duration (seconds), steps.
  """
  key = _get_key()
  if not key:
    return None

  # Amap expects "lng,lat" format
  origin_str = f"{origin[1]},{origin[0]}"
  dest_str = f"{destination[1]},{destination[0]}"

  try:
    endpoint = f"{_BASE_URL}/direction/{mode}"
    params: Dict[str, Any] = {
      "key": key,
      "origin": origin_str,
      "destination": dest_str,
      "output": "json",
    }
    if mode == "transit":
      params["city"] = "auto"

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
      resp = await client.get(endpoint, params=params)
      resp.raise_for_status()
      data = resp.json()

    if data.get("status") != "1":
      logger.debug("Amap route plan failed: %s", data.get("info"))
      return None

    route = data.get("route", {})
    paths = route.get("paths", [])
    if not paths:
      return None

    path = paths[0]
    return {
      "distance": int(path.get("distance", 0)),
      "duration": int(path.get("duration", 0)),
      "strategy": path.get("strategy", ""),
    }
  except Exception as exc:
    logger.warning("Amap route plan error: %s", exc)
    return None


def _parse_location(location_str: str) -> Optional[Tuple[float, float]]:
  """Parse Amap "lng,lat" string to (lat, lng) tuple."""
  if not location_str or "," not in location_str:
    return None
  try:
    lng_s, lat_s = location_str.split(",")
    return (float(lat_s), float(lng_s))
  except (ValueError, TypeError):
    return None


def _safe_float(val: Any) -> float:
  """Safely convert a value to float, default 0."""
  try:
    return float(val) if val else 0.0
  except (ValueError, TypeError):
    return 0.0
