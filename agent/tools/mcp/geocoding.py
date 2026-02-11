# Geocode helper - resolves location names to coordinates (Amap + hardcoded)
from __future__ import annotations

import logging
from typing import Optional, Tuple

from agent.tools.amap.client import geocode as amap_geocode

logger = logging.getLogger(__name__)

# Hardcoded coordinates for common cities (lat, lng)
_CITY_COORDS = {
  "东京": (35.6762, 139.6503), "大阪": (34.6937, 135.5023),
  "京都": (35.0116, 135.7681), "奈良": (34.6851, 135.8048),
  "北京": (39.9042, 116.4074), "上海": (31.2304, 121.4737),
  "广州": (23.1291, 113.2644), "成都": (30.5728, 104.0668),
  "杭州": (30.2741, 120.1551), "西安": (34.3416, 108.9398),
  "南京": (32.0603, 118.7969), "香港": (22.3193, 114.1694),
  "台北": (25.0330, 121.5654), "三亚": (18.2528, 109.5120),
  "曼谷": (13.7563, 100.5018), "清迈": (18.7883, 98.9853),
  "芭提雅": (12.9236, 100.8825), "首尔": (37.5665, 126.9780),
  "釜山": (35.1796, 129.0756), "新加坡": (1.3521, 103.8198),
}


async def geocode(location: str) -> Optional[Tuple[float, float]]:
  """Resolve location name to (lat, lng). Tries Amap then hardcoded."""
  # 1. Amap geocoding
  try:
    coords = await amap_geocode(location)
    if coords:
      return coords
  except Exception as exc:
    logger.debug("Amap geocode failed for %s: %s", location, exc)

  # 2. Hardcoded fallback
  return _CITY_COORDS.get(location)
