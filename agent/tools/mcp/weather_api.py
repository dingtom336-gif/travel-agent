# Weather API MCP tool - QWeather (primary) + Open-Meteo (fallback) + mock
# Three-tier fallback: QWeather → Open-Meteo → mock data
from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from agent.tools.mcp.weather_helpers import (
  open_meteo_multi_day,
  open_meteo_single_day,
  qweather_to_weather,
)
from agent.tools.qweather.client import get_forecast as qw_get_forecast
from agent.tools.qweather.client import lookup_city as qw_lookup_city

logger = logging.getLogger(__name__)


# City climate profiles: (avg_temp_low, avg_temp_high, humidity, conditions_weight)
_CLIMATE_PROFILES: Dict[str, Dict[str, Any]] = {
  "东京": {
    "spring": {"low": 10, "high": 20, "humidity": 60, "conditions": {"sunny": 0.4, "cloudy": 0.35, "rainy": 0.2, "snowy": 0.05}},
    "summer": {"low": 23, "high": 33, "humidity": 75, "conditions": {"sunny": 0.4, "cloudy": 0.3, "rainy": 0.3, "snowy": 0}},
    "autumn": {"low": 12, "high": 22, "humidity": 55, "conditions": {"sunny": 0.5, "cloudy": 0.3, "rainy": 0.2, "snowy": 0}},
    "winter": {"low": 1, "high": 10, "humidity": 45, "conditions": {"sunny": 0.5, "cloudy": 0.3, "rainy": 0.1, "snowy": 0.1}},
  },
  "大阪": {
    "spring": {"low": 10, "high": 20, "humidity": 58, "conditions": {"sunny": 0.4, "cloudy": 0.35, "rainy": 0.2, "snowy": 0.05}},
    "summer": {"low": 25, "high": 34, "humidity": 70, "conditions": {"sunny": 0.35, "cloudy": 0.35, "rainy": 0.3, "snowy": 0}},
    "autumn": {"low": 13, "high": 23, "humidity": 55, "conditions": {"sunny": 0.5, "cloudy": 0.3, "rainy": 0.2, "snowy": 0}},
    "winter": {"low": 2, "high": 10, "humidity": 50, "conditions": {"sunny": 0.45, "cloudy": 0.35, "rainy": 0.1, "snowy": 0.1}},
  },
  "北京": {
    "spring": {"low": 6, "high": 22, "humidity": 35, "conditions": {"sunny": 0.5, "cloudy": 0.3, "rainy": 0.15, "snowy": 0.05}},
    "summer": {"low": 22, "high": 35, "humidity": 65, "conditions": {"sunny": 0.4, "cloudy": 0.3, "rainy": 0.3, "snowy": 0}},
    "autumn": {"low": 5, "high": 20, "humidity": 45, "conditions": {"sunny": 0.6, "cloudy": 0.25, "rainy": 0.15, "snowy": 0}},
    "winter": {"low": -8, "high": 3, "humidity": 35, "conditions": {"sunny": 0.5, "cloudy": 0.3, "rainy": 0.05, "snowy": 0.15}},
  },
  "上海": {
    "spring": {"low": 10, "high": 20, "humidity": 65, "conditions": {"sunny": 0.35, "cloudy": 0.35, "rainy": 0.25, "snowy": 0.05}},
    "summer": {"low": 25, "high": 35, "humidity": 80, "conditions": {"sunny": 0.35, "cloudy": 0.3, "rainy": 0.35, "snowy": 0}},
    "autumn": {"low": 12, "high": 23, "humidity": 60, "conditions": {"sunny": 0.5, "cloudy": 0.3, "rainy": 0.2, "snowy": 0}},
    "winter": {"low": 0, "high": 8, "humidity": 55, "conditions": {"sunny": 0.4, "cloudy": 0.35, "rainy": 0.15, "snowy": 0.1}},
  },
  "曼谷": {
    "spring": {"low": 26, "high": 36, "humidity": 65, "conditions": {"sunny": 0.5, "cloudy": 0.3, "rainy": 0.2, "snowy": 0}},
    "summer": {"low": 26, "high": 34, "humidity": 80, "conditions": {"sunny": 0.25, "cloudy": 0.3, "rainy": 0.45, "snowy": 0}},
    "autumn": {"low": 25, "high": 33, "humidity": 75, "conditions": {"sunny": 0.3, "cloudy": 0.35, "rainy": 0.35, "snowy": 0}},
    "winter": {"low": 22, "high": 33, "humidity": 55, "conditions": {"sunny": 0.6, "cloudy": 0.25, "rainy": 0.15, "snowy": 0}},
  },
  "首尔": {
    "spring": {"low": 5, "high": 18, "humidity": 50, "conditions": {"sunny": 0.45, "cloudy": 0.35, "rainy": 0.15, "snowy": 0.05}},
    "summer": {"low": 22, "high": 32, "humidity": 75, "conditions": {"sunny": 0.3, "cloudy": 0.3, "rainy": 0.4, "snowy": 0}},
    "autumn": {"low": 8, "high": 20, "humidity": 50, "conditions": {"sunny": 0.55, "cloudy": 0.3, "rainy": 0.15, "snowy": 0}},
    "winter": {"low": -8, "high": 2, "humidity": 45, "conditions": {"sunny": 0.45, "cloudy": 0.3, "rainy": 0.05, "snowy": 0.2}},
  },
  "新加坡": {
    "spring": {"low": 25, "high": 32, "humidity": 80, "conditions": {"sunny": 0.35, "cloudy": 0.35, "rainy": 0.3, "snowy": 0}},
    "summer": {"low": 25, "high": 32, "humidity": 80, "conditions": {"sunny": 0.35, "cloudy": 0.35, "rainy": 0.3, "snowy": 0}},
    "autumn": {"low": 24, "high": 31, "humidity": 82, "conditions": {"sunny": 0.3, "cloudy": 0.35, "rainy": 0.35, "snowy": 0}},
    "winter": {"low": 24, "high": 31, "humidity": 85, "conditions": {"sunny": 0.25, "cloudy": 0.35, "rainy": 0.4, "snowy": 0}},
  },
}

_CONDITION_DISPLAY = {
  "sunny": {"zh": "晴", "icon": "sun"},
  "cloudy": {"zh": "多云", "icon": "cloud"},
  "rainy": {"zh": "雨", "icon": "rain"},
  "snowy": {"zh": "雪", "icon": "snow"},
}

_CLOTHING_ADVICE = {
  "freezing": "需穿厚羽绒服、围巾、手套、帽子，注意防寒保暖",
  "cold": "建议穿厚外套或薄羽绒服，搭配毛衣和围巾",
  "cool": "适合穿夹克或风衣，可搭配长裤和薄毛衣",
  "mild": "适合穿长袖衬衫或薄外套，温度宜人",
  "warm": "适合穿T恤、短袖，薄长裤或裙子",
  "hot": "建议穿轻薄透气衣物，注意防晒和补水",
}


def _get_season(date_str: str) -> str:
  """Determine season from date string."""
  try:
    month = int(date_str.split("-")[1])
  except (IndexError, ValueError):
    month = 6
  if month in (3, 4, 5):
    return "spring"
  elif month in (6, 7, 8):
    return "summer"
  elif month in (9, 10, 11):
    return "autumn"
  else:
    return "winter"


def _get_climate(city: str, season: str) -> Dict[str, Any]:
  """Get climate data for a city and season."""
  if city in _CLIMATE_PROFILES:
    return _CLIMATE_PROFILES[city][season]
  return {
    "low": random.randint(10, 20),
    "high": random.randint(20, 30),
    "humidity": random.randint(40, 70),
    "conditions": {"sunny": 0.4, "cloudy": 0.3, "rainy": 0.25, "snowy": 0.05},
  }


def _pick_condition(weights: Dict[str, float]) -> str:
  """Weighted random selection of weather condition."""
  conditions = list(weights.keys())
  probs = list(weights.values())
  return random.choices(conditions, weights=probs, k=1)[0]


def _get_clothing_advice(avg_temp: float) -> str:
  """Get clothing advice based on average temperature."""
  if avg_temp < -5:
    return _CLOTHING_ADVICE["freezing"]
  elif avg_temp < 5:
    return _CLOTHING_ADVICE["cold"]
  elif avg_temp < 15:
    return _CLOTHING_ADVICE["cool"]
  elif avg_temp < 22:
    return _CLOTHING_ADVICE["mild"]
  elif avg_temp < 30:
    return _CLOTHING_ADVICE["warm"]
  else:
    return _CLOTHING_ADVICE["hot"]


def _get_travel_advice(condition: str, avg_temp: float) -> str:
  """Generate travel advice based on weather."""
  if condition == "rainy":
    return "建议携带雨伞，可安排室内活动（博物馆、商场等）"
  elif condition == "snowy":
    return "路面可能湿滑，注意防滑；可欣赏雪景，注意保暖"
  elif avg_temp > 32:
    return "高温天气，建议避开中午时段外出，多补水，注意防晒"
  elif avg_temp < 0:
    return "低温天气，建议减少户外时间，做好保暖措施"
  else:
    return "天气适宜出行，享受旅途愉快"


def _generate_day_weather(city: str, date_str: str) -> Dict[str, Any]:
  """Generate mock weather data for a single day."""
  season = _get_season(date_str)
  climate = _get_climate(city, season)

  temp_low = climate["low"] + random.randint(-3, 3)
  temp_high = climate["high"] + random.randint(-3, 3)
  humidity = min(100, max(20, climate["humidity"] + random.randint(-10, 10)))
  condition = _pick_condition(climate["conditions"])

  if condition == "rainy":
    humidity = min(100, humidity + 15)
    temp_high -= random.randint(1, 3)
  elif condition == "snowy":
    temp_high = min(temp_high, 2)
    temp_low = min(temp_low, -2)

  avg_temp = (temp_low + temp_high) / 2
  cond_info = _CONDITION_DISPLAY.get(condition, _CONDITION_DISPLAY["sunny"])

  return {
    "city": city,
    "date": date_str,
    "condition": cond_info["zh"],
    "condition_code": condition,
    "icon": cond_info["icon"],
    "temp_high": temp_high,
    "temp_low": temp_low,
    "humidity": humidity,
    "wind_speed_kmh": random.randint(5, 30),
    "wind_direction": random.choice(["北", "东北", "东", "东南", "南", "西南", "西", "西北"]),
    "uv_index": random.randint(1, 11) if condition == "sunny" else random.randint(1, 5),
    "sunrise": f"0{random.randint(5, 6)}:{random.randint(10, 50):02d}",
    "sunset": f"{random.randint(17, 19)}:{random.randint(10, 50):02d}",
    "clothing_advice": _get_clothing_advice(avg_temp),
    "travel_advice": _get_travel_advice(condition, avg_temp),
  }


async def get_weather(
  city: str,
  date: str,
) -> Dict[str, Any]:
  """Get weather for a specific city and date.

  Fallback: QWeather → Open-Meteo → Serper → mock.
  """
  # 1. QWeather (China-native, <50ms)
  try:
    location_id = await qw_lookup_city(city)
    if location_id:
      forecast = await qw_get_forecast(location_id, days=3)
      if forecast and forecast.get("daily"):
        for day in forecast["daily"]:
          if day.get("date") == date:
            avg = (day["high_temp"] + day["low_temp"]) / 2
            data = qweather_to_weather(city, day, avg, _get_clothing_advice, _get_travel_advice)
            return {"success": True, "source": "qweather", "data": data}
        day = forecast["daily"][0]
        avg = (day["high_temp"] + day["low_temp"]) / 2
        data = qweather_to_weather(city, day, avg, _get_clothing_advice, _get_travel_advice)
        return {"success": True, "source": "qweather", "data": data}
  except Exception as exc:
    logger.debug("QWeather failed for %s: %s", city, exc)

  # 2. Open-Meteo (overseas fallback)
  try:
    result = await open_meteo_single_day(city, date, _get_clothing_advice, _get_travel_advice)
    if result:
      return {"success": True, "source": "open-meteo", "data": result}
  except Exception as exc:
    logger.debug("Open-Meteo failed for %s: %s", city, exc)

  # 3. Serper (may be blocked in China)
  try:
    from agent.tools.serper.client import search as serper_search
    from agent.tools.serper.parsers import parse_weather_results
    raw = await serper_search(f"{city}天气 {date}", num=5)
    if "error" not in raw:
      weather = parse_weather_results(raw, city, date)
      if weather:
        weather["clothing_advice"] = _get_clothing_advice(
          (weather["temp_high"] + weather["temp_low"]) / 2
        )
        return {"success": True, "source": "serper", "data": weather}
  except Exception:
    pass

  # 4. Mock fallback
  try:
    await asyncio.sleep(random.uniform(0.05, 0.15))
    return {"success": True, "source": "mock", "data": _generate_day_weather(city, date)}
  except Exception as exc:
    return {"success": False, "error": str(exc), "data": None}


async def get_weather_forecast(
  city: str,
  start_date: str,
  days: int = 5,
) -> Dict[str, Any]:
  """Get multi-day weather forecast.

  Fallback: QWeather (3d) → Open-Meteo (7d) → mock.
  """
  days = min(days, 14)
  source = "mock"

  # 1. QWeather (up to 3-day free tier)
  forecasts: List[Dict[str, Any]] = []
  try:
    location_id = await qw_lookup_city(city)
    if location_id:
      forecast = await qw_get_forecast(location_id, days=min(days, 3))
      if forecast and forecast.get("daily"):
        source = "qweather"
        for day in forecast["daily"]:
          avg = (day["high_temp"] + day["low_temp"]) / 2
          forecasts.append(qweather_to_weather(city, day, avg, _get_clothing_advice, _get_travel_advice))
  except Exception as exc:
    logger.debug("QWeather forecast failed for %s: %s", city, exc)

  # 2. Open-Meteo for remaining days
  if len(forecasts) < days:
    try:
      om = await open_meteo_multi_day(city, start_date, days, _get_clothing_advice, _get_travel_advice)
      if om:
        if not forecasts:
          source = "open-meteo"
          forecasts = om
        else:
          existing = {f["date"] for f in forecasts}
          for r in om:
            if r["date"] not in existing and len(forecasts) < days:
              forecasts.append(r)
          source = "qweather+open-meteo"
    except Exception as exc:
      logger.debug("Open-Meteo forecast failed for %s: %s", city, exc)

  # 3. Mock fallback for remaining
  if len(forecasts) < days:
    try:
      base_date = datetime.strptime(start_date, "%Y-%m-%d")
    except ValueError:
      base_date = datetime.now()

    existing = {f["date"] for f in forecasts}
    for i in range(days):
      d = base_date + timedelta(days=i)
      ds = d.strftime("%Y-%m-%d")
      if ds not in existing and len(forecasts) < days:
        forecasts.append(_generate_day_weather(city, ds))
    if source != "mock" and len(forecasts) > len(existing):
      source += "+mock"

  forecasts.sort(key=lambda f: f.get("date", ""))

  temps = [f.get("temp_high", f.get("high_temp", 20)) for f in forecasts]
  lows = [f.get("temp_low", f.get("low_temp", 10)) for f in forecasts]
  conds = [f.get("condition_code", f.get("condition", "")) for f in forecasts]
  rainy = sum(1 for c in conds if c in ("rainy", "snowy", "雨", "雪", "小雨", "中雨", "大雨", "阵雨", "暴雨", "小雪", "中雪", "大雪"))

  return {
    "success": True,
    "source": source,
    "query": {"city": city, "start_date": start_date, "days": days},
    "forecasts": forecasts,
    "summary": {
      "temp_range": f"{min(lows)}~{max(temps)}°C",
      "avg_high": round(sum(temps) / len(temps), 1),
      "rainy_days": rainy,
      "overall": "适宜出行" if rainy <= days // 3 else "部分时段有雨雪，建议备好雨具",
      "packing_suggestion": _get_clothing_advice(sum(temps) / len(temps)),
    },
  }
