# Hotel search MCP tool - mock implementation
# Returns realistic hotel data for development/testing
from __future__ import annotations

import asyncio
import random
from typing import Any, Dict, List, Optional


# City-specific hotel data pools
_HOTEL_POOLS: Dict[str, List[Dict[str, Any]]] = {
  "东京": [
    {"name": "东京帝国酒店", "name_en": "Imperial Hotel Tokyo", "stars": 5, "area": "千代田区", "base_price": 2800},
    {"name": "东京安缦", "name_en": "Aman Tokyo", "stars": 5, "area": "大手町", "base_price": 5500},
    {"name": "新宿格拉斯丽酒店", "name_en": "Hotel Gracery Shinjuku", "stars": 4, "area": "新宿", "base_price": 900},
    {"name": "东京湾洲际酒店", "name_en": "InterContinental Tokyo Bay", "stars": 5, "area": "台场", "base_price": 2200},
    {"name": "涩谷东急卓越酒店", "name_en": "Tokyu Excel Shibuya", "stars": 4, "area": "涩谷", "base_price": 1100},
    {"name": "浅草豪景酒店", "name_en": "Asakusa View Hotel", "stars": 4, "area": "浅草", "base_price": 800},
    {"name": "东京站大都会酒店", "name_en": "Hotel Metropolitan Tokyo", "stars": 4, "area": "池袋", "base_price": 950},
    {"name": "银座三井花园酒店", "name_en": "Mitsui Garden Ginza", "stars": 4, "area": "银座", "base_price": 1300},
  ],
  "大阪": [
    {"name": "大阪丽思卡尔顿", "name_en": "The Ritz-Carlton Osaka", "stars": 5, "area": "梅田", "base_price": 3200},
    {"name": "大阪瑞士南海酒店", "name_en": "Swissôtel Nankai Osaka", "stars": 5, "area": "难波", "base_price": 1800},
    {"name": "大阪十字酒店", "name_en": "Cross Hotel Osaka", "stars": 4, "area": "心斋桥", "base_price": 900},
    {"name": "道顿堀酒店", "name_en": "Dotonbori Hotel", "stars": 3, "area": "道顿堀", "base_price": 600},
    {"name": "大阪万豪都酒店", "name_en": "Osaka Marriott Miyako", "stars": 5, "area": "天王寺", "base_price": 2500},
    {"name": "大阪希尔顿", "name_en": "Hilton Osaka", "stars": 5, "area": "梅田", "base_price": 2000},
  ],
  "北京": [
    {"name": "北京国贸大酒店", "name_en": "China World Summit Wing", "stars": 5, "area": "国贸CBD", "base_price": 2500},
    {"name": "王府井文华东方", "name_en": "Mandarin Oriental Wangfujing", "stars": 5, "area": "王府井", "base_price": 3500},
    {"name": "北京饭店", "name_en": "Beijing Hotel", "stars": 5, "area": "长安街", "base_price": 1200},
    {"name": "三里屯通盈中心洲际", "name_en": "InterContinental Sanlitun", "stars": 5, "area": "三里屯", "base_price": 1800},
    {"name": "颐和安缦", "name_en": "Aman Summer Palace", "stars": 5, "area": "颐和园", "base_price": 4800},
    {"name": "桔子水晶酒店(鼓楼店)", "name_en": "Crystal Orange Gulou", "stars": 3, "area": "鼓楼", "base_price": 500},
  ],
  "上海": [
    {"name": "上海外滩华尔道夫", "name_en": "Waldorf Astoria Shanghai", "stars": 5, "area": "外滩", "base_price": 3000},
    {"name": "上海和平饭店", "name_en": "Fairmont Peace Hotel", "stars": 5, "area": "南京路", "base_price": 2800},
    {"name": "上海璞丽酒店", "name_en": "The PuLi Hotel", "stars": 5, "area": "静安", "base_price": 2500},
    {"name": "上海虹桥雅高美爵", "name_en": "Grand Mercure Hongqiao", "stars": 4, "area": "虹桥", "base_price": 700},
    {"name": "上海外滩英迪格", "name_en": "Hotel Indigo Shanghai", "stars": 4, "area": "外滩", "base_price": 1200},
    {"name": "全季酒店(陆家嘴店)", "name_en": "JI Hotel Lujiazui", "stars": 3, "area": "陆家嘴", "base_price": 450},
  ],
  "曼谷": [
    {"name": "曼谷文华东方", "name_en": "Mandarin Oriental Bangkok", "stars": 5, "area": "湄南河", "base_price": 2800},
    {"name": "暹罗凯宾斯基", "name_en": "Siam Kempinski", "stars": 5, "area": "暹罗", "base_price": 2200},
    {"name": "素坤逸万豪", "name_en": "Marriott Sukhumvit", "stars": 5, "area": "素坤逸", "base_price": 1200},
    {"name": "考山路背包客栈", "name_en": "Khaosan Palace Hotel", "stars": 2, "area": "考山路", "base_price": 200},
    {"name": "曼谷拉查达酒店", "name_en": "Ratchada Hotel", "stars": 3, "area": "拉差达", "base_price": 350},
  ],
}

# Facilities pools by star rating
_FACILITIES: Dict[int, List[str]] = {
  5: ["免费WiFi", "室外泳池", "健身中心", "Spa", "行政酒廊", "接机服务", "礼宾服务", "米其林餐厅", "商务中心"],
  4: ["免费WiFi", "健身中心", "自助早餐", "洗衣服务", "商务中心", "行李寄存", "24小时前台"],
  3: ["免费WiFi", "自助早餐", "行李寄存", "24小时前台", "洗衣服务"],
  2: ["免费WiFi", "行李寄存", "24小时前台"],
}

# Room types
_ROOM_TYPES = [
  {"type": "standard", "name": "标准间", "multiplier": 1.0},
  {"type": "deluxe", "name": "豪华房", "multiplier": 1.5},
  {"type": "suite", "name": "套房", "multiplier": 2.5},
  {"type": "family", "name": "家庭房", "multiplier": 1.8},
]


def _generate_hotel(
  hotel_template: Dict[str, Any],
  checkin: str,
  checkout: str,
  guests: int,
) -> Dict[str, Any]:
  """Generate a single mock hotel record from a template."""
  stars = hotel_template["stars"]
  base_price = hotel_template["base_price"]

  # Price variation +-25%
  price = int(base_price * random.uniform(0.75, 1.25))
  # Guest surcharge for > 2 guests
  if guests > 2:
    price = int(price * (1 + (guests - 2) * 0.15))

  # Rating: correlated with stars but with noise
  rating = min(5.0, max(3.0, stars - 0.5 + random.uniform(0, 1.0)))
  rating = round(rating, 1)
  review_count = random.randint(200, 8000)

  # Pick facilities based on star rating
  available_facilities = _FACILITIES.get(stars, _FACILITIES[3])
  num_facilities = min(len(available_facilities), random.randint(4, len(available_facilities)))
  facilities = random.sample(available_facilities, num_facilities)

  # Available room types
  room_types = []
  for rt in _ROOM_TYPES:
    if random.random() > 0.3:  # 70% chance each room type is available
      room_types.append({
        "type": rt["type"],
        "name": rt["name"],
        "price_per_night": int(price * rt["multiplier"]),
        "available": random.randint(1, 10),
      })

  if not room_types:
    room_types.append({
      "type": "standard",
      "name": "标准间",
      "price_per_night": price,
      "available": random.randint(1, 10),
    })

  return {
    "name": hotel_template["name"],
    "name_en": hotel_template["name_en"],
    "stars": stars,
    "rating": rating,
    "review_count": review_count,
    "area": hotel_template["area"],
    "price_per_night": price,
    "currency": "CNY",
    "checkin": checkin,
    "checkout": checkout,
    "facilities": facilities,
    "room_types": room_types,
    "breakfast_included": random.random() > 0.4,
    "free_cancellation": random.random() > 0.3,
    "distance_to_center": f"{round(random.uniform(0.3, 8.0), 1)}km",
    "image_url": f"https://placeholder.travel/hotel/{hotel_template['name_en'].lower().replace(' ', '-')}.jpg",
  }


async def search_hotels(
  city: str,
  checkin: str,
  checkout: str,
  guests: int = 1,
  stars_min: Optional[int] = None,
  price_max: Optional[int] = None,
  max_results: int = 5,
) -> Dict[str, Any]:
  """Search hotels in a city.

  Args:
    city: City name (e.g. "东京", "大阪", "北京")
    checkin: Check-in date in YYYY-MM-DD format
    checkout: Check-out date in YYYY-MM-DD format
    guests: Number of guests (default 1)
    stars_min: Minimum star rating filter (optional)
    price_max: Maximum price per night filter (optional)
    max_results: Maximum number of results (3-5)

  Returns:
    Dict with hotel list and search metadata
  """
  # Try Serper real search first
  try:
    from agent.tools.serper.client import search_places
    from agent.tools.serper.parsers import parse_hotel_results
    query = f"{city}酒店 {checkin}"
    raw = await search_places(query)
    if "error" not in raw:
      hotels = parse_hotel_results(raw, city, checkin, checkout)
      if hotels:
        if stars_min:
          hotels = [h for h in hotels if h.get("stars", 0) >= stars_min]
        if price_max:
          hotels = [h for h in hotels if h.get("price_per_night", 0) <= price_max]
        hotels = hotels[:max_results]
        prices = [h["price_per_night"] for h in hotels] if hotels else [0]
        return {
          "success": True,
          "source": "serper",
          "query": {"city": city, "checkin": checkin, "checkout": checkout, "guests": guests},
          "results": hotels,
          "total_count": len(hotels),
          "price_summary": {"min_price": min(prices), "max_price": max(prices), "avg_price": int(sum(prices) / len(prices)), "currency": "CNY"},
        }
  except Exception:
    pass  # Fall through to mock

  try:
    await asyncio.sleep(random.uniform(0.1, 0.3))

    # Get hotel pool for the city, or generate generic hotels
    pool = _HOTEL_POOLS.get(city, _generate_generic_pool(city))

    hotels = []
    for template in pool:
      hotel = _generate_hotel(template, checkin, checkout, guests)
      # Apply filters
      if stars_min and hotel["stars"] < stars_min:
        continue
      if price_max and hotel["price_per_night"] > price_max:
        continue
      hotels.append(hotel)

    # Shuffle and limit
    random.shuffle(hotels)
    hotels = hotels[:max_results]

    # Sort by rating desc
    hotels.sort(key=lambda h: h["rating"], reverse=True)

    prices = [h["price_per_night"] for h in hotels] if hotels else [0]
    return {
      "success": True,
      "query": {
        "city": city,
        "checkin": checkin,
        "checkout": checkout,
        "guests": guests,
        "stars_min": stars_min,
        "price_max": price_max,
      },
      "results": hotels,
      "total_count": len(hotels),
      "price_summary": {
        "min_price": min(prices),
        "max_price": max(prices),
        "avg_price": int(sum(prices) / len(prices)) if prices else 0,
        "currency": "CNY",
      },
    }
  except Exception as exc:
    return {
      "success": False,
      "error": str(exc),
      "query": {"city": city, "checkin": checkin, "checkout": checkout},
      "results": [],
      "total_count": 0,
    }


def _generate_generic_pool(city: str) -> List[Dict[str, Any]]:
  """Generate generic hotel templates for cities not in the predefined pool."""
  templates = [
    {"name": f"{city}洲际酒店", "name_en": f"InterContinental {city}", "stars": 5, "area": "市中心", "base_price": random.randint(1500, 3000)},
    {"name": f"{city}希尔顿酒店", "name_en": f"Hilton {city}", "stars": 5, "area": "商务区", "base_price": random.randint(1200, 2500)},
    {"name": f"{city}全季酒店", "name_en": f"JI Hotel {city}", "stars": 3, "area": "市中心", "base_price": random.randint(300, 600)},
    {"name": f"{city}亚朵酒店", "name_en": f"Atour Hotel {city}", "stars": 4, "area": "商圈", "base_price": random.randint(400, 800)},
    {"name": f"{city}万豪酒店", "name_en": f"Marriott {city}", "stars": 5, "area": "核心区", "base_price": random.randint(1000, 2200)},
  ]
  return templates
