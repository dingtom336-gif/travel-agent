# QWeather (和风天气) API client
# Docs: https://dev.qweather.com/docs/api/
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from agent.config.settings import get_settings

logger = logging.getLogger(__name__)

_GEO_URL = "https://geoapi.qweather.com/v2/city/lookup"
_WEATHER_URL = "https://devapi.qweather.com/v7/weather"
_TIMEOUT = 3.0


def _get_key() -> str:
  return get_settings().QWEATHER_API_KEY


async def lookup_city(name: str) -> Optional[str]:
  """Look up a city's QWeather location ID.

  Args:
    name: City name (e.g. "东京", "北京")

  Returns:
    Location ID string (e.g. "101010100") or None.
  """
  key = _get_key()
  if not key:
    return None

  try:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
      resp = await client.get(
        _GEO_URL,
        params={"key": key, "location": name, "number": 1},
      )
      resp.raise_for_status()
      data = resp.json()

    if data.get("code") != "200" or not data.get("location"):
      logger.debug("QWeather city lookup no result for %s", name)
      return None

    location_id = data["location"][0].get("id")
    logger.info("QWeather city lookup: %s → %s", name, location_id)
    return location_id
  except Exception as exc:
    logger.warning("QWeather city lookup error: %s", exc)
    return None


async def get_forecast(
  location_id: str,
  days: int = 3,
) -> Optional[Dict[str, Any]]:
  """Get weather forecast from QWeather.

  Args:
    location_id: QWeather location ID from lookup_city()
    days: 3 or 7 (free tier supports 3-day)

  Returns:
    Dict with daily forecast list or None.
  """
  key = _get_key()
  if not key:
    return None

  # Free tier: 3d only. 7d requires paid plan.
  endpoint = f"{_WEATHER_URL}/{'3d' if days <= 3 else '7d'}"

  try:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
      resp = await client.get(
        endpoint,
        params={"key": key, "location": location_id},
      )
      resp.raise_for_status()
      data = resp.json()

    if data.get("code") != "200" or not data.get("daily"):
      logger.debug("QWeather forecast failed: code=%s", data.get("code"))
      return None

    forecasts: List[Dict[str, Any]] = []
    for day in data["daily"][:days]:
      forecasts.append({
        "date": day.get("fxDate", ""),
        "high_temp": _safe_int(day.get("tempMax")),
        "low_temp": _safe_int(day.get("tempMin")),
        "condition": day.get("textDay", ""),
        "condition_night": day.get("textNight", ""),
        "humidity": _safe_int(day.get("humidity")),
        "wind_dir": day.get("windDirDay", ""),
        "wind_scale": day.get("windScaleDay", ""),
        "wind_speed": _safe_int(day.get("windSpeedDay")),
        "uv_index": _safe_int(day.get("uvIndex")),
        "precip": _safe_float(day.get("precip")),
        "vis": _safe_int(day.get("vis")),
      })

    logger.info("QWeather forecast: %s → %d days", location_id, len(forecasts))
    return {"daily": forecasts}
  except Exception as exc:
    logger.warning("QWeather forecast error: %s", exc)
    return None


def _safe_int(val: Any) -> int:
  """Safely convert to int, default 0."""
  try:
    return int(val) if val else 0
  except (ValueError, TypeError):
    return 0


def _safe_float(val: Any) -> float:
  """Safely convert to float, default 0."""
  try:
    return float(val) if val else 0.0
  except (ValueError, TypeError):
    return 0.0
