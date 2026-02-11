# Weather helpers: Open-Meteo fallback + shared constants/converters
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

_OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
_OPEN_METEO_TIMEOUT = 5.0

# WMO weather code → Chinese condition description
WMO_CONDITIONS: Dict[int, str] = {
  0: "晴", 1: "晴", 2: "多云", 3: "阴",
  45: "雾", 48: "雾凇", 51: "小雨", 53: "中雨", 55: "大雨",
  56: "冻雨", 57: "冻雨", 61: "小雨", 63: "中雨", 65: "大雨",
  66: "冻雨", 67: "冻雨", 71: "小雪", 73: "中雪", 75: "大雪",
  77: "雪粒", 80: "阵雨", 81: "阵雨", 82: "暴雨",
  85: "阵雪", 86: "暴雪", 95: "雷暴", 96: "雷暴冰雹", 99: "雷暴冰雹",
}

# Hardcoded coords for common cities (fallback when geocoding unavailable)
CITY_COORDS: Dict[str, tuple] = {
  "东京": (35.6762, 139.6503), "大阪": (34.6937, 135.5023),
  "北京": (39.9042, 116.4074), "上海": (31.2304, 121.4737),
  "曼谷": (13.7563, 100.5018), "首尔": (37.5665, 126.9780),
  "新加坡": (1.3521, 103.8198), "京都": (35.0116, 135.7681),
  "广州": (23.1291, 113.2644), "成都": (30.5728, 104.0668),
  "西安": (34.3416, 108.9398), "杭州": (30.2741, 120.1551),
  "南京": (32.0603, 118.7969), "香港": (22.3193, 114.1694),
  "台北": (25.0330, 121.5654), "三亚": (18.2528, 109.5120),
}


def condition_to_code(condition: str) -> str:
  """Map Chinese weather condition to internal code."""
  if any(k in condition for k in ("雪", "雪粒")):
    return "snowy"
  if any(k in condition for k in ("雨", "阵雨", "暴雨", "冻雨")):
    return "rainy"
  if any(k in condition for k in ("阴", "多云", "雾")):
    return "cloudy"
  return "sunny"


def code_to_icon(code: str) -> str:
  """Map condition code to icon name."""
  return {"sunny": "sun", "cloudy": "cloud", "rainy": "rain", "snowy": "snow"}.get(code, "sun")


def qweather_to_weather(
  city: str,
  day: Dict[str, Any],
  avg_temp: float,
  get_clothing_fn: Any,
  get_travel_fn: Any,
) -> Dict[str, Any]:
  """Convert QWeather forecast day to standard weather format."""
  condition = day.get("condition", "")
  cond_code = condition_to_code(condition)
  return {
    "city": city,
    "date": day.get("date", ""),
    "condition": condition,
    "condition_code": cond_code,
    "icon": code_to_icon(cond_code),
    "temp_high": day.get("high_temp", 0),
    "temp_low": day.get("low_temp", 0),
    "humidity": day.get("humidity", 0),
    "wind_speed_kmh": day.get("wind_speed", 0),
    "wind_direction": day.get("wind_dir", ""),
    "uv_index": day.get("uv_index", 0),
    "clothing_advice": get_clothing_fn(avg_temp),
    "travel_advice": get_travel_fn(cond_code, avg_temp),
  }


async def _get_coords(city: str) -> Optional[tuple]:
  """Get coordinates for a city, trying hardcoded then Amap geocoding."""
  coords = CITY_COORDS.get(city)
  if coords:
    return coords
  try:
    from agent.tools.amap.client import geocode
    return await geocode(city)
  except Exception:
    return None


def _build_day_from_om(
  city: str,
  date_str: str,
  daily: Dict[str, Any],
  idx: int,
  get_clothing_fn: Any,
  get_travel_fn: Any,
) -> Dict[str, Any]:
  """Build a single weather day from Open-Meteo daily arrays."""
  wmo_code = _safe_idx(daily.get("weathercode", []), idx, 0)
  high = _safe_idx(daily.get("temperature_2m_max", []), idx, 20)
  low = _safe_idx(daily.get("temperature_2m_min", []), idx, 10)
  humidity = _safe_idx(daily.get("relative_humidity_2m_max", []), idx, 50)
  wind = _safe_idx(daily.get("windspeed_10m_max", []), idx, 10)
  uv = _safe_idx(daily.get("uv_index_max", []), idx, 3)
  condition = WMO_CONDITIONS.get(wmo_code, "多云")
  cond_code = condition_to_code(condition)
  avg_temp = (high + low) / 2

  return {
    "city": city,
    "date": date_str,
    "condition": condition,
    "condition_code": cond_code,
    "icon": code_to_icon(cond_code),
    "temp_high": round(high),
    "temp_low": round(low),
    "humidity": round(humidity),
    "wind_speed_kmh": round(wind),
    "wind_direction": "",
    "uv_index": round(uv),
    "clothing_advice": get_clothing_fn(avg_temp),
    "travel_advice": get_travel_fn(cond_code, avg_temp),
  }


def _safe_idx(lst: list, idx: int, default: Any) -> Any:
  return lst[idx] if idx < len(lst) else default


async def open_meteo_single_day(
  city: str,
  date: str,
  get_clothing_fn: Any,
  get_travel_fn: Any,
) -> Optional[Dict[str, Any]]:
  """Fetch a single day's weather from Open-Meteo."""
  coords = await _get_coords(city)
  if not coords:
    return None

  try:
    async with httpx.AsyncClient(timeout=_OPEN_METEO_TIMEOUT) as client:
      resp = await client.get(_OPEN_METEO_URL, params={
        "latitude": coords[0],
        "longitude": coords[1],
        "daily": "temperature_2m_max,temperature_2m_min,weathercode,relative_humidity_2m_max,windspeed_10m_max,uv_index_max",
        "start_date": date,
        "end_date": date,
        "timezone": "auto",
      })
      resp.raise_for_status()
      data = resp.json()

    daily = data.get("daily", {})
    if not daily.get("time"):
      return None

    return _build_day_from_om(city, date, daily, 0, get_clothing_fn, get_travel_fn)
  except Exception as exc:
    logger.debug("Open-Meteo single day error: %s", exc)
    return None


async def open_meteo_multi_day(
  city: str,
  start_date: str,
  days: int,
  get_clothing_fn: Any,
  get_travel_fn: Any,
) -> Optional[List[Dict[str, Any]]]:
  """Fetch multi-day forecast from Open-Meteo."""
  coords = await _get_coords(city)
  if not coords:
    return None

  try:
    base = datetime.strptime(start_date, "%Y-%m-%d")
  except ValueError:
    base = datetime.now()
  end_date = (base + timedelta(days=days - 1)).strftime("%Y-%m-%d")

  try:
    async with httpx.AsyncClient(timeout=_OPEN_METEO_TIMEOUT) as client:
      resp = await client.get(_OPEN_METEO_URL, params={
        "latitude": coords[0],
        "longitude": coords[1],
        "daily": "temperature_2m_max,temperature_2m_min,weathercode,relative_humidity_2m_max,windspeed_10m_max,uv_index_max",
        "start_date": start_date,
        "end_date": end_date,
        "timezone": "auto",
      })
      resp.raise_for_status()
      data = resp.json()

    daily = data.get("daily", {})
    times = daily.get("time", [])
    if not times:
      return None

    return [
      _build_day_from_om(city, date_str, daily, i, get_clothing_fn, get_travel_fn)
      for i, date_str in enumerate(times)
    ]
  except Exception as exc:
    logger.debug("Open-Meteo multi-day error: %s", exc)
    return None
