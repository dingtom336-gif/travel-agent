# Proactive service: weather alerts and travel advisories
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from agent.tools.mcp.weather_api import get_weather

logger = logging.getLogger(__name__)


async def check_weather_alerts(
  city: str,
  start_date: str,
  days: int = 5,
) -> List[Dict[str, Any]]:
  """Check for severe weather conditions during a trip.

  Returns a list of alert dicts with severity and recommendation.
  """
  alerts: List[Dict[str, Any]] = []

  try:
    base = datetime.strptime(start_date, "%Y-%m-%d")
  except ValueError:
    return alerts

  for i in range(days):
    date_str = (base + timedelta(days=i)).strftime("%Y-%m-%d")
    try:
      result = await get_weather(city, date_str)
      if not result.get("success"):
        continue

      data = result.get("data", {})
      temp_high = data.get("temp_high", 25)
      temp_low = data.get("temp_low", 15)
      condition = data.get("condition", "")
      condition_code = data.get("condition_code", "")

      # High temperature alert
      if temp_high >= 38:
        alerts.append({
          "date": date_str,
          "type": "extreme_heat",
          "severity": "high",
          "title": f"{city} 高温预警",
          "message": f"{date_str} 预计最高温度 {temp_high}°C，建议避免中午户外活动",
          "recommendation": "调整行程至室内活动，备好防晒物品和充足饮用水",
        })

      # Severe cold alert
      if temp_low <= -10:
        alerts.append({
          "date": date_str,
          "type": "extreme_cold",
          "severity": "high",
          "title": f"{city} 严寒预警",
          "message": f"{date_str} 预计最低温度 {temp_low}°C，注意防寒保暖",
          "recommendation": "准备厚羽绒服和保暖装备，减少户外停留时间",
        })

      # Rain/snow alert
      if condition_code in ("rainy", "snowy"):
        sev = "medium" if condition_code == "rainy" else "high"
        alerts.append({
          "date": date_str,
          "type": "precipitation",
          "severity": sev,
          "title": f"{city} {'降雪' if condition_code == 'snowy' else '降雨'}提醒",
          "message": f"{date_str} 预计有{condition}，可能影响户外行程",
          "recommendation": "建议携带雨具，可考虑备选室内行程",
        })

    except Exception as exc:
      logger.debug("Weather check error for %s on %s: %s", city, date_str, exc)

  return alerts


async def generate_trip_advisory(
  destination: str,
  start_date: str,
  end_date: str,
) -> Dict[str, Any]:
  """Generate a comprehensive trip advisory with weather alerts.

  Returns advisory dict with alerts and overall assessment.
  """
  try:
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    days = max(1, (end - start).days + 1)
  except ValueError:
    days = 5

  alerts = await check_weather_alerts(destination, start_date, days)

  high_count = sum(1 for a in alerts if a["severity"] == "high")
  medium_count = sum(1 for a in alerts if a["severity"] == "medium")

  if high_count >= 2:
    overall = "caution"
    summary = f"旅途中有{high_count}个高级别天气预警，建议做好备选方案"
  elif high_count == 1 or medium_count >= 2:
    summary = "部分时段天气可能不佳，建议关注天气变化"
    overall = "moderate"
  else:
    summary = "天气条件总体适宜出行"
    overall = "good"

  return {
    "destination": destination,
    "period": f"{start_date} ~ {end_date}",
    "overall": overall,
    "summary": summary,
    "alerts": alerts,
    "alert_count": len(alerts),
    "generated_at": datetime.now().isoformat(),
  }
