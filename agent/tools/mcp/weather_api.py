# Weather API MCP tool - mock implementation
# Returns realistic weather data for travel destinations
from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


# City climate profiles: (avg_temp_low, avg_temp_high, humidity, conditions_weight)
# Conditions weight: {sunny, cloudy, rainy, snowy} probabilities
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

# Weather condition display names
_CONDITION_DISPLAY = {
  "sunny": {"zh": "晴", "icon": "sun"},
  "cloudy": {"zh": "多云", "icon": "cloud"},
  "rainy": {"zh": "雨", "icon": "rain"},
  "snowy": {"zh": "雪", "icon": "snow"},
}

# Clothing advice based on temperature
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
    month = 6  # Default to summer
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
  # Generate reasonable defaults for unknown cities
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


def _generate_day_weather(city: str, date_str: str) -> Dict[str, Any]:
  """Generate weather data for a single day."""
  season = _get_season(date_str)
  climate = _get_climate(city, season)

  # Add random variation to base temps
  temp_low = climate["low"] + random.randint(-3, 3)
  temp_high = climate["high"] + random.randint(-3, 3)
  humidity = min(100, max(20, climate["humidity"] + random.randint(-10, 10)))
  condition = _pick_condition(climate["conditions"])

  # Adjust for rain/snow
  if condition == "rainy":
    humidity = min(100, humidity + 15)
    temp_high -= random.randint(1, 3)
  elif condition == "snowy":
    temp_high = min(temp_high, 2)
    temp_low = min(temp_low, -2)

  avg_temp = (temp_low + temp_high) / 2
  cond_info = _CONDITION_DISPLAY.get(condition, _CONDITION_DISPLAY["sunny"])
  wind_speed = random.randint(5, 30)

  return {
    "city": city,
    "date": date_str,
    "condition": cond_info["zh"],
    "condition_code": condition,
    "icon": cond_info["icon"],
    "temp_high": temp_high,
    "temp_low": temp_low,
    "humidity": humidity,
    "wind_speed_kmh": wind_speed,
    "wind_direction": random.choice(["北", "东北", "东", "东南", "南", "西南", "西", "西北"]),
    "uv_index": random.randint(1, 11) if condition == "sunny" else random.randint(1, 5),
    "sunrise": f"0{random.randint(5, 6)}:{random.randint(10, 50):02d}",
    "sunset": f"{random.randint(17, 19)}:{random.randint(10, 50):02d}",
    "clothing_advice": _get_clothing_advice(avg_temp),
    "travel_advice": _get_travel_advice(condition, avg_temp),
  }


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


async def get_weather(
  city: str,
  date: str,
) -> Dict[str, Any]:
  """Get weather forecast for a specific city and date.

  Args:
    city: City name (e.g. "东京", "北京")
    date: Date in YYYY-MM-DD format

  Returns:
    Dict with weather information
  """
  try:
    await asyncio.sleep(random.uniform(0.05, 0.15))
    weather = _generate_day_weather(city, date)
    return {
      "success": True,
      "data": weather,
    }
  except Exception as exc:
    return {
      "success": False,
      "error": str(exc),
      "data": None,
    }


async def get_weather_forecast(
  city: str,
  start_date: str,
  days: int = 5,
) -> Dict[str, Any]:
  """Get multi-day weather forecast.

  Args:
    city: City name
    start_date: Start date in YYYY-MM-DD format
    days: Number of forecast days (default 5, max 14)

  Returns:
    Dict with daily forecast list and summary
  """
  try:
    await asyncio.sleep(random.uniform(0.1, 0.2))

    days = min(days, 14)
    try:
      base_date = datetime.strptime(start_date, "%Y-%m-%d")
    except ValueError:
      base_date = datetime.now()

    forecasts = []
    for i in range(days):
      day = base_date + timedelta(days=i)
      date_str = day.strftime("%Y-%m-%d")
      weather = _generate_day_weather(city, date_str)
      forecasts.append(weather)

    # Summary
    temps = [f["temp_high"] for f in forecasts]
    conditions = [f["condition_code"] for f in forecasts]
    rainy_days = sum(1 for c in conditions if c in ("rainy", "snowy"))

    return {
      "success": True,
      "query": {
        "city": city,
        "start_date": start_date,
        "days": days,
      },
      "forecasts": forecasts,
      "summary": {
        "temp_range": f"{min(f['temp_low'] for f in forecasts)}~{max(temps)}°C",
        "avg_high": round(sum(temps) / len(temps), 1),
        "rainy_days": rainy_days,
        "overall": "适宜出行" if rainy_days <= days // 3 else "部分时段有雨雪，建议备好雨具",
        "packing_suggestion": _get_clothing_advice(sum(temps) / len(temps)),
      },
    }
  except Exception as exc:
    return {
      "success": False,
      "error": str(exc),
      "query": {"city": city, "start_date": start_date, "days": days},
      "forecasts": [],
    }
